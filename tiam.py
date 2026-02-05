import asyncio
import os
import re
import tempfile
import threading
import requests
import time

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.types import PeerChannel
from datetime import datetime
import pytz

from flask import Flask

# ================= CONFIG =================

API_ID = 24645053
API_HASH = "88c0167b74a24fac0a85c26c1f6d1991"
SESSION_NAME = "selfbot"

SOURCE_CHAT = 6433381392  # جایی که لینک‌ها را می‌فرستی

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
IRAN_TZ = pytz.timezone("Asia/Tehran")

download_queue = asyncio.Queue()

# ================= TIME =================

def iran_time():
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ================= LINK PARSER =================

def parse_link(link):

    m_private = re.match(r"https://t.me/c/(\d+)/(\d+)", link)
    if m_private:
        return ("private", int(m_private.group(1)), int(m_private.group(2)))

    m_public = re.match(r"https://t.me/([\w_]+)/(\d+)", link)
    if m_public:
        return ("public", m_public.group(1), int(m_public.group(2)))

    return None, None, None

# ================= DOWNLOAD + SAVE =================

async def download_and_save(link):

    link_type, identifier, msg_id = parse_link(link)

    if not identifier:
        print("Invalid Link")
        return

    try:

        if link_type == "public":
            entity = await client.get_entity(identifier)
        else:
            entity = await client.get_entity(PeerChannel(identifier))

        message = await client.get_messages(entity, ids=msg_id)

        if not message:
            print("Message not found")
            return

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file_path = tmp.name

        print("Downloading:", link)

        await message.download_media(file=file_path)

        print("Uploading to Saved Messages")

        await client.send_file("me", file_path)

        os.remove(file_path)

        print("Completed:", link)

    except FloodWaitError as f:
        print("FloodWait:", f.seconds)
        await asyncio.sleep(f.seconds)

    except ChannelPrivateError:
        print("No access to channel")

    except Exception as e:
        print("Error:", e)

# ================= QUEUE WORKER =================

async def queue_worker():

    while True:

        link = await download_queue.get()

        await download_and_save(link)

        download_queue.task_done()

# ================= READ LINKS =================

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def read_links(event):

    text = event.raw_text

    links = re.findall(r"https://t.me/\S+", text)

    for link in links:
        await download_queue.put(link)
        print("Added to Queue:", link)

# ================= FLASK KEEP ALIVE =================

app = Flask(__name__)

@app.route("/")
def home():
    return "SelfBot Running"

@app.route("/health")
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ================= AUTO PING =================

def auto_ping():

    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")
            if url:
                requests.get(url)
        except:
            pass

        time.sleep(300)

# ================= MAIN =================

async def start_bot():

    await client.start()

    print("SelfBot Started")

    asyncio.create_task(queue_worker())

    await client.run_until_disconnected()

if __name__ == "__main__":

    threading.Thread(target=run_flask).start()
    threading.Thread(target=auto_ping).start()

    asyncio.run(start_bot())
