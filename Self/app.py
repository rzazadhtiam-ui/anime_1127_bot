# ================================================================
# Telegram Session Builder – FULL FINAL VERSION
# Admin Panel + Free & Paid + Accurate Session Storage
# By: Tiam
# ================================================================

import os, asyncio, threading, secrets, time, shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, session as flask_session
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from pymongo import MongoClient
import requests

# ===================== CONFIG ===================================

CONFIG = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-2.onrender.com",
    "device_name": "⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙",
    "secret_key": secrets.token_urlsafe(16)
}

os.makedirs(CONFIG["save_path"], exist_ok=True)

# ===================== Flask App =================================

app = Flask(__name__, static_folder="static")
app.secret_key = CONFIG["secret_key"]

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

# ===================== Async Loop ================================

loop = asyncio.new_event_loop()
threading.Thread(target=lambda: (asyncio.set_event_loop(loop), loop.run_forever()), daemon=True).start()
def run_async(coro): return asyncio.run_coroutine_threadsafe(coro, loop).result()

# ===================== Utils ====================================

clients = {}

def gen_token():
    return secrets.token_urlsafe(8)

def consume_link(token):
    link = links_col.find_one({"token": token})
    if not link: 
        return False
    if link["expire_at"] < datetime.utcnow():
        links_col.delete_one({"token": token})
        return False
    if link["used"] + 1 >= link["max"]:
        links_col.delete_one({"token": token})
    else:
        links_col.update_one({"token": token}, {"$inc": {"used": 1}})
    return True

def normalize_phone(phone):
    phone = phone.strip()
    if phone.startswith("0"): return "+98" + phone[1:]
    if phone.startswith("9") and len(phone) == 10: return "+98" + phone
    return phone

def delete_session(phone):
    path = os.path.join(CONFIG["save_path"], f"{phone}.session")
    if os.path.exists(path): os.remove(path)
    sessions_col.delete_one({"phone": phone})
    client = clients.pop(phone, None)
    if client:
        try: client.disconnect()
        except: pass

def save_session(phone, client):
    """ذخیره دقیق سشن در MongoDB و فایل"""
    session_str = client.session.save()
    file_path = os.path.join(CONFIG["save_path"], f"{phone}.session")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(session_str)
    sessions_col.update_one(
        {"phone": phone},
        {"$set": {"session_string": session_str, "enabled": True, "created": datetime.utcnow()}},
        upsert=True
    )

# ===================== Load Sessions ============================

async def load_all_sessions():
    for s in sessions_col.find({"session_string": {"$exists": True}}):
        phone = s["phone"]
        try:
            client = TelegramClient(
                StringSession(s["session_string"]),
                CONFIG["api_id"],
                CONFIG["api_hash"],
                device_model=CONFIG["device_name"]
            )
            
            clients[phone] = client
            print(f"✅ {phone} فعال شد")
        except Exception as e:
            print(f"❌ مشکل در سشن {phone}: {e}")

# ===================== Client Creation ==========================

async def create_client(phone):
    c = TelegramClient(os.path.join(CONFIG["save_path"], phone), CONFIG["api_id"], CONFIG["api_hash"], device_model=CONFIG["device_name"])
    await c.connect()
    return c

# ===================== Decorators ===============================

def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not flask_session.get("admin"): return redirect("/admin_login")
        return func(*args, **kwargs)
    return wrapper

# ===================== HTML Templates ===========================

ADMIN_HTML = """

<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>پنل مدیریت</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {
    font-family: Tahoma, sans-serif;
    background: #111;
    color: #fff;
    margin: 0;
    padding: 0;
}
.container {
    width: 90%;
    max-width: 900px;
    margin: 30px auto;
}
h2 {
    text-align: center;
    margin-bottom: 20px;
}
.button-row {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-bottom: 20px;
}
button.main-btn {
    padding: 10px 20px;
    cursor: pointer;
    border: none;
    border-radius: 6px;
    background-color: #6366f1;
    color: white;
    font-size: 14px;
    transition: 0.2s;
}
button.main-btn.active {
    background-color: #22c55e;
}
.panel {
    display: none;
    background: rgba(25,25,25,0.95);
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 20px;
    box-shadow: 0 0 10px #222;
    max-height: 400px;
    overflow-y: auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}
th, td {
    border: 1px solid #555;
    padding: 6px;
    text-align: center;
    font-size: 13px;
}
th {
    background: #222;
}
td button {
    padding: 3px 6px;
    cursor: pointer;
    border-radius: 4px;
    border: none;
    margin: 0 2px;
    font-size: 12px;
}
.delete-btn {
    background: #f87171;
    color: white;
}
.copy-btn {
    background: #22c55e;
    color: white;
}
.confirm-overlay {
    display: none;
    position: fixed;
    top:0; left:0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.7);
    justify-content: center;
    align-items: center;
    z-index: 1000;
}
.confirm-box {
    background: #222;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    max-width: 300px;
}
.confirm-box button {
    margin: 10px;
}
input.number-input {
    width: 60px;
    padding: 4px;
    border-radius: 4px;
    border: none;
    text-align: center;
}
</style>
</head>
<body>
<div class="container">
<h2>پنل مدیریت</h2>
<div class="button-row">
    <button class="main-btn" id="manageSessionsBtn">مدیریت سشن</button>
    <button class="main-btn" id="createLinkBtn">ساخت لینک</button>
</div>

<!-- مدیریت سشن -->
<div class="panel" id="sessionsPanel">
<h3>سشن‌ها</h3>
<table id="sessionsTable">
<tr><th>اسم سشن</th><th>تاریخ ساخت</th><th>عملیات</th></tr>
</table>
</div>

<!-- ساخت لینک -->
<div class="panel" id="linksPanel">
<h3>ساخت لینک جدید</h3>
تعداد استفاده: <input type="number" id="linkMax" class="number-input" value="1">
<button class="main-btn" id="createLinkConfirm">ساخت لینک</button>
<h4>لینک‌ها</h4>
<table id="linksTable">
<tr><th>توکن</th><th>استفاده</th><th>حداکثر</th><th>عملیات</th></tr>
</table>
</div>
</div>

<!-- تایید حذف -->
<div class="confirm-overlay" id="confirmOverlay">
<div class="confirm-box">
<p id="confirmText">آیا مطمئن هستید؟</p>
<button class="main-btn" id="confirmYes">بله</button>
<button class="main-btn" id="confirmNo">خیر</button>
</div>
</div>

<script>
let activePanel = null;
let deleteCallback = null;

// باز/بسته کردن پنل
function togglePanel(panelId, button){
    const panel = document.getElementById(panelId);
    if(activePanel === panel){
        panel.style.display='none';
        button.classList.remove('active');
        activePanel = null;
    } else {
        if(activePanel){
            activePanel.panel.style.display='none';
            activePanel.button.classList.remove('active');
        }
        panel.style.display='block';
        button.classList.add('active');
        activePanel = {panel: panel, button: button};
        // وقتی باز شد داده‌ها را از سرور بارگذاری کن
        if(panelId==='sessionsPanel') loadSessions();
        else if(panelId==='linksPanel') loadLinks();
    }
}

// ================== AJAX ===================
async function loadSessions(){
    try{
        const res = await fetch('/admin/get_sessions'); // بک‌اند باید route بسازه
        const data = await res.json();
        renderSessions(data);
    }catch(e){ console.error(e); }
}

async function loadLinks(){
    try{
        const res = await fetch('/admin/get_links'); // بک‌اند باید route بسازه
        const data = await res.json();
        renderLinks(data);
    }catch(e){ console.error(e); }
}

// ================== رندر داده‌ها ===================
function renderSessions(sessionsData){
    const table = document.getElementById('sessionsTable');
    table.innerHTML = '<tr><th>اسم سشن</th><th>تاریخ ساخت</th><th>عملیات</th></tr>';
    sessionsData.forEach(s=>{
        const row = document.createElement('tr');
        row.innerHTML = `<td>${s.name}</td><td>${s.created}</td>
        <td><button class="delete-btn" onclick="confirmDelete('session','${s.name}')">حذف</button></td>`;
        table.appendChild(row);
    });
}

function renderLinks(linksData){
    const table = document.getElementById('linksTable');
    table.innerHTML = '<tr><th>توکن</th><th>استفاده</th><th>حداکثر</th><th>عملیات</th></tr>';
    linksData.forEach(l=>{
        const row = document.createElement('tr');
        row.innerHTML = `<td>${l.token}</td><td>${l.used}</td><td>${l.max}</td>
        <td>
            <button class="delete-btn" onclick="confirmDelete('link','${l.token}')">حذف</button>
            <button class="copy-btn" onclick="copyLink('${l.token}')">کپی</button>
        </td>`;
        table.appendChild(row);
    });
}

// ================== حذف با تایید ===================
function confirmDelete(type, id){
    deleteCallback = async ()=> {
        try{
            await fetch(type==='session'?`/admin/delete_session/${id}`:`/admin/delete_link/${id}`,{method:'POST'});
            if(type==='session') loadSessions();
            else loadLinks();
        }catch(e){ console.error(e); }
    };
    document.getElementById('confirmText').innerText = type==='session'?
        `آیا از حذف سشن ${id} مطمئن هستید؟`:`آیا از حذف لینک ${id} مطمئن هستید؟`;
    document.getElementById('confirmOverlay').style.display='flex';
}

document.getElementById('confirmYes').addEventListener('click', ()=>{
    if(deleteCallback) deleteCallback();
    document.getElementById('confirmOverlay').style.display='none';
});
document.getElementById('confirmNo').addEventListener('click', ()=>{
    document.getElementById('confirmOverlay').style.display='none';
});

// کپی لینک
function copyLink(token){
    navigator.clipboard.writeText(`${window.location.origin}/?key=${token}`);
    alert("لینک کپی شد");
}

// ساخت لینک جدید
document.getElementById('createLinkConfirm').addEventListener('click', async ()=>{
    const max = parseInt(document.getElementById('linkMax').value);
    try{
        await fetch('/admin/create_link',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({max})});
        loadLinks();
    }catch(e){ console.error(e); }
});

// دکمه‌ها
document.getElementById('manageSessionsBtn').addEventListener('click', e=> togglePanel('sessionsPanel', e.target));
document.getElementById('createLinkBtn').addEventListener('click', e=> togglePanel('linksPanel', e.target));
</script>
</body>
</html>
"""

FREE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>self_login</title>
<style>
body {
    margin: 0;
    font-family: tahoma;
    color: white;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
}
#galaxy {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: url('/static/images/astronomy-1867616_1280.jpg') no-repeat center center fixed;
    background-size: cover;
    opacity: 25;
    z-index: -1;
}
#container {
    position: absolute;
    top: 45%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 380px;
    padding: 25px 20px;
    background: rgba(0,0,0,0.55);
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.15);
    backdrop-filter: blur(5px);
    text-align: center;
}
input {
    width: 90%;
    padding: 12px;
    margin-top: 12px;
    border-radius: 10px;
    border: none;
    outline: none;
    font-size: 18px;
}
button {
    width: 94%;
    padding: 13px;
    margin-top: 15px;
    background: #5e5ef7;
    border: none;
    border-radius: 10px;
    font-size: 20px;
    color: white;
    cursor: pointer;
}
h2 { margin-top: 0; }
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

    fetch("/send_phone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone })
    }).then(r => r.json()).then(data => {
        alert(data.message);
        if (data.status === "ok") {
            document.getElementById("step1").style.display = "none";
            document.getElementById("step2").style.display = "block";
        }
    });
}

function sendCode() {
    const code = document.getElementById("code").value.trim();

    fetch("/send_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone_global, code: code })
    }).then(r => r.json()).then(data => {
        if (data.status === "2fa") {
            document.getElementById("step2").style.display = "none";
            document.getElementById("step3").style.display = "block";
        } else if (data.status === "ok") {
            success(data.session_name);
        } else {
            alert(data.message);
        }
    });
}

function sendPassword() {
    const pass = document.getElementById("password").value.trim();

    fetch("/send_password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone_global, password: pass })
    }).then(r => r.json()).then(data => {
        if (data.status === "ok") {
            success(data.session_name);
        } else {
            alert(data.message);
        }
    });
}

function success(name) {
    document.getElementById("step1").style.display = "none";
    document.getElementById("step2").style.display = "none";
    document.getElementById("step3").style.display = "none";

    document.getElementById("result").style.display = "block";
    document.getElementById("msg").innerText = " "
}
</script>

</body>
</html>
"""

PAID_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paid Plans</title>

<style>
body {
    margin: 0;
    font-family: Tahoma;
    background: #0b0b0b;
    color: #fff;
    overflow-x: hidden;
}

.center {
    display: flex;
    justify-content: center;
    align-items: center;
}

/* HELLO ANIMATION */
#hello {
    position: fixed;
    inset: 0;
    background: #000;
    z-index: 999;
    font-size: 42px;
    animation: helloFade 2.5s forwards;
}

@keyframes helloFade {
    0% { opacity: 0; transform: scale(0.8); }
    30% { opacity: 1; transform: scale(1); }
    80% { opacity: 1; }
    100% { opacity: 0; visibility: hidden; }
}

/* SCROLL AREA */
.container {
    margin-top: 40px;
    padding-bottom: 60px;
}

/* CARD */
.card-wrapper {
    perspective: 1200px;
    margin: 40px auto;
    width: 300px;
}

.card {
    width: 100%;
    height: 420px;
    position: relative;
    transform-style: preserve-3d;
    transition: 0.8s;
}

.card.flip {
    transform: rotateY(180deg);
}

.card-face {
    position: absolute;
    inset: 0;
    border-radius: 20px;
    backface-visibility: hidden;
    background: rgba(20,20,20,0.9);
    border: 1px solid rgba(255,255,255,0.15);
    overflow: hidden;
}

/* FRONT */
.card-front img {
    width: 100%;
    height: 65%;
    object-fit: cover;
}

.card-front .title {
    padding: 15px;
    text-align: center;
}

.card-front h3 {
    margin: 5px 0;
}

/* BACK */
.card-back {
    transform: rotateY(180deg);
    padding: 15px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.card-back h2 {
    text-align: center;
    margin-bottom: 10px;
}

.option {
    background: #1f1f1f;
    padding: 10px;
    border-radius: 10px;
    display: flex;
    justify-content: space-between;
    cursor: pointer;
}

.option:hover {
    background: #333;
}

/* CUSTOM */
.custom-box input {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    border: none;
}

.custom-units button {
    width: 100%;
    margin-top: 5px;
    padding: 8px;
    background: #2d2dff;
    border: none;
    color: white;
    border-radius: 8px;
}
</style>
</head>

<body>

<div id="hello" class="center">Hello</div>

<div class="container">

<!-- MONTHLY -->
<div class="card-wrapper">
<div class="card" onclick="this.classList.toggle('flip')">
    <div class="card-face card-front">
        <img src="/static/images/IMG_20260107_224709_712.jpg">
        <div class="title">
            <h3>Monthly</h3>
            <p>ماهانه</p>
        </div>
    </div>

    <div class="card-face card-back">
        <h2>MONTH</h2>
        <div class="option">1 ماهه <span>30,000</span></div>
        <div class="option">2 ماهه <span>60,000</span></div>
        <div class="option">3 ماهه <span>90,000</span></div>
        <div class="option">4 ماهه <span>120,000</span></div>
        <div class="option">5 ماهه <span>150,000</span></div>
    </div>
</div>
</div>

<!-- YEARLY -->
<div class="card-wrapper">
<div class="card" onclick="this.classList.toggle('flip')">
    <div class="card-face card-front">
        <img src="/static/images/IMG_20260107_224710_176.jpg">
        <div class="title">
            <h3>Yearly</h3>
            <p>سالانه</p>
        </div>
    </div>

    <div class="card-face card-back">
        <h2>YEAR</h2>
        <div class="option">1 ساله <span>100,000</span></div>
        <div class="option">2 ساله <span>200,000</span></div>
        <div class="option">3 ساله <span>300,000</span></div>
        <div class="option">4 ساله <span>400,000</span></div>
        <div class="option">5 ساله <span>500,000</span></div>
    </div>
</div>
</div>

<!-- CUSTOM -->
<div class="card-wrapper">
<div class="card" onclick="this.classList.toggle('flip')">
    <div class="card-face card-front">
        <img src="/static/images/IMG_20260107_224710_405.jpg">
        <div class="title">
            <h3>Custom</h3>
            <p>شخصی سازی</p>
        </div>
    </div>

    <div class="card-face card-back">
        <h2>CUSTOM</h2>
        <div class="custom-box">
            <input type="number" placeholder="عدد را وارد کنید">
        </div>
        <div class="custom-units">
            <button>ساعت</button>
            <button>روز</button>
            <button>هفته</button>
            <button>ماه</button>
            <button>سال</button>
        </div>
    </div>
</div>
</div>

</div>

</body>
</html>
"""

# ===================== Routes – Admin ===========================

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if request.form.get("username")==CONFIG["admin_username"] and request.form.get("password")==CONFIG["admin_password"]:
            flask_session["admin"]=True
            return redirect("/admin")
        return "نام کاربری یا رمز اشتباه است"
    return """
    <form method="post">
    <input name="username" placeholder="نام کاربری">
    <input name="password" placeholder="رمز عبور" type="password">
    <button type="submit">ورود</button>
    </form>
    """

@app.route("/admin", methods=["GET","POST"])
@admin_required
def admin():
    if request.method=="POST":
        links_col.insert_one({"token": gen_token(), "max": int(request.form["max"]), "used": 0})
        return redirect("/admin")
    return render_template_string(ADMIN_HTML, links=list(links_col.find()))

@app.route("/admin/delete_link", methods=["POST"])
@admin_required
def del_link():
    links_col.delete_one({"token": request.json["token"]})
    return jsonify(ok=True)

# ===================== Routes – User ============================

@app.route("/")
def home():
    key = request.args.get("key")
    if not key or not consume_link(key):
        return "❌ لینک نامعتبر"
    if "paid" in request.args: return render_template_string(PAID_HTML)
    return render_template_string(FREE_HTML)

@app.route("/ping")
def ping(): return "OK"

@app.route("/check_phone", methods=["POST"])
def check_phone():
    phone = normalize_phone(request.json["phone"])
    return jsonify(status="exists" if sessions_col.find_one({"phone": phone}) else "ok")

@app.route("/delete_session", methods=["POST"])
def del_sess():
    delete_session(normalize_phone(request.json["phone"]))
    return jsonify(ok=True)

@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = normalize_phone(request.json["phone"])
    async def job():
        c = await create_client(phone)
        clients[phone]=c
        await c.send_code_request(phone)
    run_async(job())
    return jsonify(ok=True)

@app.route("/send_code", methods=["POST"])
def send_code():
    phone = normalize_phone(request.json["phone"])
    client = clients.get(phone)
    if not client: return jsonify(status="error", msg="Client not found")
    try:
        run_async(client.sign_in(phone, request.json["code"]))
        save_session(phone, client)
        return jsonify(status="ok")
    except SessionPasswordNeededError: return jsonify(status="2fa")
    except PhoneCodeInvalidError: return jsonify(status="error")
    except Exception as e: return jsonify(status="error", msg=str(e))

@app.route("/send_password", methods=["POST"])
def send_password():
    phone = normalize_phone(request.json["phone"])
    client = clients.get(phone)
    if not client: return jsonify(ok=False, msg="Client not found")
    try:
        run_async(client.sign_in(password=request.json["password"]))
        save_session(phone, client)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, msg=str(e))

@app.route("/register_session_time", methods=["POST"])
def register_time():
    phone = normalize_phone(request.json["phone"])
    created = request.json["created"]
    sessions_col.update_one({"phone": phone}, {"$set":{"created":created}}, upsert=True)
    return jsonify(ok=True)

# ===================== Routes – Admin – GET DATA =====================

@app.route("/admin/get_sessions", methods=["GET"])
@admin_required
def get_sessions():
    sessions = []
    for s in sessions_col.find({}):
        sessions.append({
            "name": s.get("phone", "نامشخص"),
            "created": s.get("created", "نامشخص")
        })
    return jsonify(sessions)

@app.route("/admin/get_links", methods=["GET"])
@admin_required
def get_links():
    links = []
    for l in links_col.find({}):
        links.append({
            "token": l.get("token", "نامشخص"),
            "used": l.get("used", 0),
            "max": l.get("max", 1)
        })
    return jsonify(links)

# ===================== Keep Alive ==============================

def keep_alive():
    while True:
        try: requests.get(CONFIG["base_url"]+"/ping", timeout=10)
        except: pass
        time.sleep(240)

threading.Thread(target=keep_alive, daemon=True).start()

# ===================== Run ======================================

if __name__ == "__main__":
    run_async(load_all_sessions())
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
