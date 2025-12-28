# ===========================
# self_userbot.py — SAFE MULTI-SESSION WITH WEBHOOK
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

# --------------------------
# کانفیگ
# --------------------------
cfg = self_config()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_userbot")

USER_DATA_DIR = "user_data"
SESSION_DIR = "sessions"

os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)

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
# سشن‌ها
# --------------------------
def get_sessions():
    return [
        os.path.join(SESSION_DIR, f)
        for f in os.listdir(SESSION_DIR)
        if f.endswith(".session")
    ]

# --------------------------
# هندلرها
# --------------------------
def create_handlers(client, owner_id, admin_id):
    @client.on(events.NewMessage)
    async def main_router(event):
        uid = event.sender_id
        text = event.raw_text.strip()

        # فقط مالک اصلی دستور وضعیت رو ببینه
        if uid == admin_id and text == ".وضعیت":
            status_text = "📊 وضعیت کاربران:\n"
            sessions = get_sessions()
            for s in sessions:
                client_name = os.path.basename(s)
                try:
                    me = await client.get_me()
                    enabled = "✅ فعال" if is_user_enabled(me.id) else "⏸ غیرفعال"
                    status_text += f"{client_name} | {me.first_name} ({me.id}) → {enabled}\n"
                except:
                    status_text += f"{client_name} → ❌ خطا\n"
            await event.reply(status_text)
            return

        # اگر کاربر خاموش کرده، فقط روشن بشه
        if not is_user_enabled(uid):
            if text == ".روشن":
                set_user_enabled(uid, True)
                await event.reply("✅ ربات برای شما روشن شد.")
            return

        # دستورات معمول
        if text == ".خاموش":
            set_user_enabled(uid, False)
            await event.reply("⏸ ربات برای شما خاموش شد.")
            return

        if text == ".پینگ":
            t0 = time.time()
            msg = await event.reply("⏳ در حال اندازه‌گیری پینگ...")
            t1 = time.time()
            await msg.edit("🏓 پینگ در حال محاسبه...")
            t2 = time.time()

            ping_send = int((t1 - t0) * 1000)
            ping_edit = int((t2 - t1) * 1000)
            ping_total = int((t2 - t0) * 1000)

            await msg.edit(f"""
🏓 پینگ ارسال پیام: {ping_send}ms
✏️ پینگ ویرایش پیام: {ping_edit}ms
⏱ کل پینگ ربات: {ping_total}ms
""")

# --------------------------
# اجرای اصلی
# --------------------------
async def main():
    admin_id = 123456789  # ← آیدی مالک اصلی
    sessions = get_sessions()
    if not sessions:
        sessions = [os.path.join(SESSION_DIR, "new_session")]

    clients = []

    for s in sessions:
        client = TelegramClient(s, cfg.api_id, cfg.api_hash)
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ {me.first_name} فعال شد")

        create_handlers(client, me.id, admin_id)
        register_handlers(client)
        register_group_handlers(client)
        self_tools(client)

        clients.append(client)

    # وب‌هوک داخلی: همه سشن‌ها با event-driven مدیریت می‌شوند و loop سبک ندارند
    await asyncio.gather(*(c.run_until_disconnected() for c in clients))

if __name__ == "__main__":
    asyncio.run(main())
