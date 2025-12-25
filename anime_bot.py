import telebot
from telebot import types
from hashlib import md5
from pymongo import MongoClient
from flask import Flask
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import os

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
musics_col = db["musics"]
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

admins = get_admins()

# =======================
def save_video(file_id, title, tags):
    if not videos_col.find_one({"file_id": file_id}):
        videos_col.insert_one({"file_id": file_id, "title": title, "tags": tags})
        print("Video saved:", file_id, title)

def save_music(file_id, title, singer):
    if not musics_col.find_one({"file_id": file_id}):
        musics_col.insert_one({"file_id": file_id, "title": title, "singer": singer})
        print("Music saved:", file_id, title)

def send_to_channel_and_save(file_id, title, tags=None, is_music=False, singer=None):
    """ارسال ویدئو یا آهنگ به کانال و ذخیره واقعی file_id"""
    try:
        if is_music:
            sent_msg = bot.send_audio(CHANNEL_ID, file_id, caption=f"{title} - {singer}")
            save_music(sent_msg.audio.file_id, title, singer)
        else:
            sent_msg = bot.send_video(CHANNEL_ID, file_id, caption=title)
            save_video(sent_msg.video.file_id, title, tags or [])
    except Exception as e:
        print("Error sending media to channel:", e)

# =======================
@bot.message_handler(content_types=['video', 'document', 'audio'])
def handle_media(message):
    file_id = None
    title = message.caption or "بدون عنوان"
    user_id = message.from_user.id
    user_mention = f"[{escape_markdown(message.from_user.first_name)}](tg://user?id={user_id})"

    # فایل ویدئو یا آهنگ
    is_music = False
    singer = None
    if message.audio:
        file_id = message.audio.file_id
        is_music = True
        singer = "ناشناس"  # می‌تونی از caption استخراج کنی اگر گذاشت
    elif message.video:
        file_id = message.video.file_id
    elif message.document and message.document.mime_type.startswith("video/"):
        file_id = message.document.file_id
    else:
        return

    if user_id == OWNER_ID:
        send_to_channel_and_save(file_id, title, is_music=is_music, singer=singer)
        bot.reply_to(message, f"{'آهنگ' if is_music else 'ویدئو'} ذخیره شد ✅\n🎬 {title}")
        return

    # کاربران دیگر → تایید مالک
    pending_id = md5(file_id.encode()).hexdigest()[:10]
    pending_col.insert_one({
        "_id": pending_id,
        "file_id": file_id,
        "title": title,
        "from_id": user_id,
        "is_music": is_music,
        "singer": singer
    })

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ تایید", callback_data=f"approve:{pending_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject:{pending_id}")
    )

    bot.send_message(
        OWNER_ID,
        f"{user_mention} یک {'آهنگ' if is_music else 'ویدئو'} ارسال کرده:\n🎬 {escape_markdown(title)}",
        parse_mode="MarkdownV2",
        reply_markup=markup
    )

    bot.reply_to(message, f"{'آهنگ' if is_music else 'ویدئو'} شما در انتظار تایید مالک است ⏳")

# =======================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve:", "reject:")))
def handle_approval(call):
    action, pending_id = call.data.split(":")
    media_info = pending_col.find_one({"_id": pending_id})

    if not media_info:
        bot.answer_callback_query(call.id, "فایل پیدا نشد ❌", show_alert=True)
        return

    from_id = media_info["from_id"]
    file_id = media_info["file_id"]
    title = media_info["title"]
    is_music = media_info.get("is_music", False)
    singer = media_info.get("singer", None)

    if action == "approve":
        send_to_channel_and_save(file_id, title, is_music=is_music, singer=singer)
        bot.send_message(from_id, f"{'آهنگ' if is_music else 'ویدئو'} شما تایید و ذخیره شد ✅\n🎬 {title}")
        bot.answer_callback_query(call.id, "تایید شد ✅", show_alert=True)
    else:
        bot.send_message(from_id, f"{'آهنگ' if is_music else 'ویدئو'} شما رد شد ❌\n🎬 {title}")
        bot.answer_callback_query(call.id, "رد شد ❌", show_alert=True)

    pending_col.delete_one({"_id": pending_id})

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "ربات آماده است 🤖\nویدئو یا آهنگ را در پی‌وی ارسال کنید.")

# =======================
# Inline Query
@bot.inline_handler(lambda query: True)
def inline_query(query):
    from telebot.types import InlineQueryResultCachedVideo, InlineQueryResultCachedAudio
    text = query.query.lower()
    results = []

    if text == "music":
        musics = musics_col.find().sort("_id", -1).limit(10)
        for idx, m in enumerate(musics):
            results.append(
                InlineQueryResultCachedAudio(
                    id=str(idx),
                    audio_file_id=m["file_id"],
                    title=m["title"],
                    performer=m.get("singer", "ناشناس"),
                )
            )
    else:
        videos = videos_col.find().sort("_id", -1).limit(10)
        for idx, v in enumerate(videos):
            tag = v.get("tags", ["ویدئو"])[0]  # حداقل یکی از تگ‌ها
            results.append(
                InlineQueryResultCachedVideo(
                    id=str(idx),
                    video_file_id=v["file_id"],
                    title=v["title"],
                    description=tag,
                )
            )

    bot.answer_inline_query(query.id, results)

# =======================
# دستور ساعت
@bot.message_handler(commands=["time"])
def send_time(message):
    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    sent_msg = bot.send_message(message.chat.id, f"🕒 زمان جهانی: {now.strftime('%H:%M')}")
    # حذف خودکار بعد 60 ثانیه
    threading.Timer(60, lambda: bot.delete_message(message.chat.id, sent_msg.message_id)).start()

# =======================
# برنامه زمان‌بندی شده هر دقیقه
scheduler = BackgroundScheduler(timezone=pytz.UTC)
def send_time_all():
    now = datetime.now(pytz.UTC)
    text = f"🕒 زمان جهانی: {now.strftime('%H:%M')}"
    try:
        sent_msg = bot.send_message(OWNER_ID, text)
        threading.Timer(60, lambda: bot.delete_message(OWNER_ID, sent_msg.message_id)).start()
    except Exception as e:
        print("Error sending time:", e)

scheduler.add_job(send_time_all, 'interval', minutes=1)
scheduler.start()

# =======================
# مدیریت ادمین‌ها
@bot.message_handler(commands=["addadmin"])
def add_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "شما دسترسی ندارید ❌")
        return
    try:
        user_id = int(message.text.split()[1])
        admins.append(user_id)
        save_admins_list(admins)
        bot.reply_to(message, f"ادمین اضافه شد ✅: {user_id}")
    except:
        bot.reply_to(message, "استفاده: /addadmin <user_id>")

@bot.message_handler(commands=["removeadmin"])
def remove_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "شما دسترسی ندارید ❌")
        return
    try:
        user_id = int(message.text.split()[1])
        if user_id in admins:
            admins.remove(user_id)
            save_admins_list(admins)
            bot.reply_to(message, f"ادمین حذف شد ✅: {user_id}")
        else:
            bot.reply_to(message, "این کاربر ادمین نیست")
    except:
        bot.reply_to(message, "استفاده: /removeadmin <user_id>")

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
