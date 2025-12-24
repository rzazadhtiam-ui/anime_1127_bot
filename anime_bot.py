import telebot
from telebot import types
import json
import os
import time
from hashlib import md5

# =======================
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
bot = telebot.TeleBot(TOKEN)

OWNER_ID = 6433381392
ADMINS_FILE = "admins.json"
FILE_PATH = "channel_videos.json"
CHANNEL_ID = "@asta_tiam_cannel"  # شناسه چنل جایگزین کن

admins = []
channel_videos = []

if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        admins = json.load(f)

if os.path.exists(FILE_PATH):
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        channel_videos = json.load(f)

# =======================
def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def save_videos():
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(channel_videos, f, ensure_ascii=False, indent=2)

# =======================
pending_videos = {}  # ویدئوهایی که در انتظار تایید هستند

# =======================
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    file_id = None
    title = message.caption or "ویدئو بدون عنوان"
    user_id = message.from_user.id
    user_mention = f"[{message.from_user.first_name}](tg://user?id={user_id})"

    if message.video:
        file_id = message.video.file_id
    elif message.document and message.document.mime_type.startswith("video/"):
        file_id = message.document.file_id

    if not file_id:
        return

    # اگر فرستنده مالک ربات هست → مستقیم ذخیره
    if user_id == OWNER_ID:
        save_and_send(file_id, title)
        bot.reply_to(message, f"ویدئو ذخیره شد ✅\n🎬 {title}")
        return

    # اگر فرستنده مدیر یا غیره هست → باید تایید شود
    pending_id = md5(file_id.encode()).hexdigest()[:10]
    pending_videos[pending_id] = {"file_id": file_id, "title": title, "from_id": user_id}

    # دکمه تایید/رد برای مالک
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve:{pending_id}"))
    markup.add(types.InlineKeyboardButton("❌ رد", callback_data=f"reject:{pending_id}"))

    bot.send_message(
        OWNER_ID,
        f"{user_mention} یک ویدئو ارسال کرده:\n🎬 {title}",
        parse_mode="Markdown",
        reply_markup=markup
    )

    # اطلاع به فرستنده
    bot.reply_to(message, "ویدئو شما در انتظار تایید مالک است ⏳")

# =======================
def save_and_send(file_id, title):
    # ذخیره در لیست ربات
    channel_videos.append({"file_id": file_id, "title": title})
    save_videos()

    # ارسال به چنل
    try:
        bot.send_video(CHANNEL_ID, file_id, caption=title)
    except:
        pass

# =======================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve:", "reject:")))
def handle_approval(call):
    action, pending_id = call.data.split(":")
    video_info = pending_videos.get(pending_id)

    if not video_info:
        bot.answer_callback_query(call.id, "ویدئو پیدا نشد ❌", show_alert=True)
        return

    from_id = video_info["from_id"]
    file_id = video_info["file_id"]
    title = video_info["title"]

    if action == "approve":
        save_and_send(file_id, title)
        bot.send_message(from_id, f"ویدئو شما تایید و ذخیره شد ✅\n🎬 {title}")
        bot.answer_callback_query(call.id, f"ویدئو تایید شد ✅", show_alert=True)
    else:
        bot.send_message(from_id, f"ویدئو شما رد شد ❌\n🎬 {title}")
        bot.answer_callback_query(call.id, f"ویدئو رد شد ❌", show_alert=True)

    # حذف از pending
    del pending_videos[pending_id]

# =======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "ربات آماده است 🤖\nویدئو را در پی‌وی ارسال کنید.")

# =======================
@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, "سلام به ربات anime1127 Bot خوش اومدی\n توی این ربات ویدیو و اهنگ قراره گذاشته بشه\n\n برای دیدن ویدیو \n@anime_1127_bot\n رو بنویس \n\n برای دیدن اهنک ها \n@anime_1127_bot music\n رو بنویس")
# =======================
@bot.message_handler(commands=["addadmin", "deladmin"])
def manage_admins(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "شما مالک نیستید ❌")
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "فرمت صحیح: /addadmin id یا /deladmin id")
        return

    try:
        target = int(parts[1])
    except:
        bot.reply_to(message, "ایدی نامعتبر ❌")
        return

    if message.text.startswith("/addadmin"):
        if target not in admins:
            admins.append(target)
            save_admins()
            bot.send_message(
                message.chat.id,
                f"کاربر [{target}](tg://user?id={target}) ادمین شد ✅",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "قبلاً ادمین بوده")
    else:
        if target in admins:
            admins.remove(target)
            save_admins()
            bot.send_message(
                message.chat.id,
                f"کاربر [{target}](tg://user?id={target}) حذف شد ❌",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "ادمین نیست")

# =======================
bot.infinity_polling()
