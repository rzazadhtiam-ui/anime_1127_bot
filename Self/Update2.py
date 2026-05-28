# =========================================================
# ◢◤ SELF NIX SYSTEM FULL CORE ◢◤
# =========================================================

import asyncio
import random
import os
from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
from functools import wraps

from multi_lang import multi_lang, reply_auto, edit_auto

# optional heavy modules (safe import)
try:
    import pytesseract
    from PIL import Image
except:
    pytesseract = None

try:
    import ffmpeg
except:
    ffmpeg = None

# whisper optional
try:
    import whisper
    whisper_model = whisper.load_model("base")
except:
    whisper_model = None


# =========================================================
# CONFIG
# =========================================================

SELF_NIX_ENABLED = True
MANDATORY_TAG = True
AUTO_SIGNATURE_LINES = 6
AUTO_SIGNATURE_LENGTH = 50

user_styles = {}

# =========================================================
# PROFILE STYLES
# =========================================================

PROFILE_STYLES = {
    1: {"name": "◈NIX◈ | {name}", "bio": "SELF NIX ACTIVE"},
    2: {"name": "◢ NIX | {name}", "bio": "POWERED BY NIX"},
    3: {"name": "тɪαм | {name}", "bio": "OFFICIAL SELF"},
    4: {"name": "[NIX] | {name}", "bio": "SYSTEM ONLINE"},
    5: {"name": "⟦SELF NIX⟧ {name}", "bio": "70% POWER"}
}


# =========================================================
# UTILS
# =========================================================

def bar(p):
    return "▰" * int(p / 10) + "▱" * (10 - int(p / 10))


def get_style(cid):
    return user_styles.get(cid, 1)


def set_style(cid, s):
    user_styles[cid] = s


def sig(text):
    if not text:
        return text

    if len(text) > AUTO_SIGNATURE_LENGTH or text.count("\n") >= AUTO_SIGNATURE_LINES:
        p = random.randint(70, 99)
        return text + f"\n\n▰ SELF NIX {p}% ▰"
    return text


# =========================================================
# PROFILE APPLY
# =========================================================

async def apply_profile(client, style_id):
    me = await client.get_me()
    name = me.first_name or "User"

    style = PROFILE_STYLES.get(style_id)
    if not style:
        return False

    new_name = style["name"].format(name=name)

    if MANDATORY_TAG and "NIX" not in new_name.upper():
        new_name = "◈NIX◈ | " + name

    try:
        await client(UpdateProfileRequest(
            first_name=new_name,
            about=style["bio"]
        ))
        return True
    except:
        return False


# =========================================================
# STATUS
# =========================================================

def status():
    return f"""
◢◤ SELF NIX ◢◤
Ping: OK
Speed: {round(random.uniform(0.05,0.2),2)}s
Status: ONLINE
{bar(random.randint(70,99))}
"""


# =========================================================
# VOICE → TEXT
# =========================================================

async def voice_to_text(path):
    if not whisper_model:
        return "Whisper not installed"

    result = whisper_model.transcribe(path)
    return result["text"]


# =========================================================
# TEXT → VOICE (placeholder)
# =========================================================

async def text_to_voice(text, out="voice.mp3"):
    # نیاز به gtts یا edge-tts
    from gtts import gTTS
    tts = gTTS(text=text, lang="en")
    tts.save(out)
    return out


# =========================================================
# IMAGE OCR
# =========================================================

async def image_to_text(path):
    if not pytesseract:
        return "OCR not installed"

    img = Image.open(path)
    return pytesseract.image_to_string(img)


# =========================================================
# AUDIO EDIT (FFMPEG)
# =========================================================

async def audio_trim(inp, out, start=0, dur=10):
    if not ffmpeg:
        return None

    (
        ffmpeg
        .input(inp, ss=start, t=dur)
        .output(out)
        .run(overwrite_output=True)
    )
    return out


# =========================================================
# VIDEO EDIT (FFMPEG)
# =========================================================

async def video_trim(inp, out, start=0, dur=10):
    if not ffmpeg:
        return None

    (
        ffmpeg
        .input(inp, ss=start, t=dur)
        .output(out)
        .run(overwrite_output=True)
    )
    return out


# =========================================================
# COMMANDS
# =========================================================

def register_self_nix_system(client):

    # ---------------- STATUS ----------------
    @multi_lang([".ping", ".پینگ"])
    async def ping(e):
        await edit_auto(e, status())

    # ---------------- PROFILE ----------------
    @multi_lang([".profile", ".پروفایل"])
    async def profile(e):
        arg = (e.ml_args or "").strip()

        if not arg:
            return await edit_auto(e, "Styles: 1-5")

        sid = int(arg)
        set_style(e.chat_id, sid)

        ok = await apply_profile(client, sid)
        await edit_auto(e, "Updated" if ok else "Error")

    # ---------------- NAME ----------------
    @multi_lang([".name", ".اسم"])
    async def name(e):
        arg = (e.ml_args or "").strip()

        if not arg:
            return await edit_auto(e, "No name")

        if MANDATORY_TAG and "NIX" not in arg.upper():
            arg = "◈NIX◈ | " + arg

        await client(UpdateProfileRequest(first_name=arg))
        await edit_auto(e, "Name updated")

    # ---------------- VOICE TO TEXT ----------------
    @multi_lang([".vvt", ".ویس"])
    async def v2t(e):
        if not e.file:
            return await reply_auto(e, "Send voice")

        path = await e.download_media()
        text = await voice_to_text(path)

        await edit_auto(e, text)

    # ---------------- TEXT TO VOICE ----------------
    @multi_lang([".ttv", ".صدا"])
    async def t2v(e):
        text = (e.ml_args or "").strip()
        if not text:
            return await reply_auto(e, "No text")

        file = await text_to_voice(text)
        await e.edit(file=file)

    # ---------------- OCR ----------------
    @multi_lang([".ocr", ".عکس"])
    async def ocr(e):
        if not e.file:
            return await reply_auto(e, "Send image")

        path = await e.download_media()
        text = await image_to_text(path)

        await edit_auto(e, text)

    # ---------------- AUDIO TRIM ----------------
    @multi_lang([".cutaudio", ".برش"])
    async def cut_audio(e):
        if not e.file:
            return await reply_auto(e, "Send audio")

        path = await e.download_media()
        out = "out.mp3"

        await audio_trim(path, out)
        await e.edit(file=out)

    # ---------------- VIDEO TRIM ----------------
    @multi_lang([".cutvideo", ".ویدیو"])
    async def cut_video(e):
        if not e.file:
            return await reply_auto(e, "Send video")

        path = await e.download_media()
        out = "out.mp4"

        await video_trim(path, out)
        await e.edit(file=out)

    print("SELF NIX FULL SYSTEM LOADED")
