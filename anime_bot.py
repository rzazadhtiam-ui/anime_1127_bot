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

# ============================
# Force commands with bot username in groups
# ============================
def command_allowed(message):

    # در پیوی همیشه اجازه بده
    if message.chat.type == "private":
        return True

    # اگر متن نبود اجازه بده
    if not message.text:
        return True

    # اگر دستور نبود اجازه بده
    if not message.text.startswith("/"):
        return True

    # اگر دستور بود ولی یوزرنیم نداشت → بلاک
    if f"@{BOT_USERNAME}" not in message.text:
        return False

    return True
# ======================
#/start
users_col = db["users"]

@bot.message_handler(commands=["start", f"start@{BOT_USERNAME}"])
def start_cmd(message):
    if not command_allowed(message):
        return
    

    chat = message.chat
    user = message.from_user

    # ======================
    # اگر پیوی باشد
    # ======================
    if chat.type == "private":

        data = {
            "type": "user",
            "name": user.first_name or "None",
            "user_id": user.id,
            "user_name": user.username or "None"
        }

        if not users_col.find_one({"user_id": user.id}):
            users_col.insert_one(data)

    # ======================
    # اگر گروه یا سوپرگروه باشد
    # ======================
    elif chat.type in ["group", "supergroup"]:

        data = {
            "type": "group",
            "group_id": chat.id,
            "group_title": chat.title or "None"
        }

        if not users_col.find_one({"group_id": chat.id}):
            users_col.insert_one(data)

    # ======================
    # پیام استارت
    # ======================
    text = (
        "👋 سلام، خوش اومدی به ربات anime_Bot!\n\n"
        "🎬 این ربات مخصوص دیدن ادیت‌های فیلم، بازی و انیمه‌ست.\n"
        "برای دیدن راهنما دستور /help رو بزن"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "پنل ربات",
            switch_inline_query_current_chat=""
        )
    )

    bot.reply_to(message, text, reply_markup=markup)

# /help
@bot.message_handler(commands=["help", f"help@{BOT_USERNAME}"])
def help_cmd(message):
    if not command_allowed(message):
        return
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
    markup.add(types.InlineKeyboardButton("پنل جستجو", switch_inline_query_current_chat=""))
    bot.reply_to(message, "برای جستجو روی دکمه زیر بزن:", reply_markup=markup)

# =======================
#inline handler 
@bot.inline_handler(func=lambda q: True)
def inline_handler(inline_query):

    query_text = inline_query.query.strip().lower()
    offset = int(inline_query.offset or 0)

    LIMIT = 50   # محدودیت تلگرام (قابل تغییر نیست)

    results = []
    added_ids = set()

    try:

        # ======================
        # ساخت query
        # ======================
        if query_text == "":
            cursor = videos_col.find().sort("_id", 1)
        else:
            cursor = videos_col.find({
                "caption": {
                    "$regex": query_text,
                    "$options": "i"
                }
            }).sort("_id", 1)

        # ======================
        # اعمال pagination
        # ======================
        cursor = cursor.skip(offset)

        count = 0
        index = offset

        for video in cursor:

            file_id = video.get("file_id")
            if not file_id or file_id in added_ids:
                continue

            added_ids.add(file_id)

            caption = video.get("caption", "")

            results.append(
                types.InlineQueryResultCachedVideo(
                    id=f"video_{index}",
                    video_file_id=file_id,
                    title=caption.replace("\n", " ")[:50] or "Video",
                    description=caption.replace("\n", " ")[:100],
                    caption=caption[:1024]
                )
            )

            count += 1
            index += 1

            if count >= LIMIT:
                break

        # ======================
        # offset بعدی
        # ======================
        next_offset = str(offset + count) if count == LIMIT else ""

        bot.answer_inline_query(
            inline_query.id,
            results,
            cache_time=0,
            is_personal=True,
            next_offset=next_offset
        )

    except Exception as e:
        print("Inline error:", e)
        bot.answer_inline_query(inline_query.id, [], cache_time=0)
# =======================
# /add
@bot.message_handler(commands=["add", f"add@{BOT_USERNAME}"])
def add_video_cmd(message):
    if not command_allowed(message):
        return
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
    if not command_allowed(message):
        return
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
    if not command_allowed(message):
        return
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
    if not command_allowed(message):
        return
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
    if not command_allowed(message):
        return
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
# /send_request فقط پیوی
@bot.message_handler(commands=["send_request", f"send_request@{BOT_USERNAME}"])
def send_request_cmd(message):
    if not command_allowed(message):
        return
    uid = message.from_user.id

    if message.chat.type != "private":
        bot.reply_to(message, "❌ این دستور فقط در پیوی ربات قابل استفاده است")
        return

    if is_admin(uid):
        bot.reply_to(message, "❌ شما ادمین هستید، این دستور مخصوص کاربران عادی است")
        return

    if uid in user_next_message:
        bot.reply_to(message, "⚠️ شما قبلاً درخواست ارسال پیام داده‌اید، لطفاً پیام خود را بفرستید")
        return

    bot.reply_to(
        message,
        "✅ پیام بعدی که ارسال کنید برای مالک فوروارد می‌شود.\n📩 متن، عکس، ویدئو یا فایل می‌توانید ارسال کنید."
    )
    user_next_message[uid] = {"action": "send_request", "time": time.time()}


# /echo فقط پیوی
@bot.message_handler(commands=["echo", f"echo@{BOT_USERNAME}"])
def echo_cmd(message):
    if not command_allowed(message):
        return
    uid = message.from_user.id

    if message.chat.type != "private":
        bot.reply_to(message, "❌ این دستور فقط در پیوی ربات قابل استفاده است")
        return

    if not is_admin(uid):
        bot.reply_to(message, "❌ فقط ادمین‌ها اجازه استفاده دارند")
        return

    bot.reply_to(message, "✅ پیام بعدی شما برای همه ارسال خواهد شد")
    user_next_message[uid] = {"action": "echo", "time": time.time()}


# =======================
# Handler واحد برای پیام بعدی
@bot.message_handler(func=lambda m: m.from_user.id in user_next_message)
def handle_next_message(message):
    uid = message.from_user.id
    data = user_next_message.pop(uid, None)
    if not data:
        return

    # send_request
    if data["action"] == "send_request":
        try:
            user = message.from_user
            name = user.first_name or "None"
            username = f"@{user.username}" if user.username else "None"
            user_id = user.id
            send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            header = (
                "📩 درخواست جدید\n\n"
                f"👤 نام: {name}\n"
                f"🆔 آیدی عددی: {user_id}\n"
                f"🔗 یوزرنیم: {username}\n"
                f"⏰ زمان ارسال: {send_time}\n\n"
                "━━━━━━━━━━━━━━\n\n"
            )

            ct = message.content_type

            if ct == "text":
                bot.send_message(OWNER_ID, header + message.text)
            elif ct == "photo":
                bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=header + (message.caption or ""))
            elif ct == "video":
                bot.send_video(OWNER_ID, message.video.file_id, caption=header + (message.caption or ""))
            elif ct == "document":
                bot.send_document(OWNER_ID, message.document.file_id, caption=header + (message.caption or ""))
            elif ct == "voice":
                bot.send_voice(OWNER_ID, message.voice.file_id, caption=header)
            elif ct == "animation":
                bot.send_animation(OWNER_ID, message.animation.file_id, caption=header + (message.caption or ""))
            elif ct == "sticker":
                bot.send_message(OWNER_ID, header)
                bot.send_sticker(OWNER_ID, message.sticker.file_id)
            elif ct == "video_note":
                bot.send_message(OWNER_ID, header)
                bot.send_video_note(OWNER_ID, message.video_note.file_id)

            bot.reply_to(message, "پیام شما برای مالک ارسال شد ✅")
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در ارسال پیام: {e}")

    # echo
    elif data["action"] == "echo":
        success = 0
        fail = 0
        all_chats = set()

        for item in users_col.find():
            if item.get("type") == "user":
                all_chats.add(item["user_id"])
            elif item.get("type") == "group":
                all_chats.add(item["group_id"])

        all_chats.add(OWNER_ID)

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
                    bot.send_voice(cid, message.voice.file_id)
                elif ct == "animation":
                    bot.send_animation(cid, message.animation.file_id, caption=message.caption)
                elif ct == "video_note":
                    bot.send_video_note(cid, message.video_note.file_id)
                success += 1
            except Exception:
                fail += 1
                users_col.delete_one({"$or": [{"user_id": cid}, {"group_id": cid}]})

        bot.reply_to(
            message,
            f"📊 آمار ارسال:\n✅ موفق: {success}\n❌ ناموفق: {fail}\n👥 کل مقصدها: {len(all_chats)}"
        )
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
    if not command_allowed(message):
        return
    global keep_alive_running
    if message.from_user.id != OWNER_ID: return
    if keep_alive_running:
        bot.reply_to(message, "ربات از قبل بیداره 👁")
        return
    keep_alive_running = True
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    bot.reply_to(message, "ربات بیدار نگه داشته میشه 🔥")

@bot.message_handler(commands=["sleep", f"sleep@{BOT_USERNAME}"])
def sleep_bot(message):
    if not command_allowed(message):
        return
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
