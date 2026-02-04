# ================================================================
# self_userbot_render.py — FIXED & STABLE
# ================================================================
# Problems fixed:
# - Broken sessions -> notify admin + auto delete from DB
# - Already started sessions will NOT restart
# - No sleep / render-safe keep-alive
# - .خاموش and .روشن commands REMOVED
# ================================================================

import os
import sys
import json
import time
import asyncio
import logging
import threading
from typing import Dict

from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from pymongo.errors import PyMongoError

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
ADMIN_SESSION_STRING = os.environ.get("ADMIN_SESSION_STRING")

SESSION_DIR = "sessions"
USER_DATA_DIR = "user_data"

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SELF-NIX")

# ================================================================
# FLASK (KEEP ALIVE ONLY)
# ================================================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Self Nix Bot is running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ================================================================
# DATABASE
# ================================================================
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
sessions_col = db[COLLECTION_NAME]

# ================================================================
# ACTIVE CLIENTS (ANTI DUPLICATE START)
# ================================================================
active_clients: Dict[str, TelegramClient] = {}
started_sessions = set()   # prevents re-start

# ================================================================
# ADMIN NOTIFY + DELETE BROKEN SESSION
# ================================================================
async def notify_admin_and_delete(name, error, doc_id):
    try:
        if ADMIN_SESSION_STRING:
            admin = TelegramClient(
                StringSession(ADMIN_SESSION_STRING),
                cfg.api_id,
                cfg.api_hash,
            )
            await admin.start()
            await admin.send_message(
                ADMIN_ID,
                f"⚠️ سشن خراب و حذف شد:\n{name}\n\n{error}"
            )
            await admin.disconnect()
    except Exception as e:
        logger.error(f"Admin notify failed: {e}")

    try:
        sessions_col.delete_one({"_id": doc_id})
        logger.info(f"🗑 Deleted broken session: {name}")
    except Exception as e:
        logger.error(f"Delete failed: {e}")

# ================================================================
# SESSION STARTER
# ================================================================
async def start_session(doc):
    name = doc.get("session_name") or doc.get("phone")
    session_str = doc.get("session_string")
    doc_id = doc.get("_id")

    # invalid or already started
    if not session_str or name in started_sessions:
        return

    try:
        client = TelegramClient(
            StringSession(session_str),
            cfg.api_id,
            cfg.api_hash,
        )

        await client.start()
        me = await client.get_me()
        
        
        logger.info(f"✅ Session online: {me.first_name} ({me.id})")
        await client.send_message("me", "ربات ⦁ Self Nix برای شما فعال شد ✅")

        # register systems
        register(client)
        create_handlers(client)
        register_handlers(client)
        register_group_handlers(client)
        register_clock(client)
        self_tools(client)

        status_bot = SelfStatusBot(client)
        asyncio.create_task(status_bot.start())

        active_clients[name] = client
        started_sessions.add(name)

        # run_until_disconnected removed → render-safe

    except Exception as e:
        logger.error(f"❌ Broken session {name}: {e}")
        await notify_admin_and_delete(name, str(e), doc_id)

# ================================================================
# HANDLERS (NO .خاموش / .روشن)
# ================================================================
def create_handlers(client: TelegramClient):
    @client.on(events.NewMessage)
    async def router(event):
        try:
            uid = event.sender_id
            text = (event.raw_text or "").strip()

            # admin status
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
            await notify_admin_and_delete("Handler", str(e), None)

# ================================================================
# SESSION WATCHER
# ================================================================
async def session_watcher():
    logger.info("🔄 Session watcher started")
    while True:
        try:
            docs = list(sessions_col.find({"enabled": True}))
            for doc in docs:
                await start_session(doc)
        except PyMongoError as e:
            logger.error(f"Mongo error: {e}")
        except Exception as e:
            logger.error(f"Watcher error: {e}")

        # anti-sleep loop (render safe)
        await asyncio.sleep(15)

# ================================================================
# MAIN
# ================================================================
async def main():
    logger.info("🚀 Self Nix Bot started")
    asyncio.create_task(session_watcher())

    # never sleep loop
    while True:
        await asyncio.sleep(60)

# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
