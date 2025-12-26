import os
import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask, request

# =======================
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
bot = telebot.TeleBot(TOKEN, threaded=False, skip_pending=True)

OWNER_ID = 6433381392
ALLOWED_USERS = [6433381392, 7851824627]
CHANNEL_USERNAME = "anime_1127"

# =======================
MONGO_URI = "mongodb://self_login:tiam_jinx@ac-nbipb9g-shard-00-00.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-01.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-02.v2vzh9e.mongodb.net:27017/?replicaSet=atlas-qppgrd-shard-0&ssl=true&authSource=admin"
mongo = MongoClient(MONGO_URI)
db = mongo["telegram_bot"]
videos_col = db["videos"]
admins_col = db["admins"]

# =======================
def is_admin(user_id):
    return admins_col.find_one({"user_id": user_id}) or user_id == OWNER_ID

# =======================
# ویدئو
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    user_id = message.from_user.id
    is_from_channel = message.forward_from_chat and message.forward_from_chat.username == CHANNEL_USERNAME
    if not (user_id in ALLOWED_USERS or is_from_channel):
        return

    file_id = message.video.file_id if message.video else None
    if not file_id and message.document and message.document.mime_type.startswith("video/"):
        file_id = message.document.file_id

    if not file_id or videos_col.find_one({"file_id": file_id}):
        return

    caption = message.caption or "ویدئو بدون متن"
    videos_col.insert_one({"file_id": file_id, "caption": caption})
    bot.send_video(OWNER_ID, file_id, caption=caption, disable_notification=True)

# =======================
# مدیریت ادمین
@bot.message_handler(commands=["addadmin"])
def add_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما اجازه اضافه کردن ادمین را ندارید")
        return
    try:
        uid = int(message.text.split()[1])
        if not admins_col.find_one({"user_id": uid}):
            admins_col.insert_one({"user_id": uid})
            bot.reply_to(message, "ادمین اضافه شد ✅")
        else:
            bot.reply_to(message, "قبلاً ادمین بوده")
    except:
        bot.reply_to(message, "فرمت اشتباه")

@bot.message_handler(commands=["removeadmin"])
def remove_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما دستر رسی حذف ادمین را ندارید")
        return
    try:
        uid = int(message.text.split()[1])
        admins_col.delete_one({"user_id": uid})
        bot.reply_to(message, "ادمین حذف شد ❌")
    except:
        bot.reply_to(message, "دستور اشتباه است")

# =======================
# دستور /add
@bot.message_handler(commands=["add"])
def add_video_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط ادمین ها اجازه اد کردن دارند")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "روی ویدئو ریپلای کن")
        return

    reply = message.reply_to_message
    file_id = reply.video.file_id if reply.video else None
    if not file_id and reply.document and reply.document.mime_type.startswith("video/"):
        file_id = reply.document.file_id

    if not file_id or videos_col.find_one({"file_id": file_id}):
        bot.reply_to(message, "قبلاً ذخیره شده یا ویدئو نیست")
        return

    caption = reply.caption or "ویدئو بدون متن"
    videos_col.insert_one({"file_id": file_id, "caption": caption})
    bot.reply_to(message, "ویدئو اضافه شد ✅")
    bot.send_video(OWNER_ID, file_id, caption=caption, disable_notification=True)

# =======================
# Inline Mode
@bot.inline_handler(func=lambda q: True)
def inline_query(inline_query):
    results = []
    for idx, video in enumerate(videos_col.find()):
        results.append(
            types.InlineQueryResultCachedVideo(
                id=str(idx),
                video_file_id=video["file_id"],
                title=video["caption"][:30],
                description=video["caption"],
                caption=video["caption"]
            )
        )
    bot.answer_inline_query(inline_query.id, results, cache_time=0)

# =======================
# Flask برای وبهوک
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive ✅"

@app.route(f"/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# =======================
if __name__ == "__main__":
    # وبهوک ست می‌کنیم
    URL = "https://anime-1127-bot.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
