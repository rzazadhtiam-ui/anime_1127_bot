
import telebot
from telebot import types
from flask import Flask, request, render_template_string
import threading
import time
from datetime import datetime

# =======================
TOKEN = "7672699726:AAG_bVsO65AR-yVmSRDJuhIm_TJUbjKYWw4"
bot = telebot.TeleBot(TOKEN, threaded=False)

OWNER_ID = 6433381392
ALLOWED_USERS = [6433381392, 7851824627]
CHANNEL_USERNAME = "anime_1127"
keep_alive_running = False

# =======================
logs = []

def log_event(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {text}")
    if len(logs) > 100:
        logs.pop(0)

# =======================
# حافظه داخلی انیمه‌ها و ویدئوها
# ساختار:
# anime_data = {
#   "anime_name": {
#       "season_number": {
#           "part_number": file_id
#       }
#   }
# }
anime_data = {}

# =======================
def is_admin(user_id):
    return user_id == OWNER_ID  # فعلا فقط مالک ادمینه

# =======================
# /start
@bot.message_handler(commands=["start"])
def start_cmd(message):
    text = (
        "👋 سلام! خوش اومدی به ربات anime_Bot!\n"
        "🎬 برای دیدن راهنما دستور /help رو بزن"
    )
    bot.reply_to(message, text)

# /help
@bot.message_handler(commands=["help"])
def help_cmd(message):
    text = (
        "راهنما:\n"
        "🎬 دیدن ادیت‌های فیلم، بازی و انیمه.\n"
        "/anime -> نمایش پنل انیمه‌ها\n"
        "ارسال ویدئو -> فقط کاربران مجاز"
    )
    bot.reply_to(message, text)

# =======================
# دریافت ویدئو و ذخیره file_id
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    user_id = message.from_user.id
    is_allowed_user = user_id in ALLOWED_USERS and message.chat.type == "private"
    is_from_channel = getattr(message.forward_from_chat, "username", None) == CHANNEL_USERNAME if message.forward_from_chat else False

    if not (is_allowed_user or is_from_channel):
        return

    file_id = getattr(message.video, "file_id", None)
    if not file_id and message.document and message.document.mime_type.startswith("video/"):
        file_id = message.document.file_id

    if not file_id:
        return

    caption = message.caption or "ویدئو بدون متن"
    # به صورت موقت، فقط یک انیمه پیش‌فرض ذخیره می‌کنیم
    anime_name = "Anime_Default"
    season = 1
    part_number = len(anime_data.get(anime_name, {}).get(season, {})) + 1
    anime_data.setdefault(anime_name, {}).setdefault(season, {})[part_number] = file_id

    bot.send_video(OWNER_ID, file_id, caption=caption, disable_notification=True)
    log_event(f"User {user_id} ارسال ویدئو: {caption}")

# =======================
# پنل انیمه با دکمه‌ها و صفحه‌بندی
PAGE_SIZE = 10  # 5 چپ 5 راست

def build_anime_panel(page=0):
    anime_names = list(anime_data.keys())
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_page = anime_names[start:end]

    keyboard = []
    left = []
    right = []

    for idx, name in enumerate(current_page):
        button = types.InlineKeyboardButton(name, callback_data=f"anime_{name}")
        if idx % 2 == 0:
            left.append(button)
        else:
            right.append(button)

    # هر ردیف ترکیب left و right
    for l, r in zip(left, right):
        keyboard.append([l, r])
    # اگر تعداد ناهماهنگ بود اضافه می‌کنیم
    if len(left) > len(right):
        keyboard.append([left[-1]])
    elif len(right) > len(left):
        keyboard.append([right[-1]])

    # دکمه‌های بعدی و قبلی
    nav_buttons = []
    if start > 0:
        nav_buttons.append(types.InlineKeyboardButton("⏮ قبلی", callback_data=f"page_{page-1}"))
    if end < len(anime_names):
        nav_buttons.append(types.InlineKeyboardButton("⏭ بعدی", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return types.InlineKeyboardMarkup(keyboard)

# =======================
# دستور /anime
@bot.message_handler(commands=["anime"])
def anime_cmd(message):
    markup = build_anime_panel(page=0)
    bot.send_message(message.chat.id, "🎬 انیمه‌ها:", reply_markup=markup)

# =======================
# callback handler برای انیمه‌ها، فصل‌ها و قسمت‌ها
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        markup = build_anime_panel(page=page)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    if data.startswith("anime_"):
        anime_name = data.split("_", 1)[1]
        # ساخت دکمه فصل‌ها
        seasons = list(anime_data.get(anime_name, {}).keys())
        keyboard = []
        for season in seasons:
            btn = types.InlineKeyboardButton(f"فصل {season}", callback_data=f"season_{anime_name}_{season}")
            keyboard.append([btn])
        keyboard.append([types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_anime_0")])
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(f"🎬 {anime_name} - فصل‌ها:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    if data.startswith("season_"):
        _, anime_name, season_num = data.split("_")
        season_num = int(season_num)
        parts = anime_data.get(anime_name, {}).get(season_num, {})
        keyboard = []
        for part_num, file_id in parts.items():
            btn = types.InlineKeyboardButton(f"قسمت {part_num}", callback_data=f"part_{anime_name}_{season_num}_{part_num}")
            keyboard.append([btn])
        keyboard.append([types.InlineKeyboardButton("🔙 بازگشت", callback_data=f"anime_{anime_name}")])
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(f"🎬 {anime_name} - فصل {season_num} - قسمت‌ها:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    if data.startswith("part_"):
        _, anime_name, season_num, part_num = data.split("_")
        season_num = int(season_num)
        part_num = int(part_num)
        file_id = anime_data.get(anime_name, {}).get(season_num, {}).get(part_num)
        if file_id:
            bot.send_video(call.message.chat.id, file_id, caption=f"{anime_name} - فصل {season_num} - قسمت {part_num}")
        return

    if data.startswith("back_to_anime_"):
        page = int(data.split("_")[-1])
        markup = build_anime_panel(page=page)
        bot.edit_message_text("🎬 انیمه‌ها:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

# =======================
# Keep-alive ساده
def keep_alive_loop():
    global keep_alive_running
    while keep_alive_running:
        print("Keep-alive ping")
        time.sleep(300)

@bot.message_handler(commands=["awake"])
def awake_bot(message):
    global keep_alive_running
    if message.from_user.id != OWNER_ID:
        return
    if keep_alive_running:
        bot.reply_to(message, "ربات از قبل بیداره 👁")
        return
    keep_alive_running = True
    threading.Thread(target=keep_alive_loop, daemon=True).start()
    bot.reply_to(message, "ربات بیدار نگه داشته می‌شود 🔥")

@bot.message_handler(commands=["sleep"])
def sleep_bot(message):
    global keep_alive_running
    if message.from_user.id != OWNER_ID:
        return
    keep_alive_running = False
    bot.reply_to(message, "حالت نگه‌دارنده خاموش شد 😴")

# =======================
# Flask app برای لاگ
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




print("running")
# =======================
if __name__ == "__main__":
    URL = "https://anime-1127-bot-1.onrender.com/webhook"
    bot.remove_webhook()
    bot.set_webhook(URL)
    app.run(host="0.0.0.0", port=8080)
