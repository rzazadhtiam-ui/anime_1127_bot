# ================================================================
# Telegram Session Builder - Flask + Telethon + MongoDB
# Only for creating sessions
# By: Tiam
# ================================================================

import asyncio
import threading
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from pymongo import MongoClient
from datetime import datetime

# ================= CONFIG =================
API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"

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

# ================= API ROUTES =================

# 1 - ارسال شماره برای OTP
@app.route("/send_phone", methods=["POST"])
def send_phone():
    phone = request.json.get("phone")
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
        return jsonify({"status":"ok","message":"کد OTP ارسال شد"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

# 2 - ارسال کد OTP
@app.route("/send_code", methods=["POST"])
def send_code():
    data = request.json
    phone = data.get("phone")
    code = data.get("code")
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت پیدا نشد"})
    
    async def task():
        try:
            await client.sign_in(phone=phone, code=code)
            session_str = client.session.save()
            # ذخیره در MongoDB فقط
            doc = {
                "phone": phone,
                "created_at": datetime.utcnow(),
                "enabled": True,
                "session_string": session_str
            }
            sessions_col.update_one({"phone": phone}, {"$set": doc}, upsert=True)
            return {"status":"ok","message":"سشن ساخته شد"}
        except SessionPasswordNeededError:
            return {"status":"2fa","message":"رمز دو مرحله‌ای لازم است"}
        except PhoneCodeInvalidError:
            return {"status":"error","message":"کد OTP اشتباه است"}
        except Exception as e:
            return {"status":"error","message":str(e)}

    return jsonify(run_async(task()))

# 3 - ارسال 2FA (در صورت نیاز)
@app.route("/send_2fa", methods=["POST"])
def send_2fa():
    data = request.json
    phone = data.get("phone")
    password = data.get("password")
    client = clients.get(phone)
    if not client:
        return jsonify({"status":"error","message":"کلاینت پیدا نشد"})
    
    async def task():
        try:
            await client.sign_in(password=password)
            session_str = client.session.save()
            doc = {
                "phone": phone,
                "created_at": datetime.utcnow(),
                "enabled": True,
                "session_string": session_str
            }
            sessions_col.update_one({"phone": phone}, {"$set": doc}, upsert=True)
            return {"status":"ok","message":"سشن ساخته شد و ورود کامل شد"}
        except Exception as e:
            return {"status":"error","message":str(e)}

    return jsonify(run_async(task()))

# ================= RUN APP =================
if __name__ == "__main__":
    print("Server running on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000)
