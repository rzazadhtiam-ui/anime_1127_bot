import telebot
from telebot import types
from hashlib import md5
from pymongo import MongoClient
from flask import Flask
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# =======================
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
bot = telebot.TeleBot(TOKEN, parse_mode=None)

OWNER_ID = 6433381392
CHANNEL_ID = "@asta_tiam_cannel"  # کانال ربات

# =======================
MONGO_URI = "mongodb+srv://self_login:tiam_jinx@self.v2vzh9e.mongodb.net/anime_bot_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["anime_bot_db"]

videos_col = db["videos"]
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

def save_admins_list(admins):
    admins_col.update_one({"_id": "admins"}, {"$set": {"list": admins}}, upsert=True)

def save_video(file_id, title):
    if not videos_col.find_one({"file_id": file_id}):
        videos_col.insert_one({"file_id": file_id, "title": title})
        print("Video saved:", file_id, title)

admins = get_admins()

# =======================
def send_to_channel_and_save(file_id, title):
    """ویدئو رو به چنل می‌فرسته و بعد file_id واقعی چنل رو ذخیره می‌کنه"""
    try:
        sent_msg = bot.send_video(CHANNEL_ID, file_id, caption=title)
        channel_file_id = sent_msg.video.file_id
        save_video(channel_file_id, title)
    except Exception as e:
        print("Error sending video to channel:", e)

# =======================
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    file_id = None
    title = message.caption or "ویدئو بدون عنوان"
    user_id = message.from_user.id
    user_mention = f"[{escape_markdown(message.from_user.first_name)}](tg://user?id={user_id})"

    if message.video:
        file_id = message.video.file_id
    elif message.document and message.document.mime_type.startswith("video/"):
        file_id = message.document.file_id

    if not file_id:
        return

    if user_id == OWNER_ID:
        send_to_channel_and_save(file_id, title)
        bot.reply_to(message, f"ویدئو ذخیره شد ✅\n🎬 {title}")
        return

    # کاربران دیگر → باید تایید مالک شود
    pending_id = md5(file_id.encode()).hexdigest()[:10]
    pending_col.insert_one({
        "_id": pending_id,
        "file_id": file_id,
        "title": title,
        "from_id": user_id
    })

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"approve:{pending_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject:{pending_id}")
    )

    bot.send_message(
        OWNER_ID,
        f"{user_mention} یک ویدئو ارسال کرده:\n🎬 {escape_markdown(title)}",
        parse_mode="MarkdownV2",
        reply_markup=markup
    )

    bot.reply_to(message, "ویدئو شما در انتظار تایید مالک است ⏳")

# =======================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve:", "reject:")))
def handle_approval(call):
    action, pending_id = call.data.split(":")
    video_info = pending_col.find_one({"_id": pending_id})

    if not video_info:
        bot.answer_callback_query(call.id, "ویدئو پیدا نشد ❌", show_alert=True)
        return

    from_id = video_info["from_id"]
    file_id = video_info["file_id"]
    title = video_info["title"]

    if action == "approve":
        send_to_channel_and_save(file_id, title)
        bot.send_message(from_id, f"ویدئو شما تایید و ذخیره شد ✅\n🎬 {title}")
        bot.answer_callback_query(call.id, "ویدئو تایید شد ✅", show_alert=True)
    else:
        bot.send_message(from_id, f"ویدئو شما رد شد ❌\n🎬 {title}")
        bot.answer_callback_query(call.id, "ویدئو رد شد ❌", show_alert=True)

    pending_col.delete_one({"_id": pending_id})

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "ربات آماده است 🤖\nویدئو را در پی‌وی ارسال کنید.")

# =======================
@bot.inline_handler(lambda query: True)
def inline_query(query):
    from telebot.types import InlineQueryResultCachedVideo
    results = []
    videos = videos_col.find().sort("_id", -1).limit(10)
    for idx, v in enumerate(videos):
        results.append(
            InlineQueryResultCachedVideo(
                id=str(idx),
                video_file_id=v["file_id"],
                title=v["title"],
                description="#ویدئو",  # تگ ویدئو
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
# برنامه زمان‌بندی شده هر دقیقه
scheduler = BackgroundScheduler(timezone=pytz.UTC)
def send_time_all():
    now = datetime.now(pytz.UTC)
    text = f"🕒 زمان جهانی: {now.strftime('%H:%M')}"
    try:
        bot.send_message(OWNER_ID, text)
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
    bot.infinity_polling()  # ← پرانتز فراموش نشه
