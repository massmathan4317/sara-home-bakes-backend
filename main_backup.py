from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3, json, hashlib
from datetime import datetime

app = FastAPI(title="Sara Home Bakes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "sara_bakes.db"

# ── Database Setup ─────────────────────────────────────────────────────────
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT,
            emoji TEXT DEFAULT '🎂',
            available INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            address TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)
    pw = hashlib.sha256("sara@admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO admin_users (username,password) VALUES (?,?)", ("admin", pw))

    items = [
        ("Chocolate Truffle Cake","Rich dark chocolate ganache layers",650,"Cakes","🎂"),
        ("Vanilla Butter Cake","Classic moist vanilla buttercream",550,"Cakes","🍰"),
        ("Red Velvet Cake","Velvet smooth cream cheese frosting",700,"Cakes","🎂"),
        ("Marble Cake","Swirled choco & vanilla perfection",600,"Cakes","🍰"),
        ("Black Forest Cake","Cherry cream with chocolate sponge",750,"Cakes","🎂"),
        ("Chocolate Chip Cookies","Soft baked premium chips (12 pcs)",280,"Cookies","🍪"),
        ("Butter Cookies","Melt-in-mouth shortbread (12 pcs)",250,"Cookies","🍪"),
        ("Almond Biscotti","Crispy Italian-style (8 pcs)",320,"Cookies","🍪"),
        ("Banana Bread","Moist loaf with walnuts",380,"Breads","🍞"),
        ("Cinnamon Rolls","Soft swirls cream glaze (6 pcs)",350,"Pastries","🥐"),
        ("Brownies","Fudgy dark chocolate squares (9 pcs)",300,"Pastries","🍫"),
        ("Cup Cakes","Assorted frosted cupcakes (6 pcs)",420,"Pastries","🧁"),
        ("Fruit Tart","Custard fresh fruits buttery crust",480,"Pastries","🥧"),
        ("Almond Cake","Nutty moist almond sponge",580,"Cakes","🎂"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO products (name,description,price,category,emoji) VALUES (?,?,?,?,?)",
        items
    )
    c.commit()
    c.close()

init_db()

# ── Models ──────────────────────────────────────────────────────────────────
class OrderItem(BaseModel):
    product_id: int
    name: str
    price: float
    quantity: int
    emoji: Optional[str] = "🎂"

class OrderCreate(BaseModel):
    customer_name: str
    phone: str
    email: Optional[str] = ""
    address: str
    items: List[OrderItem]
    total: float
    note: Optional[str] = ""

class AdminLogin(BaseModel):
    username: str
    password: str

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    emoji: Optional[str] = "🎂"
    available: Optional[int] = 1

class StatusUpdate(BaseModel):
    status: str

# ── Routes ──────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Sara Home Bakes API 🎂", "status": "running"}

@app.get("/products")
def get_products():
    c = db()
    rows = c.execute("SELECT * FROM products WHERE available=1 ORDER BY category,name").fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.get("/products/all")
def all_products():
    c = db()
    rows = c.execute("SELECT * FROM products ORDER BY category,name").fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.post("/products")
def add_product(p: ProductCreate):
    c = db()
    c.execute("INSERT INTO products (name,description,price,category,emoji,available) VALUES (?,?,?,?,?,?)",
              (p.name,p.description,p.price,p.category,p.emoji,p.available))
    c.commit(); c.close()
    return {"message": "Product added"}

@app.put("/products/{pid}")
def update_product(pid: int, p: ProductCreate):
    c = db()
    c.execute("UPDATE products SET name=?,description=?,price=?,category=?,emoji=?,available=? WHERE id=?",
              (p.name,p.description,p.price,p.category,p.emoji,p.available,pid))
    c.commit(); c.close()
    return {"message": "Updated"}

@app.delete("/products/{pid}")
def delete_product(pid: int):
    c = db()
    c.execute("DELETE FROM products WHERE id=?", (pid,))
    c.commit(); c.close()
    return {"message": "Deleted"}

@app.post("/orders")
def place_order(order: OrderCreate):
    c = db()
    c.execute(
        "INSERT INTO orders (customer_name,phone,email,address,items,total,note) VALUES (?,?,?,?,?,?,?)",
        (order.customer_name,order.phone,order.email,order.address,
         json.dumps([i.dict() for i in order.items]),order.total,order.note)
    )
    c.commit()
    oid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.close()
    return {"message": "Order placed!", "order_id": oid}

@app.get("/orders")
def get_orders():
    c = db()
    rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items"])
        result.append(d)
    return result

@app.get("/orders/{oid}")
def get_order(oid: int):
    c = db()
    row = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    c.close()
    if not row: raise HTTPException(404, "Not found")
    d = dict(row); d["items"] = json.loads(d["items"])
    return d

@app.put("/orders/{oid}/status")
def update_status(oid: int, body: StatusUpdate):
    c = db()
    c.execute("UPDATE orders SET status=? WHERE id=?", (body.status, oid))
    c.commit(); c.close()
    return {"message": "Status updated"}

@app.delete("/orders/{oid}")
def delete_order(oid: int):
    c = db()
    c.execute("DELETE FROM orders WHERE id=?", (oid,))
    c.commit(); c.close()
    return {"message": "Deleted"}

@app.post("/admin/login")
def admin_login(body: AdminLogin):
    c = db()
    pw = hashlib.sha256(body.password.encode()).hexdigest()
    row = c.execute("SELECT * FROM admin_users WHERE username=? AND password=?", (body.username,pw)).fetchone()
    c.close()
    if not row: raise HTTPException(401, "Invalid credentials")
    return {"token": "sara-admin-2024", "message": "Login successful"}

@app.get("/stats")
def get_stats():
    c = db()
    total = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    completed = c.execute("SELECT COUNT(*) FROM orders WHERE status='completed'").fetchone()[0]
    revenue = c.execute("SELECT SUM(total) FROM orders WHERE status='completed'").fetchone()[0] or 0
    products = c.execute("SELECT COUNT(*) FROM products WHERE available=1").fetchone()[0]
    today = c.execute("SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now')").fetchone()[0]
    c.close()
    return {"total_orders":total,"pending_orders":pending,"completed_orders":completed,
            "total_revenue":revenue,"active_products":products,"today_orders":today}
