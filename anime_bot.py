# ==============================
# Telegram Media Archive Bot
# Owner-only approval system
# Inline Mode Enabled
# ==============================

import telebot
from telebot import types
from pymongo import MongoClient
from datetime import datetime
import pytz
import uuid

# ========= CONFIG =========
TOKEN = "8023002873:AAEpwA3fFr_YWR6cwre5WfotT_wFxBC4HMI"
OWNER_ID = 7851824627, 7851824627, 8277911482   # آیدی عددی خودت
CHANNEL_ID = @archiv_bot_t # چنل آرشیو

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= DATABASE =========
mongo = MongoClient("mongodb+srv://self_login:tiam_jinx@self.v2vzh9e.mongodb.net/anime_bot_db?retryWrites=true&w=majority")
db = mongo["media_bot"]

videos_col = db["videos"]
audios_col = db["audios"]
voices_col = db["voices"]
requests_col = db["requests"]

# ===========================
# UTILS
# ===========================

def is_owner(user_id):
    return user_id == OWNER_ID

def now_tehran():
    return datetime.now(pytz.timezone("Asia/Tehran"))

# ===========================
# REQUEST SYSTEM
# ===========================

def send_request_to_owner(message, media_type, file_id, caption):
    req_id = str(uuid.uuid4())

    requests_col.insert_one({
        "req_id": req_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "media_type": media_type,
        "file_id": file_id,
        "caption": caption
    })

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"approve:{req_id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject:{req_id}")
    )

    text = (
        f"📥 <b>درخواست جدید</b>\n\n"
        f"👤 کاربر: @{message.from_user.username or message.from_user.id}\n"
        f"📦 نوع: {media_type}\n\n"
        f"📝 کپشن:\n{caption or '—'}"
    )

    if media_type == "video":
        bot.send_video(OWNER_ID, file_id, caption=text, reply_markup=kb)
    elif media_type == "audio":
        bot.send_audio(OWNER_ID, file_id, caption=text, reply_markup=kb)
    elif media_type == "voice":
        bot.send_voice(OWNER_ID, file_id, caption=text, reply_markup=kb)

# ===========================
# MEDIA HANDLER
# ===========================

@bot.message_handler(content_types=["video", "audio", "voice"])
def handle_media(message):
    if is_owner(message.from_user.id):
        return

    caption = message.caption or ""

    if message.video:
        send_request_to_owner(
            message,
            "video",
            message.video.file_id,
            caption
        )

    elif message.audio:
        send_request_to_owner(
            message,
            "audio",
            message.audio.file_id,
            caption
        )

    elif message.voice:
        send_request_to_owner(
            message,
            "voice",
            message.voice.file_id,
            caption
        )

    bot.reply_to(
        message,
        "📨 درخواست شما ارسال شد.\nپس از بررسی، نتیجه اعلام می‌شود."
    )

# ===========================
# APPROVE / REJECT
# ===========================

@bot.callback_query_handler(func=lambda c: c.data.startswith(("approve", "reject")))
def callback_handler(call):
    if not is_owner(call.from_user.id):
        return

    action, req_id = call.data.split(":")
    req = requests_col.find_one({"req_id": req_id})

    if not req:
        bot.answer_callback_query(call.id, "درخواست پیدا نشد")
        return

    user_id = req["user_id"]
    media_type = req["media_type"]
    caption = req["caption"]
    file_id = req["file_id"]

    if action == "reject":
        bot.send_message(user_id, "❌ درخواست شما رد شد.")
        requests_col.delete_one({"req_id": req_id})
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        return

    # ===== APPROVE =====
    if media_type == "video":
        msg = bot.send_video(CHANNEL_ID, file_id, caption=caption)
        videos_col.insert_one({
            "file_id": msg.video.file_id,
            "caption": caption,
            "date": now_tehran()
        })

    elif media_type == "audio":
        msg = bot.send_audio(CHANNEL_ID, file_id, caption=caption)
        audios_col.insert_one({
            "file_id": msg.audio.file_id,
            "caption": caption,
            "title": msg.audio.title,
            "artist": msg.audio.performer,
            "date": now_tehran()
        })

    elif media_type == "voice":
        msg = bot.send_voice(CHANNEL_ID, file_id, caption=caption)
        voices_col.insert_one({
            "file_id": msg.voice.file_id,
            "caption": caption,
            "date": now_tehran()
        })

    bot.send_message(user_id, "✅ فایل شما تأیید و منتشر شد.")
    requests_col.delete_one({"req_id": req_id})
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ===========================
# INLINE MODE
# ===========================

@bot.inline_handler(lambda q: True)
def inline_handler(query):
    results = []
    text = query.query.lower()

    if "audio" in text:
        for i, a in enumerate(audios_col.find().limit(20)):
            results.append(
                types.InlineQueryResultCachedAudio(
                    id=str(i),
                    audio_file_id=a["file_id"],
                    title=a.get("title") or "Audio",
                    performer=a.get("artist") or "Unknown",
                    caption=a.get("caption", "")
                )
            )

    elif "voice" in text:
        for i, v in enumerate(voices_col.find().limit(20)):
            results.append(
                types.InlineQueryResultCachedVoice(
                    id=str(i),
                    voice_file_id=v["file_id"],
                    caption=v.get("caption", "")
                )
            )

    else:
        for i, v in enumerate(videos_col.find().limit(20)):
            results.append(
                types.InlineQueryResultCachedVideo(
                    id=str(i),
                    video_file_id=v["file_id"],
                    title="Video",
                    description=v.get("caption", ""),
                    caption=v.get("caption", ""),
                    supports_streaming=True
                )
            )

    bot.answer_inline_query(
        query.id,
        results,
        cache_time=0,
        is_personal=True
    )

# ===========================
# GLOBAL CLOCK (SLEEP PREVENT)
# ===========================

@bot.message_handler(commands=["clock"])
def ghost_clock(message):
    msg = bot.send_message(message.chat.id, "🌍")
    bot.delete_message(message.chat.id, msg.message_id)

# ===========================
# START
# ===========================

print("🤖 Bot is running...")
bot.infinity_polling(skip_pending=True)
