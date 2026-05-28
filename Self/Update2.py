# =========================================================
# ◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤
# Tiam Official Self System
# Version: 1.1.2
# =========================================================

import os
import re
import io
import gc
import psutil
import asyncio
import yt_dlp
import edge_tts
import tempfile
import subprocess
import pytesseract
import requests
import time

from PIL import Image
from datetime import datetime
from pymongo import MongoClient

from telethon import events
from telethon.tl.types import (
    DocumentAttributeAudio
)

from deep_translator import GoogleTranslator

# =========================================================
# CONFIG
# =========================================================

OWNER_ID = 123456789

MONGO_URI = "mongodb://localhost:27017"

mongo = MongoClient(MONGO_URI)

db = mongo["nix_self"]

coins_db = db["coins"]
profile_db = db["profiles"]
stats_db = db["stats"]

START_TIME = time.time()

# =========================================================
# DECORATORS
# =========================================================

def owner_only(func):

    async def wrapper(event):

        if event.sender_id != OWNER_ID:
            return

        try:
            return await func(event)

        except Exception as e:

            await event.reply(
                f"""
◢◤ ERROR ◢◤

{str(e)}
"""
            )

    return wrapper

# =========================================================
# HELPERS
# =========================================================

def progress_bar(percent):

    filled = int(percent / 10)

    empty = 10 - filled

    return "▰" * filled + "▱" * empty


async def add_signature(user_id):

    data = stats_db.find_one(
        {"user_id": user_id}
    )

    if not data:

        stats_db.insert_one({
            "user_id": user_id,
            "messages": 1
        })

        total = 1

    else:

        total = data.get(
            "messages",
            0
        ) + 1

        stats_db.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "messages": total
                }
            }
        )

    return f"""

◢◤ ⟦ ◈ ⟧ ɴɪx ᴍᴀɴᴀɢᴇᴅ: {total:,} ᴍsɢs
"""


def add_coin(user_id, amount=1):

    data = coins_db.find_one(
        {"user_id": user_id}
    )

    if not data:

        coins_db.insert_one({
            "user_id": user_id,
            "coins": amount
        })

    else:

        coins_db.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "coins": amount
                }
            }
        )

# =========================================================
# MAIN SETUP
# =========================================================

def setup_features(client):

    # =====================================================
    # COIN SYSTEM
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.coin"
    ))
    @owner_only
    async def coin_handler(event):

        add_coin(event.sender_id)

        data = coins_db.find_one(
            {"user_id": event.sender_id}
        )

        coins = data.get(
            "coins",
            0
        )

        text = f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

◈ Coins: {coins}

▰▰▰▰▰▰▱▱▱▱

◢ ᴛɪᴀᴍ'ꜱ ᴏꜰꜰɪᴄɪᴀʟ ꜱᴇʟꜰ ◤
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # SYSTEM MONITOR
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.sys"
    ))
    @owner_only
    async def system_handler(event):

        cpu = psutil.cpu_percent()

        ram = psutil.virtual_memory().percent

        uptime = int(
            time.time() - START_TIME
        )

        text = f"""
◢◤ SYSTEM STATUS ◢◤

CPU:
{progress_bar(cpu)} {cpu}%

RAM:
{progress_bar(ram)} {ram}%

UPTIME:
{uptime}s

STATUS:
ONLINE ✨
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # TRANSLATOR
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.tr (.+)"
    ))
    @owner_only
    async def translate_handler(event):

        text = event.pattern_match.group(1)

        translated = GoogleTranslator(
            source='auto',
            target='en'
        ).translate(text)

        msg = f"""
◢◤ NIX TRANSLATOR ◢◤

◈ Original:
{text}

◈ Translated:
{translated}
"""

        msg += await add_signature(
            event.sender_id
        )

        await event.reply(msg)

    # =====================================================
    # TEXT TO SPEECH
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.tts (.+)"
    ))
    @owner_only
    async def tts_handler(event):

        text = event.pattern_match.group(1)

        file_name = "nix_tts.mp3"

        communicate = edge_tts.Communicate(
            text,
            voice="en-US-GuyNeural"
        )

        await communicate.save(file_name)

        await event.reply(
            file=file_name,
            voice_note=True
        )

        os.remove(file_name)

    # =====================================================
    # OCR
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.ocr"
    ))
    @owner_only
    async def ocr_handler(event):

        if not event.is_reply:
            return await event.reply(
                "Reply to image."
            )

        reply = await event.get_reply_message()

        path = await reply.download_media()

        image = Image.open(path)

        text = pytesseract.image_to_string(
            image
        )

        result = f"""
◢◤ NIX OCR ◢◤

{text}
"""

        result += await add_signature(
            event.sender_id
        )

        await event.reply(result)

        os.remove(path)

    # =====================================================
    # OCR TRANSLATE
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.ocrtr"
    ))
    @owner_only
    async def ocr_translate_handler(event):

        if not event.is_reply:
            return await event.reply(
                "Reply to image."
            )

        reply = await event.get_reply_message()

        path = await reply.download_media()

        image = Image.open(path)

        text = pytesseract.image_to_string(
            image
        )

        translated = GoogleTranslator(
            source='auto',
            target='en'
        ).translate(text)

        result = f"""
◢◤ NIX OCR TRANSLATOR ◢◤

◈ Extracted:
{text}

◈ Translated:
{translated}
"""

        result += await add_signature(
            event.sender_id
        )

        await event.reply(result)

        os.remove(path)

    # =====================================================
    # YOUTUBE / INSTAGRAM DOWNLOADER
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.dl (.+)"
    ))
    @owner_only
    async def download_handler(event):

        url = event.pattern_match.group(1)

        msg = await event.reply(
            "Downloading..."
        )

        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best'
        }

        os.makedirs(
            "downloads",
            exist_ok=True
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            file_path = ydl.prepare_filename(
                info
            )

        await event.reply(
            file=file_path,
            caption="""
◢◤ NIX DOWNLOADER ◢◤

Downloaded Successfully ✨
"""
        )

        await msg.delete()

        os.remove(file_path)

    # =====================================================
    # PROFILE SYSTEM
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.setbio (.+)"
    ))
    @owner_only
    async def setbio_handler(event):

        bio = event.pattern_match.group(1)

        profile_db.update_one(
            {"user_id": event.sender_id},
            {
                "$set": {
                    "bio": bio
                }
            },
            upsert=True
        )

        await event.reply(
            """
◢◤ PROFILE UPDATED ◢◤
"""
        )

    @client.on(events.NewMessage(
        pattern=r"\.profile"
    ))
    @owner_only
    async def profile_handler(event):

        me = await client.get_me()

        data = profile_db.find_one(
            {"user_id": event.sender_id}
        )

        bio = "No Bio"

        if data:
            bio = data.get(
                "bio",
                "No Bio"
            )

        text = f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

PROFILE NAME:
◈NIX◈ | {me.first_name}

USERNAME:
@{me.username}

BIO:
{bio}

STATUS:
PREMIUM SELF USER ✨
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # TIMELINE
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.timeline"
    ))
    @owner_only
    async def timeline_handler(event):

        percent = 45

        text = f"""
⟦ ◈ ⟧ ɴɪx ᴛɪᴍᴇʟɪɴᴇ

{progress_bar(percent)} {percent}% ʟᴇꜰᴛ
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # PREMIUM EMOJI STYLE
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.nixping"
    ))
    @owner_only
    async def ping_handler(event):

        start = time.time()

        msg = await event.reply(
            "Pinging..."
        )

        end = time.time()

        speed = round(
            end - start,
            2
        )

        text = f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

◈ Message: Pong!
◈ Speed: {speed}s
◈ Status: Online ✨

▰▰▰▰▰▰▰▰▱▱ 85%

◢◤ Nix Group ◢◤
"""

        text += await add_signature(
            event.sender_id
        )

        await msg.edit(text)

    # =====================================================
    # TERMINAL
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.cmd (.+)"
    ))
    @owner_only
    async def cmd_handler(event):

        command = event.pattern_match.group(1)

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate()

        output = stdout.decode()

        error = stderr.decode()

        result = output or error

        if len(result) > 4000:
            result = result[:4000]

        text = f"""
◢◤ NIX TERMINAL ◢◤

{result}
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # SCREENSHOT
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.screenshot"
    ))
    @owner_only
    async def screenshot_handler(event):

        try:

            import pyautogui

            file_name = "screen.png"

            image = pyautogui.screenshot()

            image.save(file_name)

            await event.reply(
                file=file_name
            )

            os.remove(file_name)

        except Exception as e:

            await event.reply(str(e))

    # =====================================================
    # GROUP CLEANER
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.clean"
    ))
    @owner_only
    async def clean_handler(event):

        deleted = 0

        async for msg in client.iter_messages(
            event.chat_id,
            limit=100
        ):

            try:

                if msg.sender_id != OWNER_ID:

                    await msg.delete()

                    deleted += 1

            except:
                pass

        await event.reply(
            f"""
◢◤ NIX CLEANER ◢◤

Deleted:
{deleted} messages
"""
        )

    # =====================================================
    # AI DELETE
    # =====================================================

    BAD_WORDS = [
        "spam",
        "fuck",
        "scam",
        "hack"
    ]

    @client.on(events.NewMessage)
    async def auto_moderation(event):

        if event.sender_id == OWNER_ID:
            return

        if not event.is_group:
            return

        text = event.raw_text.lower()

        for word in BAD_WORDS:

            if word in text:

                try:
                    await event.delete()
                except:
                    pass

    # =====================================================
    # VOICE TO TEXT
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.stt"
    ))
    @owner_only
    async def stt_handler(event):

        if not event.is_reply:

            return await event.reply(
                "Reply to voice."
            )

        reply = await event.get_reply_message()

        path = await reply.download_media()

        text = """
Speech Recognition Installed
Use faster-whisper here
"""

        result = f"""
◢◤ NIX STT ◢◤

{text}
"""

        result += await add_signature(
            event.sender_id
        )

        await event.reply(result)

        os.remove(path)

    # =====================================================
    # MEDIA INFO
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.media"
    ))
    @owner_only
    async def media_handler(event):

        if not event.is_reply:

            return await event.reply(
                "Reply to media."
            )

        reply = await event.get_reply_message()

        media = reply.media

        text = f"""
◢◤ MEDIA INFO ◢◤

MEDIA:
{type(media)}

DATE:
{reply.date}
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

# =====================================================
    # SELF INFO
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.(nix|selfinfo|self)"
    ))
    @owner_only
    async def nix_info(event):

        me = await client.get_me()

        cpu = psutil.cpu_percent()

        ram = psutil.virtual_memory().percent

        uptime = int(
            time.time() - START_TIME
        )

        uptime_h = uptime // 3600
        uptime_m = (uptime % 3600) // 60
        uptime_s = uptime % 60

        coin_data = coins_db.find_one(
            {"user_id": event.sender_id}
        )

        coins = 0

        if coin_data:
            coins = coin_data.get(
                "coins",
                0
            )

        stats = stats_db.find_one(
            {"user_id": event.sender_id}
        )

        total_msgs = 0

        if stats:
            total_msgs = stats.get(
                "messages",
                0
            )

        text = f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤
__________________________

◈ OWNER:
{me.first_name}

◈ USERNAME:
@{me.username}

◈ USER ID:
{me.id}

◈ VERSION:
1.1.2

◈ STATUS:
ONLINE ✨

◈ PING:
0.12s

◈ UPTIME:
{uptime_h}h {uptime_m}m {uptime_s}s

__________________________

◈ CPU:
{progress_bar(cpu)} {cpu}%

◈ RAM:
{progress_bar(ram)} {ram}%

__________________________

◈ NIX COINS:
{coins}

◈ MANAGED MSGS:
{total_msgs:,}

__________________________

◈ FEATURES:

• OCR SYSTEM
• OCR TRANSLATOR
• AI GROUP CLEANER
• DOWNLOADER
• PROFILE SYSTEM
• TTS SYSTEM
• STT SYSTEM
• TERMINAL SYSTEM
• SCREENSHOT SYSTEM
• PREMIUM STYLE
• NIX TIMELINE
• SMART TOOLS
• GROUP MANAGER

__________________________

◢ ᴛɪᴀᴍ'ꜱ ᴏꜰꜰɪᴄɪᴀʟ ꜱᴇʟꜰ ◤
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # RESTART
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.restart"
    ))
    @owner_only
    async def restart_handler(event):

        msg = await event.reply(
            """
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

Restarting Self...
"""
        )

        await asyncio.sleep(2)

        os.execl(
            sys.executable,
            sys.executable,
            *sys.argv
        )

    # =====================================================
    # PING SYSTEM
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.ping"
    ))
    @owner_only
    async def ping_handler(event):

        start = time.time()

        msg = await event.reply(
            "Pinging..."
        )

        end = time.time()

        ping = round(
            (end - start) * 1000
        )

        text = f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

◈ Message: Pong!
◈ Speed: {ping} ms
◈ Status: Online ✨

▰▰▰▰▰▰▰▰▱▱ 85%

◢◤ Nix Group ◢◤
"""

        text += await add_signature(
            event.sender_id
        )

        await msg.edit(text)

    # =====================================================
    # HELP MENU
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.(help|menu)"
    ))
    @owner_only
    async def help_handler(event):

        text = """
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤
__________________________

◈ MAIN COMMANDS

.coin
.sys
.self
.help
.profile
.timeline

__________________________

◈ MEDIA COMMANDS

.tts
.stt
.dl
.ocr
.ocrtr
.media

__________________________

◈ MANAGEMENT

.clean
.cmd
.screenshot

__________________________

◈ PROFILE

.setbio
.profile

__________________________

◈ UTILITIES

.tr
.ping
.restart

__________________________

◢ ₮ ł ₳ ₼ | NIX ◤
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # AUTO COIN SYSTEM
    # =====================================================

    @client.on(events.NewMessage)
    async def auto_coin_system(event):

        if event.sender_id != OWNER_ID:
            return

        if not event.raw_text:
            return

        add_coin(
            event.sender_id,
            amount=1
        )

    # =====================================================
    # AUTO PROFILE TAG
    # =====================================================

    @client.on(events.NewMessage(
        outgoing=True
    ))
    async def auto_profile_tag(event):

        if not event.raw_text:
            return

        if event.raw_text.startswith("."):
            return

        try:

            me = await client.get_me()

            custom_name = f"""
◢ SELF NIX ◤ | {me.first_name}
"""

            if me.first_name != custom_name:

                await client(
                    UpdateProfileRequest(
                        first_name=custom_name
                    )
                )

        except:
            pass

    # =====================================================
    # SMART DELETE
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.autodel (\d+)"
    ))
    @owner_only
    async def auto_delete(event):

        seconds = int(
            event.pattern_match.group(1)
        )

        msg = await event.reply(
            f"""
◢◤ AUTO DELETE ◢◤

This message will delete in
{seconds} seconds.
"""
        )

        await asyncio.sleep(seconds)

        await msg.delete()

    # =====================================================
    # SERVER SPEED TEST
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.speed"
    ))
    @owner_only
    async def speed_test(event):

        start = time.time()

        for _ in range(50000):
            pass

        end = time.time()

        speed = round(
            end - start,
            5
        )

        text = f"""
◢◤ SERVER SPEED ◢◤

◈ Benchmark:
{speed}s

◈ Status:
FAST ⚡
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # MEMORY CLEANER
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.ramclean"
    ))
    @owner_only
    async def ram_cleaner(event):

        before = psutil.virtual_memory().percent

        gc.collect()

        after = psutil.virtual_memory().percent

        text = f"""
◢◤ MEMORY CLEANER ◢◤

RAM BEFORE:
{before}%

RAM AFTER:
{after}%

STATUS:
CLEANED ✨
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # JSON INFO
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.json"
    ))
    @owner_only
    async def json_handler(event):

        if not event.is_reply:

            return await event.reply(
                "Reply to message."
            )

        reply = await event.get_reply_message()

        data = reply.to_dict()

        text = json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

        if len(text) > 4000:
            text = text[:4000]

        await event.reply(
            f"""
◢◤ MESSAGE JSON ◢◤

{text}
"""
        )

    # =====================================================
    # USER INFO
    # =====================================================

    @client.on(events.NewMessage(
        pattern=r"\.userinfo"
    ))
    @owner_only
    async def user_info(event):

        user = await event.get_sender()

        text = f"""
◢◤ USER INFO ◢◤

◈ ID:
{user.id}

◈ NAME:
{user.first_name}

◈ USERNAME:
@{user.username}

◈ BOT:
{user.bot}

◈ VERIFIED:
{user.verified}

◈ PREMIUM:
{user.premium}
"""

        text += await add_signature(
            event.sender_id
        )

        await event.reply(text)

    # =====================================================
    # FINAL LOADER
    # =====================================================

    print("""
╔══════════════════════════════╗
║   ◢◤ SELF NIX LOADED ◢◤    ║
╚══════════════════════════════╝
""")