# =========================================================
# SELF NIX - FINAL STABLE BUILD (SIGNATURE + FIXED CORE)
# =========================================================

from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
import asyncio
import random
import os

from pymongo import MongoClient
from gtts import gTTS

from multi_lang import multi_lang, reply_auto, edit_auto

try:
    import pytesseract
    from PIL import Image
except:
    pytesseract = None
    Image = None

whisper_model = None
try:
    import whisper
    whisper_model = whisper.load_model("base")
except:
    whisper_model = None

import yt_dlp

# ================= MONGO =================

MONGO_URI = "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017"

mongo = MongoClient(MONGO_URI)
db = mongo["telegram_sessions"]
stats_col = db["stats"]

# ================= CONFIG =================

MANDATORY_TAG = True

EXEMPT_USERS = {6433381392, 8471402457}

FORCED_SIGNATURE = "\n\n◢ SELF NIX "

user_styles = {}

PROFILE_STYLES = {
    1: {"name": "◈SELF NIX◈ | {name}", "bio": "SELF NIX ACTIVE"},
    2: {"name": "◢ SELF NIX | {name}", "bio": "POWERED BY NIX"},
    3: {"name": "тɪαм | {name}", "bio": "OFFICIAL SELF"},
    4: {"name": "[SELF NIX] | {name}", "bio": "SYSTEM ONLINE"},
    5: {"name": "⟦SELF NIX⟧ {name}", "bio": "70% POWER"}
}

# ================= STATS =================

def inc_msg_count():
    stats_col.update_one({"_id": "global"}, {"$inc": {"count": 1}}, upsert=True)

def get_msg_count():
    doc = stats_col.find_one({"_id": "global"})
    return doc.get("count", 0) if doc else 0

# ================= UTILS =================

def bar(p):
    return "▰" * int(p / 10) + "▱" * (10 - int(p / 10))

def should_sign(text):
    return text and (len(text) > 40 or text.count("\n") > 4)

def is_exempt(user_id):
    return user_id in EXEMPT_USERS

def build_signature():
    return f"◢ SELF NIX | MSG {get_msg_count()}"

# ================= PROFILE =================

async def apply_profile(client, style_id):
    me = await client.get_me()
    name = me.first_name or "User"

    style = PROFILE_STYLES.get(style_id)
    if not style:
        return False

    new_name = style["name"].format(name=name)

    if MANDATORY_TAG and "SELF NIX" not in new_name.upper():
        new_name = "◈SELF NIX◈ | " + name

    try:
        await client(UpdateProfileRequest(first_name=new_name, about=style["bio"]))
        return True
    except:
        return False

# ================= MEDIA =================

async def voice_to_text(path):
    if not whisper_model or not path or not os.path.exists(path):
        return "Voice system not available"
    try:
        return whisper_model.transcribe(path).get("text", "")
    except:
        return "Transcription error"

async def image_to_text(path):
    if not pytesseract or not Image or not path:
        return "OCR not available"
    try:
        return pytesseract.image_to_string(Image.open(path))
    except:
        return "OCR error"

async def text_to_voice(text, out="voice.mp3"):
    lang = "fa"
    if any("a" <= c.lower() <= "z" for c in text):
        lang = "en"

    gTTS(text=text, lang=lang).save(out)
    return out

# ================= DOWNLOADER =================

async def download_from_url(url):
    try:
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "format": "best",
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    except Exception as e:
        return str(e)

# ================= SYSTEM =================

def register_self_nix_system(client):

    print("SELF NIX LOADED")

    # ================= FORCE SIGNATURE =================
    @client.on(events.NewMessage(outgoing=True))
    async def force_signature(event):
        try:
            me = await event.client.get_me()

            if is_exempt(me.id):
                return

            text = event.raw_text or ""

            if "SELF NIX ✓" not in text:
                await event.edit(text + FORCED_SIGNATURE)

        except:
            pass

    # ================= EDIT ENFORCER =================
    @client.on(events.MessageEdited(outgoing=True))
    async def enforce_edit(event):
        try:
            me = await event.client.get_me()

            if is_exempt(me.id):
                return

            text = event.raw_text or ""

            if "SELF NIX ✓" not in text:
                await event.edit(text + FORCED_SIGNATURE)

        except:
            pass

    # ================= PING =================
    @client.on(events.NewMessage)
    @multi_lang([".ping", ".پینگ"])
    async def ping(e):
        await edit_auto(e, f"""
SELF NIX ONLINE
MSG: {get_msg_count()}
{bar(random.randint(1,99))}
""")

    # ================= PROFILE =================
    @client.on(events.NewMessage)
    @multi_lang([".profile", ".پروفایل"])
    async def profile(e):
        arg = (e.ml_args or "").strip()

        if not arg:
            return await edit_auto(e, "Style 1-5")

        try:
            sid = int(arg)
        except:
            return await edit_auto(e, "Invalid")

        ok = await apply_profile(client, sid)
        await edit_auto(e, "Updated" if ok else "Error")

    # ================= NAME =================
    @client.on(events.NewMessage)
    @multi_lang([".name", ".اسم"])
    async def name(e):
        arg = (e.ml_args or "").strip()

        if not arg:
            return await reply_auto(e, "No name")

        if MANDATORY_TAG:
            arg = "◈SELF NIX◈ | " + arg

        try:
            await client(UpdateProfileRequest(first_name=arg))
            await edit_auto(e, "OK")
        except:
            await edit_auto(e, "Error")

    # ================= VOICE =================
    @client.on(events.NewMessage)
    @multi_lang([".vvt", ".ویس"])
    async def vvt(e):
        msg = await e.get_reply_message() if e.is_reply else None

        if not msg or not msg.media:
            return await reply_auto(e, "Reply to voice")

        path = await msg.download_media()
        text = await voice_to_text(path)

        await edit_auto(e, text)

    # ================= OCR =================
    @client.on(events.NewMessage)
    @multi_lang([".ocr", ".عکس"])
    async def ocr(e):
        msg = await e.get_reply_message() if e.is_reply else None

        if not msg or not msg.photo:
            return await reply_auto(e, "Reply to image")

        path = await msg.download_media()
        text = await image_to_text(path)

        await edit_auto(e, text)

    # ================= TEXT TO VOICE =================
    @client.on(events.NewMessage)
    @multi_lang([".ttv", ".صدا"])
    async def ttv(e):
        text = (e.ml_args or "").strip()

        if not text:
            return await reply_auto(e, "No text")

        file = await text_to_voice(text)
        await e.reply(file=file)

    # ================= DOWNLOADER =================
    @client.on(events.NewMessage)
    @multi_lang([".dl", ".دانلود"])
    async def dl(e):
        url = (e.ml_args or "").strip()

        if not url:
            return await reply_auto(e, "Send link")

        msg = await edit_auto(e, "Downloading...")

        file = await download_from_url(url)

        if os.path.exists(file):
            await e.reply(file=file)
        else:
            await edit_auto(e, f"Failed: {file}")

    print("SELF NIX READY")
