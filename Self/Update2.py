# =========================================================
# SELF NIX UPDATE2 - FIXED VERSION
# =========================================================

import asyncio
import random
from telethon.tl.functions.account import UpdateProfileRequest
from multi_lang import multi_lang, reply_auto, edit_auto

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

SELF_NIX_ENABLED = True
MANDATORY_TAG = True
AUTO_SIGNATURE_LINES = 6
AUTO_SIGNATURE_LENGTH = 50
user_styles = {}

PROFILE_STYLES = {
    1: {"name": "◈NIX◈ | {name}", "bio": "SELF NIX ACTIVE"},
    2: {"name": "◢ NIX | {name}", "bio": "POWERED BY NIX"},
    3: {"name": "тɪαм | {name}", "bio": "OFFICIAL SELF"},
    4: {"name": "[NIX] | {name}", "bio": "SYSTEM ONLINE"},
    5: {"name": "⟦SELF NIX⟧ {name}", "bio": "70% POWER"}
}

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

async def voice_to_text(path):
    if not whisper_model:
        return "Whisper not installed"
    result = whisper_model.transcribe(path)
    return result["text"]

async def text_to_voice(text, out="voice.mp3"):
    from gtts import gTTS
    tts = gTTS(text=text, lang="en")
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
    (
        ffmpeg
        .input(inp, ss=start, t=dur)
        .output(out)
        .run(overwrite_output=True)
    )
    return out

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

def register_self_nix_system(client):
    print("runing srlf nix system")
    
    @client.on(events.NewMessage)
    @multi_lang([".ping", ".پینگ"])
    async def ping(e):
        await edit_auto(event, status())

    @client.on(events.NewMessage)
    @multi_lang([".profile", ".پروفایل"])
    async def profile(e):
        arg = (e.ml_args or "").strip()
        if not arg:
            return await edit_auto(event, "Styles: 1-5")

        try:
            sid = int(arg)
        except ValueError:
            return await edit_auto(event, "Style id must be a number")

        set_style(e.chat_id, sid)
        ok = await apply_profile(client, sid)
        await edit_auto(e, "Updated" if ok else "Error")

    @client.on(events.NewMessage)
    @multi_lang([".name", ".اسم"])
    async def name(e):
        arg = (e.ml_args or "").strip()
        if not arg:
            return await edit_auto(event, "No name")

        if MANDATORY_TAG and "NIX" not in arg.upper():
            arg = "◈NIX◈ | " + arg

        try:
            await client(UpdateProfileRequest(first_name=arg))
            await edit_auto(event, "Name updated")
        except Exception as ex:
            await edit_auto(event, f"Error: {ex}")

    @client.on(events.NewMessage)
    @multi_lang([".vvt", ".ویس"])
    async def v2t(e):
        if not e.file:
            return await reply_auto(event, "Send voice")

        path = await e.download_media()
        text = await voice_to_text(path)
        await edit_auto(event, text)

    @client.on(events.NewMessage)
    @multi_lang([".ttv", ".صدا"])
    async def t2v(e):
        text = (e.ml_args or "").strip()
        if not text:
            return await reply_auto(event, "No text")

        file = await text_to_voice(text)
        await e.reply(file=file)

    @client.on(events.NewMessage)
    @multi_lang([".ocr", ".عکس"])
    async def ocr(e):
        if not e.file:
            return await reply_auto(event, "Send image")

        path = await e.download_media()
        text = await image_to_text(path)
        await edit_auto(e, text)

    @client.on(events.NewMessage)
    @multi_lang([".cutaudio", ".برش"])
    async def cut_audio(e):
        if not e.file:
            return await reply_auto(event, "Send audio")

        path = await e.download_media()
        out = "out.mp3"
        result = await audio_trim(path, out)
        if result:
            await e.reply(file=result)
        else:
            await edit_auto(event, "FFmpeg not installed")

    @client.on(events.NewMessage)
    @multi_lang([".cutvideo", ".ویدیو"])
    async def cut_video(e):
        if not e.file:
            return await reply_auto(event, "Send video")

        path = await e.download_media()
        out = "out.mp4"
        result = await video_trim(path, out)
        if result:
            await e.reply(file=result)
        else:
            await edit_auto(event, "FFmpeg not installed")

    print("SELF NIX FULL SYSTEM LOADED")
