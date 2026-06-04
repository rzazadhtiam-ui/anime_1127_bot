# =========================================================
# SELF NIX UPDATE2 - FIXED + DIGITAL SIGNATURE
# =========================================================

from telethon import TelegramClient, events
import asyncio
import random
from telethon.tl.functions.account import UpdateProfileRequest
from multi_lang import multi_lang, reply_auto, edit_auto
from gtts import gTTS
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

try:
    import whisper
    whisper_model = whisper.load_model("base")
except Exception:
    whisper_model = None

from pymongo import MongoClient

# ================= MONGO =================

MONGO_URI = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

DB_NAME = "telegram_sessions"

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
stats_col = db["stats"]

# ================= CONFIG =================

SELF_NIX_ENABLED = True
MANDATORY_TAG = True

AUTO_SIGNATURE_LINES = 6
AUTO_SIGNATURE_LENGTH = 50

user_styles = {}

PROFILE_STYLES = {
    1: {"name": "◈SELF NIX◈ | {name}", "bio": "SELF NIX ACTIVE"},
    2: {"name": "◢ SELF NIX | {name}", "bio": "POWERED BY NIX"},
    3: {"name": "тɪαм | {name}", "bio": "OFFICIAL SELF"},
    4: {"name": "[SELF NIX] | {name}", "bio": "SYSTEM ONLINE"},
    5: {"name": "⟦SELF NIX⟧ {name}", "bio": "70% POWER"}
}

# ================= STATS =================

def get_msg_count():
    doc = stats_col.find_one({"_id": "global"})
    if not doc:
        stats_col.insert_one({"_id": "global", "count": 0})
        return 0
    return doc.get("count", 0)


def inc_msg_count():
    stats_col.update_one(
        {"_id": "global"},
        {"$inc": {"count": 1}},
        upsert=True
    )

# ================= UI HELPERS =================

def bar(p):
    return "▰" * int(p / 10) + "▱" * (10 - int(p / 10))


def get_style(cid):
    return user_styles.get(cid, 1)


def set_style(cid, s):
    user_styles[cid] = s

# ================= SIGNATURE =================

def build_signature():
    count = get_msg_count()
    return f"◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ɴɪx ᴍᴀɴᴀɢᴇᴅ: {count} ᴍsɢs"


# ================= CORE SIGN FUNCTION =================

def should_sign(text: str):
    if not text:
        return False
    return len(text) > 40 or text.count("\n") >= 5


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
        await client(UpdateProfileRequest(
            first_name=new_name,
            about=style["bio"]
        ))
        return True
    except Exception:
        return False


def status():
    return f"""
◢◤ SELF NIX ◢◤
Ping: OK
Speed: {round(random.uniform(0.05,0.2),2)}s
Status: ONLINE
{bar(random.randint(70,99))}
"""

# ================= MEDIA =================

async def voice_to_text(path):
    if not whisper_model:
        return "Whisper not installed"
    result = whisper_model.transcribe(path)
    return result["text"]

    

async def text_to_voice(text, out="voice.mp3"):

    lang = "fa"

    try:
        if any("a" <= c.lower() <= "z" for c in text):
            lang = "en"
    except:
        pass

    tts = gTTS(
        text=text,
        lang=lang
    )

    tts.save(out)

    return out


async def image_to_text(path):
    if not pytesseract or not Image:
        return "OCR not installed"
    img = Image.open(path)
    return pytesseract.image_to_string(img)


async def audio_trim(inp, out, start=0, dur=10):
    if not ffmpeg:
        return None
    ffmpeg.input(inp, ss=start, t=dur).output(out).run(overwrite_output=True)
    return out


async def video_trim(inp, out, start=0, dur=10):
    if not ffmpeg:
        return None
    ffmpeg.input(inp, ss=start, t=dur).output(out).run(overwrite_output=True)
    return out


# ================= MAIN SYSTEM =================

def register_self_nix_system(client):

    print("SELF NIX SYSTEM LOADED")

    # ================= AUTO SIGNATURE ENGINE =================
    @client.on(events.NewMessage(outgoing=True))
    async def auto_signature(e):
        try:
            text = e.raw_text or ""

            if "ɴɪx ᴍᴀɴᴀɢᴇᴅ" in text:
                return

            if should_sign(text):
                inc_msg_count()
                sig = build_signature()
                await e.edit(text + "\n\n" + sig)

        except Exception:
            pass

    # ================= COMMANDS =================

    @client.on(events.NewMessage)
    @multi_lang([".ping", ".پینگ"])
    async def ping(e):
        await edit_auto(e, status())

    @client.on(events.NewMessage)
    @multi_lang([".profile", ".پروفایل"])
    async def profile(e):
        arg = (e.ml_args or "").strip()
        if not arg:
            return await edit_auto(e, "Styles: 1-5")

        try:
            sid = int(arg)
        except ValueError:
            return await edit_auto(e, "Style id must be number")

        set_style(e.chat_id, sid)
        ok = await apply_profile(client, sid)
        await edit_auto(e, "Updated" if ok else "Error")

    @client.on(events.NewMessage)
    @multi_lang([".name", ".اسم"])
    async def name(e):
        arg = (e.ml_args or "").strip()
        if not arg:
            return await edit_auto(e, "No name")

        if MANDATORY_TAG and "SELF NIX" not in arg.upper():
            arg = "◈SELF NIX◈ | " + arg

        try:
            await client(UpdateProfileRequest(first_name=arg))
            await edit_auto(e, "Name updated")
        except Exception as ex:
            await edit_auto(e, f"Error: {ex}")

    @client.on(events.NewMessage)
    @multi_lang([".vvt", ".ویس"])
    async def v2t(e):

        msg = e

        if e.is_reply:
            msg = await e.get_reply_message()

        if not msg.media:
            return await reply_auto(e, "روی ویس یا فایل صوتی ریپلای کن")

        path = await msg.download_media()

        text = await voice_to_text(path)

        await edit_auto(e, text)

    @client.on(events.NewMessage)
    @multi_lang([".ttv", ".صدا"])
    async def t2v(e):
        text = (e.ml_args or "").strip()
        if not text:
            return await reply_auto(e, "No text")

        file = await text_to_voice(text)
        await e.reply(file=file)

    @client.on(events.NewMessage)
    @multi_lang([".ocr", ".عکس"])
    async def ocr(e):

        msg = e

        if e.is_reply:
            msg = await e.get_reply_message()

        if not msg.photo:
            return await reply_auto(e, "روی عکس ریپلای کن")

        path = await msg.download_media()

        text = await image_to_text(path)

        await edit_auto(e, text)

    @client.on(events.NewMessage)
    @multi_lang([".cutaudio", ".برش"])
    async def cut_audio(e):
        msg = e

        if e.is_reply:
            msg = await e.get_reply_message()

        if not msg.media:
            return await reply_auto(e, "روی فایل صوتی ریپلای کن")

        path = await msg.download_media()
        out = "out.mp3"
        res = await audio_trim(path, out)

        if res:
            await e.reply(file=res)
        else:
            await edit_auto(e, "FFmpeg not installed")

    @client.on(events.NewMessage)
    @multi_lang([".cutvideo", ".ویدیو"])
    async def cut_video(e):
        msg = e

        if e.is_reply:
            msg = await e.get_reply_message()

        if not msg.video:
            return await reply_auto(e, "روی ویدیو ریپلای کن")

        path = await msg.download_media()
        out = "out.mp4"
        res = await video_trim(path, out)

        if res:
            await e.reply(file=res)
        else:
            await edit_auto(e, "FFmpeg not installed")

    print("SELF NIX READY")
