import os
import asyncio
import threading
import time
import requests
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from pymongo import MongoClient
from datetime import datetime, timedelta

# ================= CONFIG =================
API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"
TRIAL_DURATION = 1  # 1 day for trial

# ================= MongoDB =================
mongo = MongoClient(
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)
db = mongo.telegram_sessions
sessions_col = db.sessions

# ================= Flask =================
app = Flask(__name__)

# ================= Async Loop =================
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

# ================= Clients =================
clients = {}  # phone: TelegramClient

# ================= Routes =================
@app.route("/", methods=["GET"])
def home():
    return "Server is running", 200

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status":"ok","message":"alive"})

# ---------- Step 1: Send Phone ----------
@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = request.json.get("phone")
    trial = request.json.get("trial", False)  # False = main, True = trial
    if not phone:
        return jsonify({"status":"error","message":"شماره وارد نشده"})
    
    async def task():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        clients[phone] = client
        return True

    try:
        run_async(task())
        return jsonify({"status":"ok","message":"کد OTP ارسال شد","trial":trial})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

# ---------- Step 2: Send OTP Code ----------
@app.route("/send_code", methods=["POST"])
def send_code():
    data = request.json
    phone = data.get("phone")
    code = data.get("code")
    trial = data.get("trial", False)
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت پیدا نشد"})
    
    async def task():
        try:
            await client.sign_in(phone=phone, code=code)
            me = await client.get_me()
            session_str = client.session.save()
            doc = {
                "phone": phone,
                "user_id": me.id,
                "username": me.username if me.username else None,
                "created_at": datetime.utcnow(),
                "enabled": True,
                "power": "on",
                "trial": trial,
                "session_string": session_str
            }
            if trial:
                doc["trial_end"] = datetime.utcnow() + timedelta(days=TRIAL_DURATION)

            sessions_col.update_one({"phone": phone}, {"$set": doc}, upsert=True)

            return {"status":"ok","message":"سشن ساخته شد و آیدی ذخیره شد","user_id": me.id,"trial": trial}

        except SessionPasswordNeededError:
            return {"status":"2fa","message":"رمز دو مرحله‌ای لازم است"}
        except PhoneCodeInvalidError:
            return {"status":"error","message":"کد OTP اشتباه است"}
        except Exception as e:
            return {"status":"error","message":str(e)}

    return jsonify(run_async(task()))

# ---------- Step 3: 2FA Password ----------
@app.route("/send_2fa", methods=["POST"])
def send_2fa():
    data = request.json
    phone = data.get("phone")
    password = data.get("password")
    trial = data.get("trial", False)
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت پیدا نشد"})
    
    async def task():
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            session_str = client.session.save()
            doc = {
                "phone": phone,
                "user_id": me.id,
                "username": me.username if me.username else None,
                "created_at": datetime.utcnow(),
                "enabled": True,
                "power": "on",
                "trial": trial,
                "session_string": session_str
            }
            if trial:
                doc["trial_end"] = datetime.utcnow() + timedelta(days=TRIAL_DURATION)

            sessions_col.update_one({"phone": phone}, {"$set": doc}, upsert=True)

            return {"status":"ok","message":"سشن ساخته شد و آیدی ذخیره شد","user_id": me.id,"trial": trial}

        except Exception as e:
            return {"status":"error","message":str(e)}

    return jsonify(run_async(task()))

# ================= Background Expiration =================
def trial_expiration_worker():
    while True:
        now = datetime.utcnow()
        expired = sessions_col.find({"trial": True, "power": "on", "trial_end": {"$lte": now}})
        for session in expired:
            sessions_col.update_one({"_id": session["_id"]}, {"$set": {"power": "off"}})
            sessions_col.update_one({"_id": session["_id"]}, {"$unset": {"trial_end": ""}})
            print(f"[Trial Expired] Phone: {session['phone']}")
        time.sleep(60)  # check every minute

threading.Thread(target=trial_expiration_worker, daemon=True).start()

# ================= Self Ping =================
def self_ping(url):
    while True:
        try:
            requests.get(url)
        except:
            pass
        time.sleep(240)

# ================= RUN APP =================
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    url = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")
    threading.Thread(target=self_ping, args=(url,), daemon=True).start()
    print(f"Server running on {url}")
    app.run(host="0.0.0.0", port=PORT)
