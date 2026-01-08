# ================================================================
# self_userbot.py — SAFE MULTI SESSION + MONGODB (FINAL FIXED)
# ================================================================

import os
import json
import asyncio
import logging
import time
from typing import Dict

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from pymongo.errors import PyMongoError

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

DB_NAME = "sessions_db"
COLLECTION_NAME = "sessions"

ADMIN_ID = 6433381392

SESSION_DIR = "sessions"
USER_DATA_DIR = "user_data"

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_userbot")

# ================================================================
# USER STATE (ON / OFF PER USER)
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
# MONGODB
# ================================================================

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
sessions_col = db[COLLECTION_NAME]

# ================================================================
# SESSION MANAGER
# ================================================================

active_clients: Dict[str, TelegramClient] = {}

async def load_sessions_from_mongo():
    try:
        return list(sessions_col.find({"enabled": True}))
    except PyMongoError as e:
        logger.error(f"Mongo error: {e}")
        return []

async def start_session(doc):
    # اگر session_name وجود نداشت، از شماره استفاده کن
    name = doc.get("session_name") or doc.get("phone")
    session_str = doc["session_string"]

    if name in active_clients:
        return

    try:
        client = TelegramClient(
            StringSession(session_str),
            cfg.api_id,
            cfg.api_hash,
        )

        await client.start()
        me = await client.get_me()

        logger.info(f"✅ Session loaded: {me.first_name} ({me.id})")

        # پیام خوش‌آمد فقط یک بار
        await client.send_message(
            "me",
            f"کاربر گرامی {me.first_name} عزیز\nربات ⦁ Self Nix برای شما فعال شد"
        )

        # ثبت هَندلرها و ابزارها
        register(client)
        create_handlers(client, me.id)
        register_handlers(client)
        register_group_handlers(client)
        register_clock(client)
        self_tools(client)

        # استارت وضعیت خودکار
        status_bot = SelfStatusBot(client)
        asyncio.create_task(status_bot.start())

        active_clients[name] = client
        asyncio.create_task(client.run_until_disconnected())

    except Exception as e:
        logger.warning(f"❌ Failed session {name}: {e}")
        # پیام به پیوی شما اگر سشن خراب بود
        try:
            admin_client = TelegramClient(
                StringSession("YOUR_ADMIN_SESSION_STRING"),  # سشن شما
                cfg.api_id,
                cfg.api_hash,
            )
            await admin_client.start()
            await admin_client.send_message(ADMIN_ID, f"⚠️ سشن خراب: {name}\nخطا: {e}")
            await admin_client.disconnect()
        except:
            logger.error("❌ Failed to notify admin about broken session.")

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
            await event.reply("⏸ ربات کاملاً خاموش شد.")
            return

        if uid == ADMIN_ID and text == ".وضعیت":
            msg = "📊 وضعیت سشن‌ها:\n"
            for k in active_clients.keys():
                msg += f"• {k}\n"
            await event.reply(msg)
            return

        if text == ".پینگ":
            t0 = time.time()
            m = await event.reply("⏳")
            t1 = time.time()
            await m.edit(f"🏓 {int((t1 - t0) * 1000)}ms")

# ================================================================
# SESSION WATCHER (AUTO RELOAD)
# ================================================================

async def session_watcher():
    while True:
        try:
            docs = await load_sessions_from_mongo()
            for doc in docs:
                await start_session(doc)
        except Exception as e:
            logger.error(f"Session watcher error: {e}")
        await asyncio.sleep(30)  # هر ۳۰ ثانیه بررسی سشن جدید

# ================================================================
# MAIN
# ================================================================

async def main():
    logger.info("🚀 Bot started. Waiting for sessions from MongoDB...")
    asyncio.create_task(session_watcher())
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
