# ================================================================
# self_userbot_render.py — FINAL STABLE RENDER VERSION
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

MONGO_URI = "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set")

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
# USER STATE
# ================================================================

def _user_file(uid):
    return os.path.join(USER_DATA_DIR, f"{uid}.json")

def load_user(uid):
    if os.path.exists(_user_file(uid)):
        with open(_user_file(uid), "r", encoding="utf-8") as f:
            return json.load(f)
    return {"enabled": True}

def save_user(uid, data):
    with open(_user_file(uid), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_enabled(uid):
    return load_user(uid).get("enabled", True)

def set_enabled(uid, status: bool):
    data = load_user(uid)
    data["enabled"] = status
    save_user(uid, data)

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

# ================================================================
# SESSION STARTER
# ================================================================

async def start_session(doc):
    name = doc.get("session_name") or doc.get("phone")
    session_str = doc.get("session_string")

    if not session_str or name in active_clients:
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

        await client.send_message(
            "me",
            f"ربات ⦁ Self Nix برای شما فعال شد ✅"
        )

        register(client)
        create_handlers(client)
        register_handlers(client)
        register_group_handlers(client)
        register_clock(client)
        self_tools(client)

        status_bot = SelfStatusBot(client)
        asyncio.create_task(status_bot.start())

        active_clients[name] = client
        asyncio.create_task(client.run_until_disconnected())

    except Exception as e:
        logger.error(f"❌ Session failed {name}: {e}")
        await notify_admin(name, e)

async def notify_admin(name, error):
    if not ADMIN_SESSION_STRING:
        return
    try:
        admin = TelegramClient(
            StringSession(ADMIN_SESSION_STRING),
            cfg.api_id,
            cfg.api_hash,
        )
        await admin.start()
        await admin.send_message(
            ADMIN_ID,
            f"⚠️ سشن خراب:\n{name}\n\n{error}"
        )
        await admin.disconnect()
    except Exception:
        pass

# ================================================================
# HANDLERS
# ================================================================

def create_handlers(client: TelegramClient):
    @client.on(events.NewMessage)
    async def router(event):
        uid = event.sender_id
        text = (event.raw_text or "").strip()

        if not is_enabled(uid):
            if text == ".روشن":
                set_enabled(uid, True)
                await event.reply("✅ ربات روشن شد")
            return

        if text == ".خاموش":
            set_enabled(uid, False)
            await event.reply("⏸ ربات خاموش شد")
            return

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
        await asyncio.sleep(30)

# ================================================================
# MAIN
# ================================================================

async def main():
    logger.info("🚀 Self Nix Bot started")
    asyncio.create_task(session_watcher())
    while True:
        await asyncio.sleep(3600)

# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":
    # Flask thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Telethon loop
    asyncio.run(main())
