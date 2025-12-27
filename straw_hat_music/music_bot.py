import os
import time
import threading
import requests
from datetime import datetime
from flask import Flask, request, render_template_string
import telebot
from telebot import types
from pymongo import MongoClient, errors

# =======================
TOKEN = "8569519729:AAG2ZLf5xn_2pNtuGDaXF_y_88SU-dqUnis"
bot = telebot.TeleBot(TOKEN, threaded=False)

# =======================
# دسترسی‌ها
OWNERS_IDS = [6433381392, 6409859836]

def is_owner(user_id):
    return user_id in OWNERS_IDS

# مدیرها و ادمین‌ها در دیتابیس ذخیره می‌شوند
def is_admin(user_id):
    admin = admins_col.find_one({"user_id": user_id, "role": "admin"})
    return admin is not None or is_owner(user_id)

def is_manager(user_id):
    manager = admins_col.find_one({"user_id": user_id, "role": "manager"})
    return manager is not None or is_owner(user_id)

# =======================
ALLOWED_USERS = [6433381392, 6409859836]
CHANNEL_USERNAME = "JUDUHDHJHDV"
keep_alive_running = False
logs = []

def log_event(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {text}")
    if len(logs) > 100:
        logs.pop(0)

# =======================
# اتصال MongoDB
MONGO_URI = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

try:
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000, tls=True, tlsAllowInvalidCertificates=True)
    db = mongo["telegram_bot"]
    audios_col = db["audios"]
    admins_col = db["admins"]
    mongo.admin.command("ping")
    print("✅ اتصال موفق به MongoDB")
except errors.ServerSelectionTimeoutError as err:
    print("❌ خطای اتصال MongoDB:", err)
    raise

# =======================
# دستورات شروع و راهنما
@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.reply_to(message, "🎵 سلام به ربات straw hat music خوش اومدی!\n\nبرای راهنما /help را بزن")

@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.reply_to(
        message,
        "🎧 راهنمای ربات موسیقی\n\n"
        "🔎 دیدن و جستجو کردن آهنگ\n"
        "@straw_hat_music11Bot <--- این رو خالی بنویس همه آهنگ‌ها رو ببینی\n"
        "@straw_hat_music11Bot <--- دنبال یه آهنگ خاص می‌گردی اسمشو جلوی این بنویس\n"
        "@JUDUHDHJHDV یه سر به چنل هم بزن چون توی اینجا هم آهنگ می‌زاریم😁"
    )

# =======================
# دریافت Audio و Voice
@bot.message_handler(content_types=["audio", "voice"])
def handle_audio(message):
    user_id = message.from_user.id
    is_allowed_user = user_id in ALLOWED_USERS and message.chat.type == "private"
    is_from_channel = getattr(message.forward_from_chat, "username", None) == CHANNEL_USERNAME if message.forward_from_chat else False
    if not (is_allowed_user or is_from_channel):
        return

    if message.audio:
        audio = message.audio
    elif message.voice:
        audio = message.voice
    else:
        return

    # گرفتن عنوان و خواننده از تلگرام
    if hasattr(audio, "title") and audio.title and hasattr(audio, "performer") and audio.performer:
        caption = f"{audio.title} - {audio.performer}"
    else:
        return  # اگر عنوان یا خواننده وجود نداشت، ذخیره نکن

    file_id = audio.file_id
    duration = audio.duration

    if audios_col.find_one({"file_id": file_id}):
        return

    audios_col.insert_one({"file_id": file_id, "caption": caption, "duration": duration})
    for owner in OWNERS_IDS:
        bot.send_audio(owner, file_id, caption=caption, disable_notification=True)
    log_event(f"Audio saved by {user_id}: {caption}")

# =======================
# اضافه کردن و حذف آهنگ
@bot.message_handler(commands=["addmusic"])
def add_audio_cmd(message):
    if not (is_admin(message.from_user.id) or is_manager(message.from_user.id) or is_owner(message.from_user.id)):
        bot.reply_to(message, "❌ دسترسی ندارید")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "روی آهنگ یا ویس ریپلای کن")
        return

    reply = message.reply_to_message
    if reply.audio:
        audio = reply.audio
    elif reply.voice:
        audio = reply.voice
    else:
        bot.reply_to(message, "❌ فایل معتبر نیست")
        return

    if not hasattr(audio, "title") or not audio.title or not hasattr(audio, "performer") or not audio.performer:
        bot.reply_to(message, "❌ فایل باید دارای نام آهنگ و خواننده باشد")
        return

    caption = f"{audio.title} - {audio.performer}"
    file_id = audio.file_id
    duration = audio.duration

    if audios_col.find_one({"file_id": file_id}):
        bot.reply_to(message, "قبلاً ذخیره شده")
        return

    audios_col.insert_one({"file_id": file_id, "caption": caption, "duration": duration})
    bot.reply_to(message, "آهنگ اضافه شد ✅")
    log_event(f"User {message.from_user.id} added audio")

@bot.message_handler(commands=["removmusic"])
def remove_audio(message):
    if not (is_admin(message.from_user.id) or is_manager(message.from_user.id) or is_owner(message.from_user.id)):
        bot.reply_to(message, "❌ دسترسی ندارید")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "روی آهنگ ریپلای کن")
        return

    reply = message.reply_to_message
    if reply.audio:
        file_id = reply.audio.file_id
    elif reply.voice:
        file_id = reply.voice.file_id
    else:
        bot.reply_to(message, "❌ فایل پیدا نشد")
        return

    result = audios_col.delete_one({"file_id": file_id})
    bot.reply_to(message, "حذف شد ✅" if result.deleted_count else "در دیتابیس نبود")

# =======================
# دستورات افزودن/حذف ادمین با آیدی عددی
@bot.message_handler(commands=["addadmin"])
def add_admin_cmd(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ فقط مالک کل می‌تواند این کار را انجام دهد")
        return
    try:
        admin_id = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ باید آیدی عددی ادمین رو وارد کنید\nمثال: /addadmin 123456789")
        return
    if admins_col.find_one({"user_id": admin_id}):
        bot.reply_to(message, "این کاربر قبلاً ادمین است")
        return
    admins_col.insert_one({"user_id": admin_id, "role": "admin"})
    bot.reply_to(message, f"✅ {admin_id} به عنوان ادمین اضافه شد")

@bot.message_handler(commands=["deladmin"])
def del_admin_cmd(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ فقط مالک کل می‌تواند این کار را انجام دهد")
        return
    try:
        admin_id = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ باید آیدی عددی ادمین رو وارد کنید\nمثال: /deladmin 123456789")
        return
    result = admins_col.delete_one({"user_id": admin_id, "role": "admin"})
    bot.reply_to(message, "✅ حذف شد" if result.deleted_count else "❌ ادمین پیدا نشد")

# =======================
# جستجوی اینلاین
@bot.inline_handler(func=lambda q: True)
def inline_handler(inline_query):
    query = inline_query.query.strip().lower()
    results = []
    cursor = audios_col.find({} if query == "" else {"caption": {"$regex": query, "$options": "i"}})
    for idx, audio in enumerate(cursor):
        if idx >= 50: break
        results.append(types.InlineQueryResultCachedAudio(id=f"audio_{idx}", audio_file_id=audio["file_id"], caption=audio.get("caption")))
    bot.answer_inline_query(inline_query.id, results, cache_time=0, is_personal=True)

# =======================
# Keep-Alive
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
    if not is_owner(message.from_user.id):
        return
    if keep_alive_running:
        bot.reply_to(message, "ربات بیداره")
        return
    keep_alive_running = True
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    bot.reply_to(message, "ربات فعال شد 🔥")

@bot.message_handler(commands=["sleep"])
def sleep_bot(message):
    global keep_alive_running
    if is_owner(message.from_user.id):
        keep_alive_running = False
        bot.reply_to(message, "ربات خاموش شد 😴")

# =======================
# Flask Webhook
app = Flask(__name__)
@app.route("/")
def home():
    return render_template_string("<h2>Music Bot Alive 🎵</h2><ul>{% for l in logs %}<li>{{l}}</li>{% endfor %}</ul>", logs=logs)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    except Exception as e:
        import traceback
        print("Webhook error:", e)
        traceback.print_exc()
        return f"Internal Server Error: {e}", 500

# =======================
if __name__ == "__main__":
    URL = "https://anime-1127-bot-2.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
