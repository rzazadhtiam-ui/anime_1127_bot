# ================================================================
# self_userbot_render_fixed.py — FIXED & POWER SAFE (LIVE ERRORS + FULL POWER CHECK)
# ================================================================


import os
import sys
import time
import asyncio
import logging
import threading
from typing import Dict
from datetime import datetime

from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from Update1 import register_update1
from multi_lang import register_language_commands
from Update2 import register_self_nix_system
#from self_AI import register_self_AI
from mirror_bridge import register_mirror, register_commands
from full_ai_autopilot import register_autopilot
# ------------------------------------------------
# PATH FIX
# ------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from all_imports import (
    self_config,
    self_tools,
    register_handlers,
    register_group_handlers,
    register_clock,
    SelfStatusBot,
    register,
)

# ================================================================
# CONFIG
# ================================================================
cfg = self_config()

MONGO_URI = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

DB_NAME = "telegram_sessions"
COLLECTION_NAME = "sessions"

ADMIN_ID = 6433381392

SESSION_DIR = "sessions"
USER_DATA_DIR = "user_data"

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SELF-NIX")

# ================================================================
# FLASK (KEEP ALIVE + LIVE ERRORS + CLEAR BUTTON)
# ================================================================
app = Flask(__name__)
live_errors = []

@app.route("/")
def home():
    return "Self Nix Bot is running ✅"

@app.route("/errors")
def show_errors():
    if not live_errors:
        return "هیچ خطایی ثبت نشده ✅"
    html = "<h2>لیست خطاهای سشن‌ها</h2>"
    for e in live_errors:
        html += f"<b>{e['session_name']}</b> | ساخته شده: {e['created_at']} | مشکل: {e['reason']}<br>"
    html += '<br><a href="/errors/clear">پاک کردن خطاها</a>'
    return html

@app.route("/errors/clear")
def clear_errors():
    global live_errors
    live_errors = []
    return "تمام خطاها پاک شدند ✅"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

async def notify_error_fa(session_name, created_at, reason):
    entry = {
        "session_name": session_name,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason
    }
    live_errors.append(entry)
    if len(live_errors) > 50:
        live_errors.pop(0)

    # پاک کردن سشن خراب از active_clients و MongoDB
    if session_name in active_clients:
        client = active_clients[session_name]
        try:
            await client.disconnect()
        except:
            pass
        del active_clients[session_name]
        started_sessions.discard(session_name)

    sessions_col.update_one(
        {"session_name": session_name},
        {"$set": {"enabled": False}}
    )

# ================================================================
# ADVANCED SELF KEEP ALIVE (PRODUCTION SAFE)
# ================================================================
import aiohttp

class SelfKeepAlive:

    def __init__(self, logger):
        self.logger = logger
        self.fail_count = 0
        self.max_fail = 3
        self.url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("APP_URL") or "http://localhost:5000"
        self.normal_interval = 240
        self.fail_interval = 60

    async def ping(self):
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.url) as resp:
                return resp.status

    async def run(self):
        await asyncio.sleep(15)
        self.logger.info(f"🌐 KeepAlive started -> {self.url}")
        while True:
            try:
                status = await self.ping()
                if status == 200:
                    if self.fail_count > 0:
                        self.logger.info("✅ KeepAlive recovered")
                    self.fail_count = 0
                    self.logger.info("🏓 KeepAlive OK")
                    await asyncio.sleep(self.normal_interval)
                else:
                    raise Exception(f"Bad status {status}")
            except Exception as e:
                self.fail_count += 1
                self.logger.warning(f"⚠️ KeepAlive failed ({self.fail_count}) -> {e}")
                if self.fail_count >= self.max_fail:
                    self.logger.error("🚨 KeepAlive multiple failures")
                await asyncio.sleep(self.fail_interval)

# ================================================================
# DATABASE
# ================================================================
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
sessions_col = db[COLLECTION_NAME]

# ================================================================
# ACTIVE CLIENTS
# ================================================================
active_clients: Dict[str, TelegramClient] = {}
started_sessions = set()

# ================================================================
# SESSION STARTER (POWER CHECK ADDED)
# ================================================================
async def start_session(doc):
    name = doc.get("session_name") or doc.get("phone")
    session_str = doc.get("session_string")
    created_at = doc.get("created_at") or datetime.now()

    if doc.get("power", "on") == "off":
        logger.info(f"⏹ Session {name} is OFF (power flag)")
        return

    if not session_str or name in started_sessions:
        logger.info(f"⏹ Skipping {name}, already started or no session_string")
        return

    try:
        logger.info(f"🌐 Trying to start session: {name}")
        client = TelegramClient(
            StringSession(session_str),
            cfg.api_id,
            cfg.api_hash,
        )
        await client.start()
        me = await client.get_me()
        client.session_name = name
        logger.info(f"✅ Session online: {me.first_name} ({me.id})")
        await client.send_message("me", "ربات ⦁ Self Nix برای شما فعال شد ✅")

        # ثبت هندلرها و ابزارها
        register_self_nix_system(client)
        register(client)
        create_handlers(client)
        register_handlers(client)
        register_group_handlers(client, me.id)
        register_update1(client)
        register_clock(client)
        self_tools(client)
        register_language_commands(client)
        #register_self_AI(client)
        register_mirror(client)
        register_commands(client)
        register_autopilot(client)
        started_sessions.add(name)
        

        # استارت status bot
        status_bot = SelfStatusBot(client)
        asyncio.create_task(status_bot.start())

        active_clients[name] = client
        

        # آپدیت MongoDB
        sessions_col.update_one(
            {"session_name": name},
            {"$set": {"enabled": True, "power": "on", "last_start": datetime.now()}},
            upsert=True
        )

    except Exception as e:
        reason = ""
        err_str = str(e)
        if "PhoneCode" in err_str:
            reason = "کد تایید منقضی شده یا اشتباه است"
        elif "Auth" in err_str:
            reason = "مشکل احراز هویت"
        elif "Connection" in err_str:
            reason = "مشکل اتصال به سرور تلگرام"
        else:
            reason = f"خطای نامشخص: {err_str}"

        await notify_error_fa(name, created_at, reason)
        logger.error(f"❌ Broken session {name}: {reason}")

# ================================================================
# HANDLERS
# ================================================================
def create_handlers(client: TelegramClient):
    @client.on(events.NewMessage)
    async def router(event):
        try:
            uid = event.sender_id
            text = (event.raw_text or "").strip()

            doc = sessions_col.find_one({"session_name": getattr(client, "session_name", None)})
            if doc and doc.get("power", "on") == "off":
                return  # خاموش بودن power فقط پیام‌ها را نادیده می‌گیرد

            if uid == ADMIN_ID and text in (".وضعیت", ".وضغیت"):
                msg = "📊 سشن‌های فعال:\n"
                for k in active_clients:
                    msg += f"• {k}\n"
                await event.reply(msg)
                return

            if text == ".پینگ":
                t = time.time()
                m = await event.reply("⏳")
                await m.edit(f"🏓 {int((time.time() - t)*1000)}ms")

        except Exception as e:
            created_at = datetime.now()
            await notify_error_fa(getattr(client, "session_name", "Handler"), created_at, f"خطای هندلر: {str(e)}")
            logger.error(f"Handler error: {e}")

# ================================================================
# SESSION WATCHER
# ================================================================
async def session_watcher():
    logger.info("🔄 Session watcher started")
    while True:
        try:
            docs = list(sessions_col.find({"session_string": {"$exists": True}}))

            for doc in docs:
                name = doc.get("session_name") or doc.get("phone")

                if doc.get("power", "on") == "off":
                    if name in active_clients:
                        logger.info(f"⏹ Power OFF -> Disconnecting {name}")
                        try:
                            await active_clients[name].disconnect()
                        except:
                            pass
                        del active_clients[name]
                        started_sessions.discard(name)
                    continue

                await start_session(doc)

        except PyMongoError as e:
            logger.error(f"Mongo error: {e}")
        except Exception as e:
            logger.error(f"Watcher error: {e}")

        await asyncio.sleep(15)

# ================================================================
# MAIN
# ================================================================
async def main():
    logger.info("🚀 Self Nix Bot started")
    asyncio.create_task(session_watcher())
    keep_alive = SelfKeepAlive(logger)
    asyncio.create_task(keep_alive.run())

    while True:
        await asyncio.sleep(60)

# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
