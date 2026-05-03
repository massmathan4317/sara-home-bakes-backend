from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import sqlite3, json, hashlib, random, string
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DB = "sara_bakes.db"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "sarahomebakes@gmail.com"
# EMAIL_PASS = ""  # ← Replace with Gmail App Password
EMAIL_PASS = "kpgbtqusnjmvzyay"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if EMAIL_PASS == "your_app_password_here":
        print("⚠️  WARNING: Email not configured! Set EMAIL_PASS in main.py")
        print("   Get Gmail App Password: myaccount.google.com → Security → App Passwords")
    init_db()
    print("✅ Sara Home Bakes API started!")
    yield
    # Shutdown (nothing to clean up)

app = FastAPI(title="Sara Home Bakes API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, description TEXT,
            price REAL NOT NULL, category TEXT,
            emoji TEXT DEFAULT '🎂', available INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '', password TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            otp TEXT DEFAULT '', otp_expiry TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS delivery_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT NOT NULL,
            vehicle TEXT DEFAULT 'Bike',
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL, phone TEXT NOT NULL,
            email TEXT DEFAULT '', address TEXT NOT NULL,
            items TEXT NOT NULL, total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            note TEXT DEFAULT '',
            user_id INTEGER DEFAULT NULL,
            delivery_partner_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password TEXT NOT NULL
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
    c.executemany("INSERT OR IGNORE INTO products (name,description,price,category,emoji) VALUES (?,?,?,?,?)", items)
    # Sample delivery partners
    partners = [("Rajan K","9876543210","Bike"),("Muthu S","9988776655","Scooter"),("Vel R","9123456789","Bike")]
    c.executemany("INSERT OR IGNORE INTO delivery_partners (name,phone,vehicle) VALUES (?,?,?)", partners)
    c.commit(); c.close()

def gen_order_number():
    now = datetime.now()
    rand = ''.join(random.choices(string.digits, k=4))
    return f"SHB{now.strftime('%Y%m%d')}{rand}"

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def gen_otp():
    return ''.join(random.choices(string.digits, k=6))

def otp_email_html(name, otp, title="Verify Your Email"):
    return f"""
    <div style="font-family:Arial;max-width:500px;margin:auto;padding:24px;background:#FFF8F0;border-radius:16px">
      <div style="text-align:center;margin-bottom:20px">
        <div style="font-size:48px">🎂</div>
        <h2 style="color:#7A3728;margin:8px 0">Sara Home Bakes</h2>
        <p style="color:#8B6B5E;margin:0">A Sweet Escape · Ettayapuram</p>
      </div>
      <h3 style="color:#D4785A;text-align:center">{title}</h3>
      <p>Hi <strong>{name}</strong>! Your OTP is:</p>
      <div style="background:#D4785A;color:#fff;font-size:42px;font-weight:bold;text-align:center;padding:24px;border-radius:12px;letter-spacing:12px;margin:16px 0">{otp}</div>
      <p style="color:#888">⏱️ Expires in <strong>10 minutes</strong>. Do not share this OTP.</p>
      <hr style="border-color:#E8D5CC;margin:20px 0">
      <p style="color:#aaa;font-size:12px;text-align:center">📞 9363992785 · sarahomebakes@gmail.com · Ettayapuram, Tamil Nadu</p>
    </div>"""

# Models
class UserRegister(BaseModel):
    name: str; email: str; phone: Optional[str]=""; password: str

class UserLogin(BaseModel):
    email: str; password: str

class OTPVerify(BaseModel):
    email: str; otp: str

class ResendOTP(BaseModel):
    email: str

class ForgotPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    email: str; otp: str; new_password: str

class OrderItem(BaseModel):
    product_id: int; name: str; price: float; quantity: int; emoji: Optional[str]="🎂"

class OrderCreate(BaseModel):
    customer_name: str; phone: str; email: Optional[str]=""
    address: str; items: List[OrderItem]; total: float
    note: Optional[str]=""; user_id: Optional[int]=None

class AdminLogin(BaseModel):
    username: str; password: str

class ProductCreate(BaseModel):
    name: str; description: str; price: float
    category: str; emoji: Optional[str]="🎂"; available: Optional[int]=1

class StatusUpdate(BaseModel):
    status: str

class AssignDelivery(BaseModel):
    delivery_partner_id: int

class DeliveryPartnerCreate(BaseModel):
    name: str; phone: str; vehicle: Optional[str]="Bike"

# ── Auth ──────────────────────────────────────────────────────────────────
@app.post("/auth/register")
def register(body: UserRegister):
    c = db()
    if c.execute("SELECT id FROM users WHERE email=?", (body.email,)).fetchone():
        c.close(); raise HTTPException(400, "Email already registered. Please login.")
    pw = hashlib.sha256(body.password.encode()).hexdigest()
    otp = gen_otp()
    expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
    c.execute("INSERT INTO users (name,email,phone,password,otp,otp_expiry) VALUES (?,?,?,?,?,?)",
              (body.name, body.email, body.phone, pw, otp, expiry))
    c.commit(); c.close()
    sent = send_email(body.email, "🎂 Verify Email - Sara Home Bakes", otp_email_html(body.name, otp))
    return {"message": "OTP sent!", "email_sent": sent, "debug_otp": otp}

@app.post("/auth/verify-otp")
def verify_otp(body: OTPVerify):
    c = db()
    user = c.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
    if not user: c.close(); raise HTTPException(404, "User not found")
    if user['is_verified']: c.close(); return {"message": "Already verified. Login please."}
    if user['otp'] != body.otp: c.close(); raise HTTPException(400, "Wrong OTP. Check your email.")
    if datetime.now() > datetime.fromisoformat(user['otp_expiry']): c.close(); raise HTTPException(400, "OTP expired.")
    c.execute("UPDATE users SET is_verified=1,otp='',otp_expiry='' WHERE email=?", (body.email,))
    c.commit()
    u = {"id":user['id'],"name":user['name'],"email":user['email'],"phone":user['phone']}
    c.close()
    return {"message": "Email verified! Welcome 🎂", "user": u}

@app.post("/auth/resend-otp")
def resend_otp(body: ResendOTP):
    c = db()
    user = c.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
    if not user: c.close(); raise HTTPException(404, "Email not found")
    otp = gen_otp(); expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
    c.execute("UPDATE users SET otp=?,otp_expiry=? WHERE email=?", (otp, expiry, body.email))
    c.commit(); c.close()
    send_email(body.email, "🎂 New OTP - Sara Home Bakes", otp_email_html(user['name'], otp))
    return {"message": "New OTP sent!", "debug_otp": otp}

@app.post("/auth/login")
def user_login(body: UserLogin):
    c = db()
    pw = hashlib.sha256(body.password.encode()).hexdigest()
    user = c.execute("SELECT * FROM users WHERE email=? AND password=?", (body.email, pw)).fetchone()
    c.close()
    if not user: raise HTTPException(401, "Invalid email or password")
    if not user['is_verified']: raise HTTPException(403, "Verify email first. Check inbox for OTP.")
    return {"message":"Login successful!","user":{"id":user['id'],"name":user['name'],"email":user['email'],"phone":user['phone']}}

@app.post("/auth/forgot-password")
def forgot_password(body: ForgotPassword):
    c = db()
    user = c.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
    if not user: c.close(); raise HTTPException(404, "Email not registered")
    otp = gen_otp(); expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
    c.execute("UPDATE users SET otp=?,otp_expiry=? WHERE email=?", (otp, expiry, body.email))
    c.commit(); c.close()
    send_email(body.email, "🎂 Reset Password - Sara Home Bakes", otp_email_html(user['name'], otp, "Reset Password"))
    return {"message": "Reset OTP sent!", "debug_otp": otp}

@app.post("/auth/reset-password")
def reset_password(body: ResetPassword):
    c = db()
    user = c.execute("SELECT * FROM users WHERE email=?", (body.email,)).fetchone()
    if not user: c.close(); raise HTTPException(404, "User not found")
    if user['otp'] != body.otp: c.close(); raise HTTPException(400, "Invalid OTP")
    if datetime.now() > datetime.fromisoformat(user['otp_expiry']): c.close(); raise HTTPException(400, "OTP expired")
    new_pw = hashlib.sha256(body.new_password.encode()).hexdigest()
    c.execute("UPDATE users SET password=?,otp='',otp_expiry='' WHERE email=?", (new_pw, body.email))
    c.commit(); c.close()
    return {"message": "Password reset! Please login."}

# ── Products ──────────────────────────────────────────────────────────────
@app.get("/")
def root(): return {"message":"Sara Home Bakes API 🎂","status":"running"}

@app.get("/products")
def get_products():
    c=db(); rows=c.execute("SELECT * FROM products WHERE available=1 ORDER BY category,name").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.get("/products/all")
def all_products():
    c=db(); rows=c.execute("SELECT * FROM products ORDER BY category,name").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/products")
def add_product(p: ProductCreate):
    c=db(); c.execute("INSERT INTO products (name,description,price,category,emoji,available) VALUES (?,?,?,?,?,?)",(p.name,p.description,p.price,p.category,p.emoji,p.available)); c.commit(); c.close(); return {"message":"Added"}

@app.put("/products/{pid}")
def update_product(pid:int, p:ProductCreate):
    c=db(); c.execute("UPDATE products SET name=?,description=?,price=?,category=?,emoji=?,available=? WHERE id=?",(p.name,p.description,p.price,p.category,p.emoji,p.available,pid)); c.commit(); c.close(); return {"message":"Updated"}

@app.delete("/products/{pid}")
def delete_product(pid:int):
    c=db(); c.execute("DELETE FROM products WHERE id=?",(pid,)); c.commit(); c.close(); return {"message":"Deleted"}

# ── Orders ────────────────────────────────────────────────────────────────
@app.post("/orders")
def place_order(order: OrderCreate):
    c=db()
    order_number = gen_order_number()
    c.execute("INSERT INTO orders (order_number,customer_name,phone,email,address,items,total,note,user_id) VALUES (?,?,?,?,?,?,?,?,?)",
              (order_number,order.customer_name,order.phone,order.email,order.address,
               json.dumps([i.dict() for i in order.items]),order.total,order.note,order.user_id))
    c.commit()
    oid=c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.close()
    return {"message":"Order placed!","order_id":oid,"order_number":order_number}

@app.get("/orders")
def get_orders():
    c=db()
    rows=c.execute("""SELECT o.*, dp.name as partner_name, dp.phone as partner_phone
        FROM orders o LEFT JOIN delivery_partners dp ON o.delivery_partner_id=dp.id
        ORDER BY o.created_at DESC""").fetchall()
    c.close()
    result=[]
    for r in rows:
        d=dict(r); d["items"]=json.loads(d["items"]); result.append(d)
    return result

@app.get("/orders/user/{uid}")
def user_orders(uid:int):
    c=db()
    rows=c.execute("""SELECT o.*, dp.name as partner_name, dp.phone as partner_phone
        FROM orders o LEFT JOIN delivery_partners dp ON o.delivery_partner_id=dp.id
        WHERE o.user_id=? ORDER BY o.created_at DESC""",(uid,)).fetchall()
    c.close()
    return [dict(r)|{"items":json.loads(r["items"])} for r in rows]

@app.put("/orders/{oid}/status")
def update_status(oid:int, body:StatusUpdate):
    c=db(); c.execute("UPDATE orders SET status=? WHERE id=?",(body.status,oid)); c.commit(); c.close()
    return {"message":"Status updated"}

@app.put("/orders/{oid}/assign-delivery")
def assign_delivery(oid:int, body:AssignDelivery):
    c=db()
    c.execute("UPDATE orders SET delivery_partner_id=?,status='out_for_delivery' WHERE id=?",(body.delivery_partner_id,oid))
    c.commit(); c.close()
    return {"message":"Delivery partner assigned!"}

@app.delete("/orders/{oid}")
def delete_order(oid:int):
    c=db(); c.execute("DELETE FROM orders WHERE id=?",(oid,)); c.commit(); c.close(); return {"message":"Deleted"}

# ── Delivery Partners ─────────────────────────────────────────────────────
@app.get("/delivery-partners")
def get_partners():
    c=db(); rows=c.execute("SELECT * FROM delivery_partners WHERE status='active'").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.get("/delivery-partners/all")
def all_partners():
    c=db(); rows=c.execute("SELECT * FROM delivery_partners ORDER BY name").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/delivery-partners")
def add_partner(p: DeliveryPartnerCreate):
    c=db(); c.execute("INSERT INTO delivery_partners (name,phone,vehicle) VALUES (?,?,?)",(p.name,p.phone,p.vehicle)); c.commit(); c.close()
    return {"message":"Partner added"}

@app.put("/delivery-partners/{pid}/toggle")
def toggle_partner(pid:int):
    c=db()
    curr=c.execute("SELECT status FROM delivery_partners WHERE id=?",(pid,)).fetchone()
    new_status="inactive" if curr['status']=='active' else "active"
    c.execute("UPDATE delivery_partners SET status=? WHERE id=?",(new_status,pid)); c.commit(); c.close()
    return {"message":f"Partner {new_status}"}

@app.delete("/delivery-partners/{pid}")
def delete_partner(pid:int):
    c=db(); c.execute("DELETE FROM delivery_partners WHERE id=?",(pid,)); c.commit(); c.close()
    return {"message":"Deleted"}

# ── Admin ─────────────────────────────────────────────────────────────────
@app.post("/admin/login")
def admin_login(body:AdminLogin):
    c=db(); pw=hashlib.sha256(body.password.encode()).hexdigest()
    row=c.execute("SELECT * FROM admin_users WHERE username=? AND password=?",(body.username,pw)).fetchone(); c.close()
    if not row: raise HTTPException(401,"Invalid credentials")
    return {"token":"sara-admin-2024","message":"Login successful"}

@app.get("/stats")
def get_stats():
    c=db()
    t=c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    p=c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    done=c.execute("SELECT COUNT(*) FROM orders WHERE status='completed'").fetchone()[0]
    rev=c.execute("SELECT SUM(total) FROM orders WHERE status='completed'").fetchone()[0] or 0
    prods=c.execute("SELECT COUNT(*) FROM products WHERE available=1").fetchone()[0]
    today=c.execute("SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now')").fetchone()[0]
    users=c.execute("SELECT COUNT(*) FROM users WHERE is_verified=1").fetchone()[0]
    delivery=c.execute("SELECT COUNT(*) FROM delivery_partners WHERE status='active'").fetchone()[0]
    c.close()
    return {"total_orders":t,"pending_orders":p,"completed_orders":done,"total_revenue":rev,
            "active_products":prods,"today_orders":today,"total_users":users,"active_delivery_partners":delivery}
