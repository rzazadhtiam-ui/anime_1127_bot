import os
import threading
from hashlib import md5
from datetime import datetime
import pytz

import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# =======================
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
bot = telebot.TeleBot(TOKEN, parse_mode=None)

OWNER_ID = 6433381392
CHANNEL_ID = "@asta_tiam_cannel"

# =======================
MONGO_URI = "mongodb+srv://self_login:tiam_jinx@self.v2vzh9e.mongodb.net/anime_bot_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["anime_bot_db"]

videos_col = db["videos"]
music_col = db["music"]
pending_col = db["pending_videos"]
admins_col = db["admins"]

# =======================
def get_admins():
    data = admins_col.find_one({"_id": "admins"})
    if data:
        return data.get("list", [])
    admins_col.insert_one({"_id": "admins", "list": []})
    return []

admins = get_admins()

# =======================
def is_duplicate(kind, unique_id):
    col = videos_col if kind == "video" else music_col
    return col.find_one({"unique_id": unique_id}) is not None

# =======================
def send_to_channel_and_save(file_id, caption, kind, artist=None, unique_id=None):
    if unique_id and is_duplicate(kind, unique_id):
        return

    if kind == "video":
        msg = bot.send_video(CHANNEL_ID, file_id, caption=caption)
        videos_col.insert_one({
            "file_id": msg.video.file_id,
            "caption": caption,
            "unique_id": unique_id
        })

    elif kind == "music":
        msg = bot.send_audio(
            CHANNEL_ID,
            file_id,
            caption=caption,
            performer=artist
        )
        music_col.insert_one({
            "file_id": msg.audio.file_id,
            "caption": caption,
            "artist": artist,
            "unique_id": unique_id
        })

# =======================
@bot.message_handler(content_types=["video", "audio", "document"])
def handle_media(message):
    user_id = message.from_user.id
    caption = message.caption or " "
    kind = None
    file_id = None
    unique_id = None
    artist = None

    if message.video:
        kind = "video"
        file_id = message.video.file_id
        unique_id = message.video.file_unique_id

    elif message.audio:
        kind = "music"
        file_id = message.audio.file_id
        unique_id = message.audio.file_unique_id
        artist = (
            message.audio.performer
            or message.audio.title
            or "Unknown Artist"
        )

    elif message.document and message.document.mime_type.startswith("video/"):
        kind = "video"
        file_id = message.document.file_id
        unique_id = message.document.file_unique_id

    if not file_id:
        return

    if user_id == OWNER_ID or user_id in admins:
        send_to_channel_and_save(
            file_id,
            caption,
            kind,
            artist=artist,
            unique_id=unique_id
        )
        bot.reply_to(message, "✅ ذخیره شد")
        return

    pending_id = md5(unique_id.encode()).hexdigest()[:12]

    if pending_col.find_one({"_id": pending_id}):
        bot.reply_to(message, "⏳ این فایل قبلاً ارسال شده")
        return

    pending_col.insert_one({
        "_id": pending_id,
        "file_id": file_id,
        "caption": caption,
        "kind": kind,
        "artist": artist,
        "unique_id": unique_id,
        "from_id": user_id
    })

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"ok:{pending_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"no:{pending_id}")
    )

    bot.send_message(
        OWNER_ID,
        f"فایل جدید:\n\n{caption}",
        reply_markup=kb
    )

# =======================
@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok:", "no:")))
def approve(call):
    action, pid = call.data.split(":")
    data = pending_col.find_one({"_id": pid})
    if not data:
        return

    if action == "ok":
        send_to_channel_and_save(
            data["file_id"],
            data["caption"],
            data["kind"],
            artist=data.get("artist"),
            unique_id=data.get("unique_id")
        )
        bot.send_message(data["from_id"], "✅ تایید شد")

    else:
        bot.send_message(data["from_id"], "❌ رد شد")

    pending_col.delete_one({"_id": pid})
    bot.answer_callback_query(call.id)

# =======================
@bot.inline_handler(lambda q: True)
def inline_query(query):
    from telebot.types import InlineQueryResultCachedVideo, InlineQueryResultCachedAudio
    results = []
    q = query.query.lower().strip()

    if q.startswith("music"):
        items = list(music_col.find().limit(20))
        for i, m in enumerate(items):
            results.append(
                InlineQueryResultCachedAudio(
                    id=f"m{i}",
                    audio_file_id=m["file_id"],
                    title=m.get("caption", "Music"),
                    performer=m.get("artist", "Unknown"),
                    caption=m.get("caption", " ")
                )
            )
    else:
        items = list(videos_col.find().limit(20))
        for i, v in enumerate(items):
            results.append(
                InlineQueryResultCachedVideo(
                    id=f"v{i}",
                    video_file_id=v["file_id"],
                    title="Video",
                    description=v.get("caption", " "),
                    supports_streaming=True
                )
            )

    bot.answer_inline_query(
        query.id,
        results,
        cache_time=0,
        is_personal=True
    )

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "🤖 ربات آماده است")

# =======================
scheduler = BackgroundScheduler(timezone=pytz.UTC)

def send_time():
    now = datetime.now(pytz.UTC).strftime("%H:%M")
    bot.send_message(OWNER_ID, f"🕒 {now}")

scheduler.add_job(send_time, "interval", minutes=1)
scheduler.start()

# =======================
app = Flask(__name__)
@app.route("/")
def home():
    return "OK"

def run_web():
    app.run("0.0.0.0", int(os.environ.get("PORT", 5000)))

# =======================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
