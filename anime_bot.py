import telebot
from telebot import types
from hashlib import md5
from pymongo import MongoClient
from flask import Flask
import threading

# =======================
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
bot = telebot.TeleBot(TOKEN, parse_mode=None)

OWNER_ID = 6433381392

# =======================
MONGO_URI = "mongodb+srv://self_login:tiam_jinx@self.v2vzh9e.mongodb.net/anime_bot_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["anime_bot_db"]

admins_col = db["admins"]
videos_col = db["videos"]
pending_col = db["pending_videos"]

# =======================
# تابع Escape MarkdownV2
def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + c if c in escape_chars else c for c in text])

# =======================
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

def add_pending(pending_id, file_id, title, from_id):
    pending_col.insert_one({
        "_id": pending_id,
        "file_id": file_id,
        "title": title,
        "from_id": from_id
    })

def remove_pending(pending_id):
    pending_col.delete_one({"_id": pending_id})

def get_pending(pending_id):
    return pending_col.find_one({"_id": pending_id})

admins = get_admins()

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

    # مالک مستقیم ذخیره می‌کند
    if user_id == OWNER_ID:
        save_video(file_id, title)
        bot.reply_to(message, f"ویدئو ذخیره شد ✅\n🎬 {title}")
        return

    # مدیر یا کاربران دیگر → باید تایید شود
    pending_id = md5(file_id.encode()).hexdigest()[:10]
    add_pending(pending_id, file_id, title, user_id)

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
    video_info = get_pending(pending_id)

    if not video_info:
        bot.answer_callback_query(call.id, "ویدئو پیدا نشد ❌", show_alert=True)
        return

    from_id = video_info["from_id"]
    file_id = video_info["file_id"]
    title = video_info["title"]

    if action == "approve":
        # فقط ذخیره می‌کنه
        save_video(file_id, title)
        bot.send_message(from_id, f"ویدئو شما تایید و ذخیره شد ✅\n🎬 {title}")
        bot.answer_callback_query(call.id, f"ویدئو تایید شد ✅", show_alert=True)
    else:
        bot.send_message(from_id, f"ویدئو شما رد شد ❌\n🎬 {title}")
        bot.answer_callback_query(call.id, f"ویدئو رد شد ❌", show_alert=True)

    remove_pending(pending_id)

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "ربات آماده است 🤖\nویدئو را در پی‌وی ارسال کنید.")

# =======================
# Inline Query handler
@bot.inline_handler(lambda query: True)
def inline_query(query):
    from telebot.types import InlineQueryResultArticle, InputTextMessageContent
    results = []
    videos = videos_col.find().sort("_id", -1).limit(5)
    for idx, v in enumerate(videos):
        results.append(
            InlineQueryResultArticle(
                id=str(idx),
                title=v["title"],
                input_message_content=InputTextMessageContent(
                    f"🎬 {v['title']}\nFile ID: {v['file_id']}"
                ),
            )
        )
    bot.answer_inline_query(query.id, results)

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
