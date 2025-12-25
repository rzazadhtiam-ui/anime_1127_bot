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
def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + c if c in escape_chars else c for c in text])

def get_admins():
    data = admins_col.find_one({"_id": "admins"})
    if data:
        return data.get("list", [])
    else:
        admins_col.insert_one({"_id": "admins", "list": []})
        return []

admins = get_admins()

# =======================
def is_duplicate(file_id, caption, kind):
    """چک می‌کنه که فایل یا آهنگ با همین caption و file_id تکراری نباشه"""
    col = videos_col if kind == "video" else music_col
    return col.find_one({"file_id": file_id, "caption": caption}) is not None

def send_to_channel_and_save(file_id, title, caption=None, kind="video", tags=None, artist=None):
    tags = tags or []
    caption = caption or title

    if is_duplicate(file_id, caption, kind):
        print(f"{kind.capitalize()} تکراری است و ذخیره نشد: {title}")
        return

    try:
        if kind == "video":
            sent_msg = bot.send_video(CHANNEL_ID, file_id, caption=caption)
            channel_file_id = sent_msg.video.file_id
            videos_col.insert_one({
                "file_id": channel_file_id,
                "title": title,
                "caption": caption,
                "tags": tags
            })
        elif kind == "music":
            sent_msg = bot.send_audio(CHANNEL_ID, file_id, caption=caption)
            channel_file_id = sent_msg.audio.file_id
            music_col.insert_one({
                "file_id": channel_file_id,
                "title": title,
                "caption": caption,
                "tags": tags,
                "artist": artist
            })
    except Exception as e:
        print("Error sending to channel:", e)

# =======================
@bot.message_handler(content_types=['video', 'document', 'audio'])
def handle_media(message):
    file_id = None
    title = "بدون عنوان"
    caption = message.caption or "بدون توضیح"
    user_id = message.from_user.id

    kind = None
    if message.video or (message.document and message.document.mime_type.startswith("video/")):
        kind = "video"
        file_id = message.video.file_id if message.video else message.document.file_id
    elif message.audio:
        kind = "music"
        file_id = message.audio.file_id

    if not file_id:
        return

    # مالک و ادمین مستقیم ذخیره می‌کنند
    if user_id == OWNER_ID or user_id in admins:
        send_to_channel_and_save(file_id, title, caption=caption, kind=kind)
        bot.reply_to(message, f"{kind.capitalize()} ذخیره شد ✅\n🎬 {caption}")
        return

    # کاربران عادی → تایید مالک لازم
    pending_id = md5(file_id.encode()).hexdigest()[:10]
    if pending_col.find_one({"_id": pending_id}):
        bot.reply_to(message, "این فایل قبلاً ارسال شده و در انتظار تایید است ⏳")
        return

    pending_col.insert_one({
        "_id": pending_id,
        "file_id": file_id,
        "title": title,
        "caption": caption,
        "from_id": user_id,
        "kind": kind
    })

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"approve:{pending_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject:{pending_id}")
    )

    bot.send_message(
        OWNER_ID,
        f"یک {kind} از [{escape_markdown(message.from_user.first_name)}](tg://user?id={user_id}) ارسال شد:\n🎬 {escape_markdown(caption)}",
        parse_mode="MarkdownV2",
        reply_markup=markup
    )

    bot.reply_to(message, f"{kind.capitalize()} شما دریافت شد و در انتظار تایید مالک است ⏳")

# =======================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve:", "reject:")))
def handle_approval(call):
    action, pending_id = call.data.split(":")
    media_info = pending_col.find_one({"_id": pending_id})

    if not media_info:
        bot.answer_callback_query(call.id, "پیدا نشد ❌", show_alert=True)
        return

    from_id = media_info["from_id"]
    file_id = media_info["file_id"]
    title = media_info["title"]
    caption = media_info.get("caption", title)
    kind = media_info["kind"]

    if action == "approve":
        send_to_channel_and_save(file_id, title, caption=caption, kind=kind)
        bot.send_message(from_id, f"{kind.capitalize()} شما تایید و ذخیره شد ✅\n🎬 {caption}")
        bot.answer_callback_query(call.id, f"{kind.capitalize()} تایید شد ✅", show_alert=True)
    else:
        bot.send_message(from_id, f"{kind.capitalize()} شما رد شد ❌\n🎬 {caption}")
        bot.answer_callback_query(call.id, f"{kind.capitalize()} رد شد ❌", show_alert=True)

    pending_col.delete_one({"_id": pending_id})

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "ربات آماده است 🤖\nویدئو یا آهنگ را در پی‌وی ارسال کنید.")

# =======================
@bot.inline_handler(lambda query: True)
def inline_query(query):
    from telebot.types import InlineQueryResultCachedVideo, InlineQueryResultCachedAudio
    results = []

    q = query.query.lower()
    if q.startswith("music"):
        items = music_col.find().sort("_id", -1).limit(10)
        for idx, m in enumerate(items):
            artist = m.get("artist", "ناشناخته")
            caption = m.get("caption", "بدون توضیح")
            results.append(
                InlineQueryResultCachedAudio(
                    id=str(idx),
                    audio_file_id=m["file_id"],
                    title=m["title"],
                    performer=artist,
                    caption=caption
                )
            )
    else:
        items = videos_col.find().sort("_id", -1).limit(10)
        for idx, v in enumerate(items):
            caption = v.get("caption", "بدون توضیح")
            results.append(
                InlineQueryResultCachedVideo(
                    id=str(idx),
                    video_file_id=v["file_id"],
                    title=v["title"],
                    description=caption
                )
            )

    bot.answer_inline_query(query.id, results)

# =======================
# دستور ساعت
@bot.message_handler(commands=["time"])
def send_time(message):
    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    bot.send_message(message.chat.id, f"🕒 زمان جهانی: {now.strftime('%H:%M')}")

# =======================
scheduler = BackgroundScheduler(timezone=pytz.UTC)
time_message_id = None

def send_time_all():
    global time_message_id
    now = datetime.now(pytz.UTC)
    text = f"🕒 زمان جهانی: {now.strftime('%H:%M')}"
    try:
        if time_message_id:
            bot.delete_message(OWNER_ID, time_message_id)
        msg = bot.send_message(OWNER_ID, text)
        time_message_id = msg.message_id
    except Exception as e:
        print("Error sending time:", e)

scheduler.add_job(send_time_all, 'interval', minutes=1)
scheduler.start()

# =======================
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running ✅"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# =======================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
