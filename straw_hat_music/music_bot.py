import requests
import threading
import time
import os
import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask, request, render_template_string
from datetime import datetime

# =======================
TOKEN = "8569519729:AAG2ZLf5xn_2pNtuGDaXF_y_88SU-dqUnis"
bot = telebot.TeleBot(TOKEN, threaded=False)

OWNER_ID = 6409859836
ALLOWED_USERS = [6433381392, 6409859836]
CHANNEL_USERNAME = "JUDUHDHJHDV"
keep_alive_running = False
# =======================

# MongoDB جدید
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://strawhatmusicdb_db_user:db_strawhatmusic@cluster0.morh5s8.mongodb.net/strawhatmusic?retryWrites=true&w=majority"

mongo = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = mongo["strawhatmusic"]
audios_col = db["audios"]
admins_col = db["admins"]

# =======================
logs = []

def log_event(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {text}")
    if len(logs) > 100:
        logs.pop(0)

def is_admin(user_id):
    return admins_col.find_one({"user_id": user_id}) or user_id == OWNER_ID

# =======================
@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.reply_to(
        message,
        "🎵 سلام به ربات straw hat music خوش اومدی!\n\n"
        "این ربات  پر از اهنگ های قشنگه.\n"
        "برای راهنما دستور /help رو بزن"
)
@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.reply_to(
        message,
        "🎧 راهنمای ربات موسیقی\n\n"
        "🔎 دیدن و جستو جو کردن اهنگ\n"
        "@straw_hat_music11Bot <--- این رو خالی بنویس همه اهنگ ها رو ببینی\n\n"
        "@straw_hat_music11Bot <--- دنبال یه آهنگ خاص میگردی اسمشو جلوی این بنویس\n\n"
        "خب اگه آهنگی که میخواستی رپ پیدا نکردی بیا به @Monkey_d_luffy12345666 این بگو\n\n"
        "@JUDUHDHJHDV یه سر به چنل هم بزن چون توی اینجا هم اهنگ میزاریم😁"
    )

# =======================
# دریافت Audio و Voice
@bot.message_handler(content_types=["audio"])
def handle_audio(message):
    user_id = message.from_user.id

    is_allowed_user = user_id in ALLOWED_USERS and message.chat.type == "private"
    is_from_channel = (
        getattr(message.forward_from_chat, "username", None) == CHANNEL_USERNAME
        if message.forward_from_chat else False
    )

    if not (is_allowed_user or is_from_channel):
        return

    file_id = None
    duration = None

    if message.audio:
        file_id = message.audio.file_id
        duration = message.audio.duration
    elif message.voice:
        file_id = message.voice.file_id
        duration = message.voice.duration

    if not file_id or audios_col.find_one({"file_id": file_id}):
        return

    caption = message.caption or "آهنگ بدون عنوان"

    audios_col.insert_one({
        "file_id": file_id,
        "caption": caption,
        "duration": duration
    })

    bot.send_audio(OWNER_ID, file_id, caption=caption, disable_notification=True)
    log_event(f"Audio saved by {user_id}: {caption}")

# =======================
@bot.message_handler(commands=["addmusic"])
def add_audio_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط ادمین‌ها")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "روی آهنگ یا ویس ریپلای کن")
        return

    reply = message.reply_to_message

    file_id = None
    duration = None

    if reply.audio:
        file_id = reply.audio.file_id
        duration = reply.audio.duration
    elif reply.voice:
        file_id = reply.voice.file_id
        duration = reply.voice.duration

    if not file_id or audios_col.find_one({"file_id": file_id}):
        bot.reply_to(message, "قبلاً ذخیره شده یا فایل معتبر نیست")
        return

    caption = reply.caption or "آهنگ بدون عنوان"

    audios_col.insert_one({
        "file_id": file_id,
        "caption": caption,
        "duration": duration
    })

    bot.reply_to(message, "آهنگ اضافه شد ✅")
    log_event(f"Admin {message.from_user.id} added audio")

# =======================
@bot.message_handler(commands=["removmusic"])
def remove_audio(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ دسترسی نداری")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "روی آهنگ ریپلای کن")
        return

    reply = message.reply_to_message
    file_id = reply.audio.file_id if reply.audio else reply.voice.file_id if reply.voice else None

    if not file_id:
        bot.reply_to(message, "فایل پیدا نشد")
        return

    result = audios_col.delete_one({"file_id": file_id})
    bot.reply_to(message, "حذف شد ✅" if result.deleted_count else "در دیتابیس نبود")

# =======================
# Inline Search
@bot.inline_handler(func=lambda q: True)
def inline_handler(inline_query):
    query = inline_query.query.strip().lower()
    results = []

    cursor = audios_col.find(
        {} if query == "" else {
            "caption": {"$regex": query, "$options": "i"}
        }
    )

    for idx, audio in enumerate(cursor):
        if idx >= 50:
            break

        results.append(
            types.InlineQueryResultCachedAudio(
                id=f"audio_{idx}",
                audio_file_id=audio["file_id"],
                caption=audio.get("caption", "🎵")
            )
        )

    bot.answer_inline_query(
        inline_query.id,
        results,
        cache_time=0,
        is_personal=True
    )

# =======================
def keep_alive_loop():
    global keep_alive_running
    while keep_alive_running:
        try:
            requests.get("https://anime-1127-bot-2.onrender.com/")
        except:
            pass
        time.sleep(300)

@bot.message_handler(commands=["awake"])
def awake_bot(message):
    global keep_alive_running
    if message.from_user.id != OWNER_ID:
        return
    if keep_alive_running:
        bot.reply_to(message, "ربات بیداره")
        return
    keep_alive_running = True
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    bot.reply_to(message, "بیدار شد 🔥")

@bot.message_handler(commands=["sleep"])
def sleep_bot(message):
    global keep_alive_running
    if message.from_user.id == OWNER_ID:
        keep_alive_running = False
        bot.reply_to(message, "خوابید 😴")

# =======================
app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string(
        "<h2>Music Bot Alive 🎵</h2><ul>{% for l in logs %}<li>{{l}}</li>{% endfor %}</ul>",
        logs=logs
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.get_data().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "", 200

# =======================
if __name__ == "__main__":
    URL = "https://anime-1127-bot-2.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
