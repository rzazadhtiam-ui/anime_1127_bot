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
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
BOT_USERNAME = "anime_1127_bot"
bot = telebot.TeleBot(TOKEN, threaded=True)

OWNER_ID = 6433381392
ALLOWED_USERS = [6433381392, 7851824627]
CHANNEL_USERNAME = "anime_1127"
keep_alive_running = False

# =======================
MONGO_URI = "mongodb://self_login:tiam_jinx@ac-nbipb9g-shard-00-00.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-01.v2vzh9e.mongodb.net:27017,ac-nbipb9g-shard-00-02.v2vzh9e.mongodb.net:27017/?replicaSet=atlas-qppgrd-shard-0&ssl=true&authSource=admin"
mongo = MongoClient(MONGO_URI)
db = mongo["telegram_bot"]
videos_col = db["videos"]
admins_col = db["admins"]

logs = []
user_next_message = {}  # برای /echo و send_request

def log_event(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {text}")
    if len(logs) > 100:
        logs.pop(0)

def is_admin(user_id):
    return admins_col.find_one({"user_id": user_id}) or user_id == OWNER_ID

def get_video_file_id(message):
    try:
        if hasattr(message, 'video') and message.video:
            return message.video.file_id
        if hasattr(message, 'document') and message.document:
            if message.document.mime_type.startswith("video/") or message.document.mime_type in ["application/octet-stream"]:
                return message.document.file_id
    except Exception:
        return None
    return None

# =======================
# /start
@bot.message_handler(commands=["start", f"start@{BOT_USERNAME}"])
def start_cmd(message):
    text = (
        "👋 سلام، خوش اومدی به ربات anime_Bot!\n\n"
        "🎬 این ربات مخصوص دیدن ادیت‌های فیلم، بازی و انیمه‌ست.\n"
        "برای دیدن راهنما دستور /help رو بزن"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("پنل ربات", switch_inline_query_current_chat=f"@{BOT_USERNAME}"))
    bot.reply_to(message, text, reply_markup=markup)

# /help
@bot.message_handler(commands=["help", f"help@{BOT_USERNAME}"])
def help_cmd(message):
    text = (
        "راهنما ربات:\n\n"
        "🎬 مخصوص دیدن ادیت‌های فیلم، بازی و انیمه‌ست.\n\n"
        "📌 روش استفاده:\n"
        f"@{BOT_USERNAME} یا @{BOT_USERNAME} <کلمه>\n\n"
        "❗ اگر ادیتی خواستی که نبود، بهم پیام بده:\n"
        "👉 @asta_TIAM\n\n"
        "📣 برای دیدن ادیت‌های بیشتر، به چنل ما سر بزن:\n"
        "👉 @anime_1127"
    )
    bot.reply_to(message, text)

# /search
@bot.message_handler(commands=["search", f"search@{BOT_USERNAME}"])
def search_panel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("پنل جستجو", switch_inline_query_current_chat=f"@{BOT_USERNAME}"))
    bot.reply_to(message, "برای جستجو روی دکمه زیر بزن:", reply_markup=markup)

# =======================
# Video Handler
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    user_id = message.from_user.id
    is_allowed_user = user_id in ALLOWED_USERS and message.chat.type == "private"
    is_from_channel = getattr(message.forward_from_chat, "username", None) == CHANNEL_USERNAME if message.forward_from_chat else False

    if not (is_allowed_user or is_from_channel):
        return

    file_id = get_video_file_id(message)
    if not file_id or videos_col.find_one({"file_id": file_id}):
        return

    caption = message.caption or "ویدئو بدون متن"
    videos_col.insert_one({"file_id": file_id, "caption": caption})
    bot.send_video(OWNER_ID, file_id, caption=caption, disable_notification=True)
    log_event(f"User {user_id} ارسال ویدئو: {caption}")

# =======================
# /add
@bot.message_handler(commands=["add", f"add@{BOT_USERNAME}"])
def add_video_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط ادمین ها اجازه اد کردن دارند")
        log_event(f"User {message.from_user.id} تلاش برای add ویدئو بدون دسترسی")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "روی ویدئو ریپلای کن")
        log_event(f"User {message.from_user.id} دستور add داد بدون ریپلای")
        return

    file_id = get_video_file_id(message.reply_to_message)
    if not file_id or videos_col.find_one({"file_id": file_id}):
        bot.reply_to(message, "قبلاً ذخیره شده یا ویدئو نیست")
        log_event(f"User {message.from_user.id} تلاش کرد ویدئو add کند که قبلاً ذخیره شده یا ویدئو نیست")
        return

    caption = message.reply_to_message.caption or "ویدئو بدون متن"
    videos_col.insert_one({"file_id": file_id, "caption": caption})
    bot.reply_to(message, "ویدئو اضافه شد ✅")
    bot.send_video(OWNER_ID, file_id, caption=caption, disable_notification=True)
    log_event(f"User {message.from_user.id} ویدئو اضافه کرد: {caption}")

# /remov
@bot.message_handler(commands=["remov", f"remov@{BOT_USERNAME}"])
def remove_video(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط مالک کل و ادمین اجازه حذف دارند")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ روی ویدئو ریپلای کن تا حذف شود")
        return

    file_id = get_video_file_id(message.reply_to_message)
    if not file_id:
        bot.reply_to(message, "❌ ویدئو پیدا نشد")
        return

    result = videos_col.delete_one({"file_id": file_id})
    if result.deleted_count:
        bot.reply_to(message, "ویدئو حذف شد ✅")
        log_event(f"User {message.from_user.id} ویدئو حذف کرد: {file_id}")
    else:
        bot.reply_to(message, "❌ این ویدئو در دیتابیس موجود نبود")
        log_event(f"User {message.from_user.id} تلاش کرد ویدئو حذف کند که موجود نبود: {file_id}")

# =======================
# Admin Management
@bot.message_handler(commands=["addadmin", f"addadmin@{BOT_USERNAME}"])
def add_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما اجازه اضافه کردن ادمین را ندارید")
        log_event(f"User {message.from_user.id} تلاش برای اضافه کردن ادمین بدون دسترسی")
        return
    try:
        uid = int(message.text.split()[1])
        if not admins_col.find_one({"user_id": uid}):
            admins_col.insert_one({"user_id": uid})
            bot.reply_to(message, "ادمین اضافه شد ✅")
            log_event(f"User {OWNER_ID} ادمین {uid} را اضافه کرد")
        else:
            bot.reply_to(message, "قبلاً ادمین بوده")
            log_event(f"User {OWNER_ID} تلاش کرد ادمین {uid} دوباره اضافه کند")
    except:
        bot.reply_to(message, "فرمت اشتباه")
        log_event(f"User {message.from_user.id} دستور addadmin فرمت اشتباه داد")

@bot.message_handler(commands=["removeadmin", f"removeadmin@{BOT_USERNAME}"])
def remove_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما دستر رسی حذف ادمین را ندارید")
        log_event(f"User {message.from_user.id} تلاش برای حذف ادمین بدون دسترسی")
        return
    try:
        uid = int(message.text.split()[1])
        admins_col.delete_one({"user_id": uid})
        bot.reply_to(message, "ادمین حذف شد ❌")
        log_event(f"User {OWNER_ID} ادمین {uid} را حذف کرد")
    except:
        bot.reply_to(message, "دستور اشتباه است")
        log_event(f"User {message.from_user.id} دستور removeadmin اشتباه داد")

@bot.message_handler(commands=["admin_list", f"admin_list@{BOT_USERNAME}"])
def admin_list_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط مالک و ادمین‌ها اجازه دیدن لیست ادمین‌ها را دارند")
        return
    admins = list(admins_col.find())
    text_lines = []
    for adm in admins:
        uid = adm.get("user_id")
        try:
            user = bot.get_chat(uid)
            username = f"@{user.username}" if user.username else "None"
        except Exception:
            username = "None"
        text_lines.append(f"{uid} | {username}")
    try:
        owner_user = bot.get_chat(OWNER_ID)
        owner_username = f"@{owner_user.username}" if owner_user.username else "None"
    except Exception:
        owner_username = "None"
    text_lines.insert(0, f"{OWNER_ID} | {owner_username} (Owner)")
    bot.reply_to(message, "لیست ادمین‌ها:\n\n" + "\n".join(text_lines))

# =======================
# /send_request
@bot.message_handler(commands=["send_request", f"send_request@{BOT_USERNAME}"])
def send_request_cmd(message):
    uid = message.from_user.id
    if is_admin(uid):
        bot.reply_to(message, "❌ شما ادمین هستید، دستور مخصوص کاربران عادی است")
        return
    bot.reply_to(message, "✅ پیام بعدی شما برای مالک ارسال می‌شود")
    user_next_message[uid] = "send_request"

# /echo
@bot.message_handler(commands=["echo", f"echo@{BOT_USERNAME}"])
def echo_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.reply_to(message, "❌ فقط ادمین‌ها اجازه استفاده دارند")
        return
    bot.reply_to(message, "✅ پیام بعدی شما برای همه ارسال خواهد شد")
    user_next_message[uid] = "echo"

# =======================
# Capturing next message
@bot.message_handler(func=lambda m: m.from_user.id in user_next_message)
def handle_next_message(message):
    uid = message.from_user.id
    action = user_next_message.pop(uid, None)
    if action == "send_request":
        try:
            bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
            bot.reply_to(message, "پیام شما برای مالک ارسال شد ✅")
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در ارسال پیام: {e}")
    elif action == "echo":
        success, fail = 0, 0
        all_chats = set([u["user_id"] for u in admins_col.find()])
        all_chats.add(OWNER_ID)
        GROUP_IDS = [-1001234567890, -1009876543210]
        all_chats.update(GROUP_IDS)
        for cid in all_chats:
            try:
                ct = message.content_type
                if ct == "text":
                    bot.send_message(cid, message.text)
                elif ct == "photo":
                    bot.send_photo(cid, message.photo[-1].file_id, caption=message.caption)
                elif ct == "video":
                    bot.send_video(cid, message.video.file_id, caption=message.caption)
                elif ct == "document":
                    bot.send_document(cid, message.document.file_id, caption=message.caption)
                elif ct == "sticker":
                    bot.send_sticker(cid, message.sticker.file_id)
                elif ct == "voice":
                    bot.send_voice(cid, message.voice.file_id, caption=message.caption)
                elif ct == "animation":
                    bot.send_animation(cid, message.animation.file_id, caption=message.caption)
                elif ct == "video_note":
                    bot.send_video_note(cid, message.video_note.file_id)
                success += 1
            except:
                fail += 1
        bot.reply_to(message, f"✅ موفق: {success}\n❌ ناموفق: {fail}\n👥 کل کاربران/گروه‌ها: {len(all_chats)}")

# =======================
# Keep-alive
def keep_alive_loop():
    global keep_alive_running
    while keep_alive_running:
        try:
            requests.get("https://anime-1127-bot-1.onrender.com/")
            log_event("Keep-alive ping successful")
        except Exception as e:
            log_event(f"Keep-alive error: {e}")
        time.sleep(300)

@bot.message_handler(commands=["awake", f"awake@{BOT_USERNAME}"])
def awake_bot(message):
    global keep_alive_running
    if message.from_user.id != OWNER_ID: return
    if keep_alive_running:
        bot.reply_to(message, "ربات از قبل بیداره 👁")
        return
    keep_alive_running = True
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    bot.reply_to(message, "ربات بیدار نگه داشته می‌شود 🔥")

@bot.message_handler(commands=["sleep", f"sleep@{BOT_USERNAME}"])
def sleep_bot(message):
    global keep_alive_running
    if message.from_user.id != OWNER_ID: return
    keep_alive_running = False
    bot.reply_to(message, "حالت نگه‌دارنده خاموش شد 😴")

# =======================
# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    template = """
    <h2>Bot is alive ✅</h2>
    <h3>آخرین لاگ‌ها:</h3>
    <ul>
    {% for log in logs %}
        <li>{{ log }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(template, logs=logs)

@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# =======================
if __name__ == "__main__":
    URL = "https://anime-1127-bot-1.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
