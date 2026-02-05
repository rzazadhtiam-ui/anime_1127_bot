import asyncio
import os
import re
import tempfile
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError
from datetime import datetime
import pytz

# ================= CONFIG =================

API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"
SESSION_NAME = "selfbot"

OWNER_ID = 6433381392   # فقط این شخص اجازه استفاده دارد

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
IRAN_TZ = pytz.timezone("Asia/Tehran")


# ================= UTILS =================

def iran_time():
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")


async def edit_status(msg, link, status, progress=0):
    try:
        await msg.edit(
            f"لینک ویدئو: {link}\n"
            f"وضعیت: {status}\n"
            f"پیشرفت: {progress}%\n"
            f"تاریخ: {iran_time()}"
        )
    except:
        pass


# -------- لینک parser --------

def parse_link(link):

    # private channel
    m_private = re.match(r"https://t\.me/c/(\d+)/(\d+)", link)
    if m_private:
        channel_id = int("-100" + m_private.group(1))
        msg_id = int(m_private.group(2))
        return channel_id, msg_id

    # public channel
    m_public = re.match(r"https://t\.me/([\w_]+)/(\d+)", link)
    if m_public:
        return m_public.group(1), int(m_public.group(2))

    return None, None


# ================= TEMP SAVE =================

async def temp_save_media(message, reply_to, link):

    if not message.media:
        return False, "مدیا ندارد"

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:

        # دانلود
        await message.download_media(
            file=temp_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال دانلود", int(d * 100 / t))
            )
        )

        # ارسال به سیو مسیج
        await client.send_file(
            "me",
            temp_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال آپلود", int(d * 100 / t))
            )
        )

        return True, "ذخیره شد ✅"

    except Exception as e:
        return False, f"خطا: {e}"

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ================= EVENT =================

@client.on(events.NewMessage(pattern=r'^\.save (.+)'))
async def handler(event):

    # فقط اگر PV باشد
    if not event.is_private:
        return

    # فقط اگر مالک باشد
    if event.sender_id != OWNER_ID:
        return

    link = event.pattern_match.group(1)
    msg = event.message

    await edit_status(msg, link, "در حال پردازش", 0)

    entity, msg_id = parse_link(link)

    if not entity:
        await edit_status(msg, link, "لینک نامعتبر", 0)
        return

    try:

        entity_obj = await client.get_entity(entity)
        target_msg = await client.get_messages(entity_obj, ids=msg_id)

        if not target_msg:
            await edit_status(msg, link, "پیام پیدا نشد", 0)
            return

        ok, text = await temp_save_media(target_msg, msg, link)
        await edit_status(msg, link, text, 100)

    except ChannelPrivateError:
        await edit_status(msg, link, "دسترسی ندارید", 0)

    except FloodWaitError as f:
        await edit_status(msg, link, f"FloodWait {f.seconds}s", 0)

    except Exception as e:
        await edit_status(msg, link, str(e), 0)
#===============================================
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ================= MAIN =================

async def main():
    await client.start()
    print("Selfbot Active")
    await client.run_until_disconnected()


asyncio.run(main())
