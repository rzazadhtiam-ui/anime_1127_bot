import requests
import threading
import time
import os
import telebot
from telebot import types
from pymongo import MongoClient
from flask import Flask, request, render_template_string
from datetime import datetime
import random
import string

# =========================
# CONFIG
# =========================
CONFIRM_ACCOUNT = 8588914809
remove_all_sessions = {}  # state storage
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

# =========================
# FORCE JOIN SYSTEM - MongoDB Version
# =========================

force_join_col = db["force_join"]  # کلکسیون برای کانال‌ها/گروه‌های اجباری

# -------------------------
# بررسی عضویت کاربر
# -------------------------
def check_user_joined(user_id):
    force_channels = list(force_join_col.find())
    for fc in force_channels:
        chat_id = fc.get("chat_id")
        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True

# -------------------------
# ارسال پیام عضویت اجباری
# -------------------------
def send_force_join(message):
    force_channels = list(force_join_col.find())
    markup = types.InlineKeyboardMarkup()
    for fc in force_channels:
        title = fc.get("title") or "کانال/گروه"
        username = fc.get("username")
        url = f"https://t.me/{username}" if username else "https://t.me/c/{str(fc.get('chat_id'))[4:]}"
        markup.add(types.InlineKeyboardButton(title, url=url))

    markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join"))
    bot.reply_to(message, "کاربر گرامی برای استفاده از ربات لطفا در کانال‌ها/گروه‌های زیر عضو شوید 👇", reply_markup=markup)

# -------------------------
# کنترل قبل از اجرای دستورات
# -------------------------
def force_join_required(message):
    if message.chat.type == "private":
        return True
    if not check_user_joined(message.from_user.id):
        send_force_join(message)
        return False
    return True

# -------------------------
# تایید عضویت (دکمه)
# -------------------------
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    if check_user_joined(user_id):
        bot.answer_callback_query(call.id, "عضویت تایید شد ✅")
        bot.edit_message_text("✅ عضویت شما تایید شد. حالا می‌توانید از ربات استفاده کنید.",
                              call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو همه کانال‌ها/گروه‌ها نشدی", show_alert=True)

# -------------------------
# /id - نمایش لیست کانال‌ها و گروه‌های اجباری
# -------------------------
@bot.message_handler(commands=["id", f"id@{BOT_USERNAME}"])
def show_force_join_ids(message):
    if not command_allowed(message):
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط ادمین‌ها می‌توانند لیست را ببینند")
        return
    rows = []
    for fc in force_join_col.find():
        chat_id = fc.get("chat_id")
        username = fc.get("username") or "None"
        title = fc.get("title") or "None"
        rows.append(f"{chat_id} | {username} | {title}")
    if not rows:
        bot.reply_to(message, "⚠️ هنوز کانال یا گروه اجباری اضافه نشده")
    else:
        bot.reply_to(message, "📌 کانال‌ها/گروه‌های اجباری:\n" + "\n".join(rows))

# -------------------------
# /add_force - اضافه کردن کانال/گروه اجباری
# -------------------------
@bot.message_handler(commands=["add_force", f"add_force@{BOT_USERNAME}"])
def add_force_join(message):
    if not command_allowed(message):
        return
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ فقط مالک می‌تواند کانال/گروه اضافه کند")
        return
    try:
        parts = message.text.split()
        chat_id = int(parts[1])
        username = parts[2] if len(parts) > 2 else None
        title = " ".join(parts[3:]) if len(parts) > 3 else "None"
        if force_join_col.find_one({"chat_id": chat_id}):
            bot.reply_to(message, "⚠️ این کانال/گروه قبلاً اضافه شده")
            return
        force_join_col.insert_one({"chat_id": chat_id, "username": username, "title": title})
        bot.reply_to(message, "✅ کانال/گروه اجباری اضافه شد")
    except Exception as e:
        bot.reply_to(message, f"❌ دستور اشتباه است\nفرمت: /add_force <chat_id> <username/None> <title>")

# -------------------------
# /remove_force - حذف کانال/گروه اجباری
# -------------------------
@bot.message_handler(commands=["remove_force", f"remove_force@{BOT_USERNAME}"])
def remove_force_join(message):
    if not command_allowed(message):
        return
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ فقط مالک می‌تواند کانال/گروه حذف کند")
        return
    try:
        chat_id = int(message.text.split()[1])
        result = force_join_col.delete_one({"chat_id": chat_id})
        if result.deleted_count:
            bot.reply_to(message, "✅ کانال/گروه حذف شد")
        else:
            bot.reply_to(message, "❌ این کانال/گروه در لیست نبود")
    except:
        bot.reply_to(message, "❌ دستور اشتباه است\nفرمت: /remove_force <chat_id>")

# ======================
# Collection
users_col = db["users"]

# تابع ثبت کاربر یا گروه
def register_user_or_group(message):
    chat = message.chat
    user = message.from_user

    if chat.type == "private":
        data = {
            "type": "user",
            "name": user.first_name or "None",
            "user_id": user.id,
            "user_name": user.username or "None"
        }
        if not users_col.find_one({"user_id": user.id}):
            users_col.insert_one(data)

    elif chat.type in ["group", "supergroup"]:
        data = {
            "type": "group",
            "group_id": chat.id,
            "group_title": chat.title or "None"
        }
        if not users_col.find_one({"group_id": chat.id}):
            users_col.insert_one(data)

# ======================
# /start
@bot.message_handler(commands=["start", f"start@{BOT_USERNAME}"])
def start_cmd(message):
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return

    # ذخیره کاربر یا گروه قبل از هر چیزی
    register_user_or_group(message)

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
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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
def get_video_data(message):
    try:
        # اگر ویدئو معمولی باشد
        if message.video:
            return (
                message.video.file_id,
                message.video.file_unique_id
            )

        # اگر ویدئو به صورت document ارسال شده باشد
        if message.document:
            if message.document.mime_type and message.document.mime_type.startswith("video/"):
                return (
                    message.document.file_id,
                    message.document.file_unique_id
                )
    except Exception as e:
        print("Video detect error:", e)

    return None, None


@bot.message_handler(commands=["add", f"add@{BOT_USERNAME}"])
def add_video_cmd(message):

    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    register_user_or_group(message)
    

    user_id = message.from_user.id

    # بررسی دسترسی ادمین
    if not is_admin(user_id):
        bot.reply_to(message, "❌ فقط ادمین‌ها اجازه اضافه کردن ویدئو دارند")
        log_event(f"User {user_id} تلاش add بدون دسترسی")
        return

    # بررسی ریپلای
    if not message.reply_to_message:
        bot.reply_to(message, "❌ روی ویدئو ریپلای کن")
        log_event(f"User {user_id} دستور add بدون ریپلای")
        return

    # دریافت اطلاعات ویدئو
    file_id, unique_id = get_video_data(message.reply_to_message)

    if not file_id:
        bot.reply_to(message, "❌ فایل ویدئو نیست")
        return

    # جلوگیری از ذخیره تکراری
    if videos_col.find_one({"unique_id": unique_id}):
        bot.reply_to(message, "⚠️ این ویدئو قبلاً ذخیره شده")
        log_event(f"Duplicate video blocked by {user_id}")
        return

    # گرفتن کپشن
    caption = message.reply_to_message.caption or "ویدئو بدون متن"

    # ذخیره در دیتابیس
    try:
        videos_col.insert_one({
            "file_id": file_id,
            "unique_id": unique_id,
            "caption": caption,
            "added_by": user_id,
            "added_time": datetime.now()
        })

        bot.reply_to(message, "✅ ویدئو با موفقیت اضافه شد")

        # ارسال برای مالک جهت بکاپ
        try:
            bot.send_video(
                OWNER_ID,
                file_id,
                caption=f"📥 ویدئو جدید اضافه شد:\n\n{caption}",
                disable_notification=True
            )
        except:
            pass

        log_event(f"Video added by {user_id}: {caption}")

    except Exception as e:
        bot.reply_to(message, "❌ خطا در ذخیره ویدئو")
        log_event(f"Add video DB error: {e}")
# /remov
@bot.message_handler(commands=["remov", f"remov@{BOT_USERNAME}"])
def remove_video(message):
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ فقط مالک کل و ادمین اجازه حذف دارند")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ روی ویدئو ریپلای کن تا حذف شود")
        return
    register_user_or_group(message)

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


        
        


# ================================
# OTP RECEIVE
@bot.message_handler(func=lambda m:
    m.from_user.id in remove_all_sessions and
    remove_all_sessions[m.from_user.id].get("step") == 3
)
def remove_all_receive_otp(message):

    uid = message.from_user.id
    session = remove_all_sessions.get(uid)

    if not message.text or not message.text.isdigit():
        return

    # expire check
    if time.time() - session["time"] > REMOVE_OTP_EXPIRE:
        remove_all_sessions.pop(uid, None)
        bot.reply_to(message, "OTP expired")
        return

    # wrong otp
    if message.text.strip() != session["otp"]:
        bot.reply_to(message, "Wrong OTP")
        return

    # delete videos
    count = videos_col.count_documents({})
    videos_col.delete_many({})

    remove_all_sessions.pop(uid, None)

    bot.reply_to(message, f"All videos deleted\nCount: {count}")

    log_event(f"OWNER removed ALL videos -> {count}")


# =======================
# Admin Management
@bot.message_handler(commands=["add_admin", f"add_admin@{BOT_USERNAME}"])
def add_admin(message):
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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

@bot.message_handler(commands=["remove_admin", f"remove_admin@{BOT_USERNAME}"])
def remove_admin(message):
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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
    if not force_join_required(message):
        return
    register_user_or_group(message)
    
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
# ======================
# /echo with timeout
# ======================
@bot.message_handler(commands=["echo", f"echo@{BOT_USERNAME}"])
def echo_cmd(message):
    if not command_allowed(message):
        return
    if not force_join_required(message):
        return
    register_user_or_group(message)

    uid = message.from_user.id

    # فقط پیوی
    if message.chat.type != "private":
        bot.reply_to(message, "❌ این دستور فقط در پیوی ربات قابل استفاده است")
        return

    # فقط ادمین‌ها
    if not is_admin(uid):
        bot.reply_to(message, "❌ فقط ادمین‌ها اجازه استفاده دارند")
        return

    # تنظیم دستور در حافظه با timestamp
    user_next_message[uid] = {"action": "echo", "time": time.time()}

    bot.reply_to(message, "✅ پیام بعدی شما برای همه ارسال خواهد شد.\n⏳ زمان تایمر: 1 دقیقه")

    # Thread برای منقضی شدن دستور بعد از 60 ثانیه
    def expire_echo():
        time.sleep(60)
        if uid in user_next_message and user_next_message[uid].get("action") == "echo":
            user_next_message.pop(uid, None)
            try:
                bot.send_message(uid, "⏰ زمان استفاده از دستور /echo منقضی شد. لطفا دوباره دستور را ارسال کنید.")
            except:
                pass

    threading.Thread(target=expire_echo, daemon=True).start()

# =======================
# Handler واحد برای پیام بعدی
@bot.message_handler(
    func=lambda m: m.from_user.id in user_next_message,
    content_types=[
        "text",
        "photo",
        "video",
        "document",
        "animation",
        "voice",
        "video_note",
        "sticker"
    ]
)
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

        # جمع‌آوری کاربران و گروه‌ها
        for item in users_col.find():
            if item.get("type") == "user":
                all_chats.add(item["user_id"])
            elif item.get("type") == "group":
                all_chats.add(item["group_id"])

        # اضافه کردن مالک
        all_chats.add(OWNER_ID)

        # تابع ارسال محتوا
def send_content(cid, message):
    try:
        bot.copy_message(
            chat_id=cid,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        return True

    except Exception as e:
        print(f"Echo send error to {cid}: {e}")
        return False

        # ارسال به همه
        for cid in all_chats:
            if send_content(cid, message):
                success += 1
            else:
                fail += 1
                users_col.delete_one({"$or": [{"user_id": cid}, {"group_id": cid}]})

            time.sleep(0.05)

        bot.reply_to(
            message,
            f"📊 آمار ارسال:\n✅ موفق: {success}\n❌ ناموفق: {fail}\n👥 کل مقصدها: {len(all_chats)}"
        )
    

@bot.message_handler(content_types=["video", "document"])
def auto_save_videos(message):
    try:
        # ---------- شرط 1 : کاربران مجاز ----------
        allowed_user = message.from_user and message.from_user.id in ALLOWED_USERS

        # ---------- شرط 2 : ارسال از کانال داخل گروه ----------
        channel_forward = (
            message.forward_from_chat
            and message.forward_from_chat.username == CHANNEL_USERNAME
        )

        if not allowed_user and not channel_forward:
            return

        # دریافت file_id و unique_id
        file_id, unique_id = get_video_data(message)
        if not file_id:
            return

        # جلوگیری از ذخیره تکراری
        if videos_col.find_one({"unique_id": unique_id}):
            return

        caption = message.caption or "Auto Saved Video"

        videos_col.insert_one({
            "file_id": file_id,
            "unique_id": unique_id,
            "caption": caption,
            "auto_saved": True,
            "time": datetime.utcnow()
        })

        log_event(f"Auto Saved Video: {caption}")

    except Exception as e:
        import traceback
        print("Auto Save Error:", e)
        traceback.print_exc()
# =======================
# Keep-alive (Professional Version)

KEEP_ALIVE_URLS = [
    "https://anime-1128-bot.onrender.com"
    "https://self-nix-bot.onrender.com"
    "https://self-nix-app.onrender.com"
    "https://self-bot-tv3l.onrender.com"
    "https://anime-1127-bot-x0nn.onrender.com"
] 

KEEP_ALIVE_INTERVAL = 150  # هر چند ثانیه پینگ شود (۵ دقیقه)

def ping_site(url):
    try:
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            log_event(f"Keep-alive SUCCESS -> {url}")
        else:
            log_event(f"Keep-alive WARNING -> {url} | Status: {res.status_code}")

    except Exception as e:
        log_event(f"Keep-alive ERROR -> {url} | {e}")


def keep_alive_loop():
    global keep_alive_running

    while keep_alive_running:

        for url in KEEP_ALIVE_URLS:
            ping_site(url)

        time.sleep(KEEP_ALIVE_INTERVAL)


@bot.message_handler(commands=["awake", f"awake@{BOT_USERNAME}"])
def awake_bot(message):
    if not command_allowed(message):
        return

    global keep_alive_running

    if not is_admin(user_id):
        return

    if keep_alive_running:
        bot.reply_to(message, "ربات قبلاً در حالت بیدار نگه داشتن است 👁")
        return

    keep_alive_running = True

    threading.Thread(
        target=keep_alive_loop,
        daemon=True
    ).start()

    bot.reply_to(message, "سیستم Keep-Alive فعال شد 🔥")


@bot.message_handler(commands=["sleep", f"sleep@{BOT_USERNAME}"])
def sleep_bot(message):
    if not command_allowed(message):
        return

    global keep_alive_running

    if not is_admin(user_id):
        return

    keep_alive_running = False

    bot.reply_to(message, "سیستم Keep-Alive خاموش شد 😴")



# =======================
# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    template = """
    <h2>Bot is alive ✅, tiam</h2>
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
    URL = "https://anime-1128-bot.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
