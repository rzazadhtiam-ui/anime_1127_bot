import asyncio
import os
import re
import tempfile
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError
from datetime import datetime
import pytz

API_ID = 24645053
API_HASH = '88c0167b74a24fac0a85c26c1f6d1991'
SESSION_NAME = 'selfbot'

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


def parse_link(link):
    m = re.match(r'https://t\.me/(?:c/)?([\w\-]+)/(\d+)', link)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


# ================= TEMP SAVE =================

async def temp_save_media(message, reply_to, link):

    if not message.media:
        return False, "مدیا وجود ندارد"

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:
        # دانلود موقتی
        await message.download_media(
            file=temp_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال دانلود", int(d * 100 / t))
            )
        )

        # ارسال سریع به Saved Messages
        await client.send_file(
            "me",
            temp_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال آپلود", int(d * 100 / t))
            )
        )

        return True, "ویدئو ذخیره شد"

    except Exception as e:
        return False, f"خطا: {str(e)}"

    finally:
        # حذف تضمینی فایل
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ================= EVENT =================

@client.on(events.NewMessage(pattern=r'^\.save (.+)'))
async def save_media(event):

    link = event.pattern_match.group(1)
    msg = event.message

    await edit_status(msg, link, "در حال پردازش", 0)

    username, msg_id = parse_link(link)
    if not username:
        await edit_status(msg, link, "لینک نامعتبر", 0)
        return

    try:
        entity = await client.get_entity(username)
        target_msg = await client.get_messages(entity, ids=msg_id)

        if not target_msg:
            await edit_status(msg, link, "پیام پیدا نشد", 0)
            return

        ok, text = await temp_save_media(target_msg, msg, link)
        await edit_status(msg, link, text, 100)

    except ChannelPrivateError:
        await edit_status(msg, link, "دسترسی به کانال ندارید", 0)

    except FloodWaitError as f:
        await edit_status(msg, link, f"Flood wait: {f.seconds}", 0)

    except Exception as e:
        await edit_status(msg, link, str(e), 0)


# ================= MAIN =================

async def main():
    await client.start()
    print("Selfbot Running...")
    await client.run_until_disconnected()


asyncio.run(main())
