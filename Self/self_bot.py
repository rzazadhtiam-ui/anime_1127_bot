
# ===========================
# self_userbot.py — SAFE MULTI-SESSION (MongoDB)
# ===========================

from all_imports import (
    self_config,
    self_tools,
    register_handlers,
    register_group_handlers,
)
from self_panel import *

import os
import json
import asyncio
import logging
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient

# --------------------------
# کانفیگ
# --------------------------
cfg = self_config()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_userbot")

USER_DATA_DIR = "user_data"
os.makedirs(USER_DATA_DIR, exist_ok=True)

ADMIN_ID = 123456789  # آیدی عددی مالک اصلی

# --------------------------
# MongoDB
# --------------------------
MONGO_URI = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

mongo = MongoClient(MONGO_URI)
db = mongo["telegram_sessions"]
sessions_col = db["sessions"]

# --------------------------
# ابزار داده کاربر
# --------------------------
def get_user_file(user_id):
    return os.path.join(USER_DATA_DIR, f"{user_id}.json")

def load_user_data(user_id):
    if os.path.exists(get_user_file(user_id)):
        with open(get_user_file(user_id), "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(user_id, data):
    with open(get_user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_user_enabled(user_id):
    data = load_user_data(user_id)
    return data.get("enabled", True)

def set_user_enabled(user_id, status: bool):
    data = load_user_data(user_id)
    data["enabled"] = status
    save_user_data(user_id, data)

# --------------------------
# گرفتن سشن‌ها از MongoDB
# --------------------------
def get_sessions_from_db():
    return list(sessions_col.find({}, {"_id": 0, "session": 1}))

# --------------------------
# هندلرها
# --------------------------
def create_handlers(client, owner_id):
    @client.on(events.NewMessage)
    async def main_router(event):
        uid = event.sender_id
        text = event.raw_text.strip()

        # وضعیت فقط برای مالک اصلی
        if uid == ADMIN_ID and text == ".وضعیت":
            status = "📊 وضعیت سشن‌ها:\n\n"
            try:
                me = await client.get_me()
                enabled = "✅ فعال" if is_user_enabled(me.id) else "⏸ غیرفعال"
                status += f"{me.first_name} ({me.id}) → {enabled}\n"
            except:
                status += "❌ خطا در دریافت اطلاعات\n"
            await event.reply(status)
            return

        # اگر خاموش باشد
        if not is_user_enabled(uid):
            if text == ".روشن":
                set_user_enabled(uid, True)
                await event.reply("✅ ربات برای شما روشن شد.")
            return

        if text == ".خاموش":
            set_user_enabled(uid, False)
            await event.reply("⏸ ربات برای شما خاموش شد.")
            return

        if text == ".پینگ":
            t0 = time.time()
            msg = await event.reply("⏳ تست پینگ...")
            t1 = time.time()
            await msg.edit("🏓 در حال محاسبه...")
            t2 = time.time()

            await msg.edit(
                f"🏓 پینگ: {int((t2 - t0) * 1000)}ms"
            )

# --------------------------
# اجرای اصلی
# --------------------------
async def main():
    sessions = get_sessions_from_db()

    if not sessions:
        logger.error("❌ هیچ سشنی در دیتابیس پیدا نشد")
        return

    clients = []

    for s in sessions:
        try:
            string_session = s["session"]
            client = TelegramClient(
                StringSession(string_session),
                cfg.api_id,
                cfg.api_hash
            )

            await client.start()
            me = await client.get_me()

            logger.info(f"✅ {me.first_name} ({me.id}) فعال شد")

            create_handlers(client, me.id)
            register_handlers(client)
            register_group_handlers(client)
            self_tools(client)

            clients.append(client)

        except Exception as e:
            logger.error(f"❌ خطا در لود سشن: {e}")

    await asyncio.gather(*(c.run_until_disconnected() for c in clients))

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    asyncio.run(main())
