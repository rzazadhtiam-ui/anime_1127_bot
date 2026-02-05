import asyncio
import os
import tempfile
import threading
import requests
import time
import re
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.types import PeerChannel
from datetime import datetime
import pytz
from flask import Flask
import shutil

# ================= CONFIG =================
API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"
SESSION_NAME = "selfbot"
SOURCE_CHAT = "me"  # پیوی خودت که لینک‌ها را می‌فرستی

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
IRAN_TZ = pytz.timezone("Asia/Tehran")
download_queue = asyncio.Queue()

# ================= TIME =================
def iran_time():
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ================= DOWNLOAD + SEND WITH PROGRESS =================
async def download_and_send(link, part_number):
    try:
        # ================= PARSE LINK =================
        m_private = re.match(r"https://t.me/c/(\d+)/(\d+)", link)
        if not m_private:
            print(f"[{iran_time()}] Invalid Link:", link)
            return
        identifier = int(m_private.group(1))
        msg_id = int(m_private.group(2))

        channel_id = int(f"-100{identifier}")
        entity = await client.get_entity(PeerChannel(channel_id))
        message = await client.get_messages(entity, ids=msg_id)
        if not message or not message.media:
            print(f"[{iran_time()}] Message has no media or not found: {link}")
            return

        # ================= TEMP FILE =================
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = tmp.name

        # ================= SEND START MESSAGE =================
        status_msg = await client.send_message("me", f"لینک: {link}\nوضعیت: درحال دانلود\nشروع دانلود: {iran_time()}\nPart: {part_number}")

        # ================= PROGRESS CALLBACK =================
        def progress_callback(current, total):
            percent = int(current / total * 100)
            asyncio.create_task(status_msg.edit(f"لینک: {link}\nوضعیت: درحال دانلود {percent}%\nشروع دانلود: {iran_time()}\nPart: {part_number}"))

        # ================= DOWNLOAD =================
        await message.download_media(file=temp_path, progress_callback=progress_callback)

        # ================= SEND FILE =================
        await client.send_file("me", temp_path, caption=f"Part {part_number}")

        os.remove(temp_path)

        # ================= UPDATE STATUS =================
        await status_msg.edit(f"لینک: {link}\nوضعیت: دانلود شده ✅\nشروع دانلود: {iran_time()}\nPart: {part_number}")
        print(f"[{iran_time()}] Completed: Part {part_number}")

    except FloodWaitError as f:
        print(f"[{iran_time()}] FloodWait {f.seconds}s")
        await asyncio.sleep(f.seconds)
        await download_queue.put((link, part_number))

    except ChannelPrivateError:
        print(f"[{iran_time()}] Cannot access private channel: {link}")

    except Exception as e:
        print(f"[{iran_time()}] Error:", e, f"Link: {link}")

# ================= QUEUE WORKER =================
async def queue_worker():
    part_counter = 1
    while True:
        link = await download_queue.get()
        await download_and_send(link, part_counter)
        part_counter += 1
        download_queue.task_done()

# ================= READ LINKS =================
@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def read_links(event):
    text = event.raw_text
    links = re.findall(r"https://t.me/\S+", text)
    for link in links:
        await download_queue.put(link)
        print(f"[{iran_time()}] Added to queue:", link)

# ================= FLASK KEEP ALIVE =================
app = Flask(__name__)
@app.route("/")
def home(): return "SelfBot Running"
@app.route("/health")
def health(): return "OK"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ================= AUTO PING =================
def auto_ping():
    url = os.environ.get("PING_URL", "https://anime-1127-bot.onrender.com/")
    while True:
        try: requests.get(url)
        except Exception as e: print(f"[{iran_time()}] Auto Ping Error:", e)
        time.sleep(300)

# ================= MAIN =================
async def start_bot():
    await client.start()
    print(f"[{iran_time()}] SelfBot Started")
    asyncio.create_task(queue_worker())
    await client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_ping, daemon=True).start()
    asyncio.run(start_bot())
