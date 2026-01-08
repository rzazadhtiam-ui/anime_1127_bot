# ================================================================
# self_userbot_render.py — FINAL STABLE VERSION FOR RENDER
# ================================================================

import sys
import os
import json
import asyncio
import logging
import time
import threading
from typing import Dict

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from flask import Flask

# ------------------------------------------------
# PATH FIX
# ------------------------------------------------
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

MONGO_URI = os.environ.get("MONGO_URI") or (
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
logger = logging.getLogger("self_userbot")

# ================================================================
# FLASK (FOR RENDER HEALTH CHECK)
# ================================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Self Nix Bot is running"

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
# MONGO
# ================================================================

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
sessions_col = db[COLLECTION_NAME]

# ================================================================
# ACTIVE CLIENTS
# ================================================================

active_clients: Dict[str, TelegramClient] = {}

async def load_sessions():
    try:
        return list(sessions_col.find({"enabled": True}))
    except PyMongoError as e:
        logger.error(f"Mongo error: {e}")
        return []

# ================================================================
# HANDLERS
# ================================================================

def create_handlers(client: TelegramClient, owner_id: int):
    @client.on(events.NewMessage)
    async def router(event):
        uid = event.sender_id
        text = (event.raw_text or "").strip()

        if not is_enabled(uid):
            if text == ".روشن":
                set_enabled(uid, True)
                await event.reply("✅ ربات روشن شد.")
            return

        if text == ".خاموش":
            set_enabled(uid, False)
            await event.reply("⏸ ربات خاموش شد.")
            return

        if uid == ADMIN_ID and text == ".وضعیت":
            msg = "📊 سشن‌های فعال:\n"
            for k in active_clients.keys():
                msg += f"• {k}\n"
            await event.reply(msg)

        if text == ".پینگ":
            t0 = time.time()
            m = await event.reply("⏳")
            await m.edit(f"🏓 {int((time.time()-t0)*1000)}ms")

# ================================================================
# SESSION STARTER
# ================================================================

async def start_session(doc):
    name = doc.get("session_name") or doc.get("phone")
    if name in active_clients:
        return

    try:
        client = TelegramClient(
            StringSession(doc["session_string"]),
            cfg.api_id,
            cfg.api_hash,
        )

        await client.start()
        me = await client.get_me()

        logger.info(f"Session started: {me.id}")

        register(client)
        create_handlers(client, me.id)
        register_handlers(client)
        register_group_handlers(client)
        register_clock(client)
        self_tools(client)

        status_bot = SelfStatusBot(client)
        asyncio.create_task(status_bot.start())

        active_clients[name] = client
        asyncio.create_task(client.run_until_disconnected())

    except Exception as e:
        logger.error(f"Session failed {name}: {e}")

# ================================================================
# WATCHER
# ================================================================

async def session_watcher():
    while True:
        docs = await load_sessions()
        for doc in docs:
            await start_session(doc)
        await asyncio.sleep(30)

# ================================================================
# MAIN LOOP
# ================================================================

async def main():
    logger.info("Bot core started")
    asyncio.create_task(session_watcher())
    while True:
        await asyncio.sleep(3600)

# ================================================================
# BACKGROUND THREAD (IMPORTANT)
# ================================================================

def start_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

threading.Thread(
    target=start_background,
    daemon=True
).start()
