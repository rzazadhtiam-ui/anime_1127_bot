import asyncio
import os
import re
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.types import PeerChannel
from datetime import datetime
import pytz
import tempfile  # برای فایل موقت

# ===============================
# CONFIGURATION
# ===============================
API_ID = 24645053
API_HASH = '88c0167b74a24fac0a85c26c1f6d1991'
SESSION_NAME = 'selfbot'

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
IRAN_TZ = pytz.timezone("Asia/Tehran")

# ===============================
# UTILS
# ===============================
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
    """
    لینک پرایوت t.me/c/... یا عمومی t.me/username/... را پارس می‌کند
    """
    m_private = re.match(r'https://t.me/c/(\d+)/(\d+)', link)
    if m_private:
        return ('private', int(m_private.group(1)), int(m_private.group(2)))
    m_public = re.match(r'https://t.me/([\w_]+)/(\d+)', link)
    if m_public:
        return ('public', m_public.group(1), int(m_public.group(2)))
    return None, None, None

async def forward_media(message, reply_to, link):
    """
    دانلود موقت فایل و آپلود به Saved Messages
    """
    media_type = 'unknown'
    if message.video:
        media_type = 'video'
    elif message.photo:
        media_type = 'photo'
    elif message.voice:
        media_type = 'voice'
    elif message.document:
        media_type = 'document'

    if media_type == 'unknown':
        return None, "نوع مدیا پشتیبانی نمی‌شود"

    # استفاده از tempfile برای فایل موقت
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file_path = tmp_file.name

    try:
        await message.download_media(
            file=file_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال دانلود", int(d*100/t))
            )
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, f"خطا در دانلود: {str(e)}"

    try:
        new_msg = await client.send_file(
            'me',  # همیشه Saved Messages
            file_path,
            progress_callback=lambda d, t: asyncio.create_task(
                edit_status(reply_to, link, "در حال آپلود", int(d*100/t))
            )
        )
        os.remove(file_path)  # حذف فایل بعد از آپلود موفق
        return new_msg.id, "عملیات انجام شد"
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, f"خطا در آپلود: {str(e)}"

# ===============================
# EVENT HANDLER
# ===============================
@client.on(events.NewMessage(pattern=r'^.save (.+)'))
async def save_media(event):
    link_text = event.pattern_match.group(1)
    msg = event.message
    await edit_status(msg, link_text, "در حال پردازش", 0)

    link_type, identifier, msg_id = parse_link(link_text)
    if not identifier:
        await edit_status(msg, link_text, "خطا: لینک نامعتبر", 0)
        return

    try:
        if link_type == 'public':
            entity = await client.get_entity(identifier)
        else:
            entity = await client.get_entity(PeerChannel(identifier))

        target_msg = await client.get_messages(entity, ids=msg_id)
        if not target_msg:
            await edit_status(msg, link_text, "خطا: پیام پیدا نشد", 0)
            return

        new_msg_id, status_text = await forward_media(target_msg, msg, link_text)
        if new_msg_id:
            status_text += f"\nID پیام جدید در Saved Messages: {new_msg_id}"
        await edit_status(msg, link_text, status_text, 100)

    except ChannelPrivateError:
        await edit_status(msg, link_text, "خطا: کانال خصوصی یا دسترسی ندارید", 0)
    except FloodWaitError as f:
        await edit_status(msg, link_text, f"خطا: صبر کنید {f.seconds} ثانیه", 0)
    except Exception as e:
        await edit_status(msg, link_text, f"خطا: {str(e)}", 0)

# ===============================
# MAIN
# ===============================
async def main():
    await client.start()
    print("Self Bot آماده است...")
    await client.run_until_disconnected()

asyncio.run(main())
