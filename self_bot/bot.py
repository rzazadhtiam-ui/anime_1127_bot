import telebot
from bson import ObjectId
from telebot import types
from datetime import datetime, timedelta, UTC
import threading
import requests
from pymongo import MongoClient
from update1 import PanelManager
from update1_2 import register_commands
from games import register_games
# ================= CONFIG =================

TOKEN = "8860876332:AAE2iCEK3X-YVrsjwT_3yvejRWYqu3x5bOc"
SITE_URL = 'https://anime-1127-bot-x0nn.onrender.com'
MIN_COINS = 10
REFERRAL_REWARD = 25
TRIAL_DURATION = 1  # روز
HOURLY_DEDUCT = 2  # تعداد سکه‌ای که هر ساعت کم می‌کنه
MIN_COINS_FOR_SESSION = 10 # حداقل سکه برای ادامه سشن
BOT_USERNAME = "tiam"
PRICE_PER_50 = 5000 
CARD_NUMBER = "6219861457618899"
CARD_NAME = "تیام رضازاده"
admin_messages = {} 
# ================= MongoDB =================
mongo_uri = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)
mongo = MongoClient(mongo_uri)
db = mongo.telegram_sessions
db1 = mongo.self_panel_db

users_col = db.users
sessions_col = db.sessions1
required_chats_col = db1.required_chats



# ================= Bot =================
bot = telebot.TeleBot(TOKEN)
panel_manager = PanelManager(bot)
register_commands(bot)
register_games(bot)
#==================data =================
user_state = {}
temp_data = {}
panel_text = (
    "✨ سلام و درود 🌹\n"
    "به ربات ⦁ Self Nix خوش اومدید 🙌🔥\n\n"
    "با این ربات می‌تونید امکانات اکانتتون رو بیشتر و خاص‌تر کنید 💎🚀"
)
ADMIN = [6433381392, 8588914809, 8277911482] 

ADMINS = [6433381392, 8471402457, 7851824627, 8259391739]

SUPER_ADMIN = 6433381392
# ================= Helper =================

def send_coin_log(text, parse_mode=None):
    try:
        bot.send_message(SUPER_ADMIN, f"📊 گزارش سکه:\n\n{text}", parse_mode=parse_mode)
    except Exception as e:
        print("Log Error:", e)

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

def safe_edit(call, text, markup=None):
    try:
        bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.from_user.id, text, reply_markup=markup)

def start_trial_expiration(uid):
    def remove_trial():
        users_col.update_one({"user_id": uid}, {"$set": {"trial_active": False}})
        try:
            bot.send_message(uid, "⚡ سلف تست یک روزه شما منقضی شد!")
        except:
            pass
    threading.Timer(TRIAL_DURATION * 86400, remove_trial).start()

def register_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {
            "$set": {
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username or "",
                "last_seen": datetime.now(UTC)
            },
            "$setOnInsert": {
                "coins": 0,
                "created_at": datetime.now(UTC),
                "trial_used": False,
                "ban": False,
                "wins": 0
            }
        },
        upsert=True
    )

def get_main_panel():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 فعال سازی سلف ✨️", callback_data="selfbot_start_self"))
    markup.add(types.InlineKeyboardButton("⚡️ سلف تست(یک روزه)⚡️", callback_data="selfbot_start_trial"))
    markup.row(
        types.InlineKeyboardButton("💼 حساب کاربری👤", callback_data="selfbot_account_info"),
        types.InlineKeyboardButton("🌟 زیر مجموعه گیری 🔗", callback_data="selfbot_referral")
    )
    markup.add(types.InlineKeyboardButton("🛍 خرید سکه 💰", callback_data="selfbot_buy_coins"))
    
    
    markup.add(
    types.InlineKeyboardButton(
        "🛠️ ارتباط با ما💬",
        callback_data="open_support_menu"
    )
)

       
    return markup

def get_back_panel():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="selfbot_main_panel"))
    return markup

def make_join_link(link):
    link = link.strip()

    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"

    if "t.me/" in link:
        return f"https://t.me/{link.split('t.me/')[1]}"

    return f"https://t.me/{link}"

def get_membership_panel(missing_chats):
    markup = types.InlineKeyboardMarkup()

    for chat in missing_chats:
        markup.add(types.InlineKeyboardButton(
            chat["button_name"],
            url=chat["link"]
        ))

    markup.add(types.InlineKeyboardButton(
        "✅ تایید عضویت",
        callback_data="check_membership"
    ))

    return markup
    
def resolve_chat(chat_link):
    try:
        chat_link = chat_link.strip()

        if "t.me/" in chat_link:
            username = chat_link.split("t.me/")[1]
            username = username.split("?")[0]
            return "@" + username

        if chat_link.startswith("@"):
            return chat_link

        return "@" + chat_link

    except:
        return None


def is_user_joined(user_id):
    chats = list(required_chats_col.find({}))

    missing = []

    for chat in chats:
        try:
            chat_id = resolve_chat(chat["link"])
            member = bot.get_chat_member(chat_id, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                missing.append(chat)

        except Exception as e:
            print("Membership check error:", e)
            missing.append(chat)

    return missing

import threading
import time


import threading
import time


def manage_user_coins(uid):
    """
    کاهش سکه هر ساعت و مدیریت خودکار سشن‌ها.
    """
    try:
        user = users_col.find_one({"user_id": uid})
        if not user:
            return

        # پیدا کردن سشن‌های فعال
        active_sessions = list(sessions_col.find({
            "user_id": uid,
            "power": "on"
        }))

        session_count = len(active_sessions)
        current_coins = user.get("coins", 0)

        # کاهش سکه فقط اگر سشن فعال وجود داشته باشد
        if session_count > 0:
            deduct_amount = HOURLY_DEDUCT * session_count
            new_coins = max(current_coins - deduct_amount, 0)

            # بروزرسانی سکه و ثبت زمان آخرین کاهش
            users_col.update_one(
                {"user_id": uid},
                {"$set": {"coins": new_coins, "last_coin_deduct": datetime.now(UTC)}}
            )

            print(f"[COIN ENGINE] User {uid} used {deduct_amount} coins | Active Sessions: {session_count} | Remaining: {new_coins}")

            # اگر سکه کم شد → خاموش کردن سشن‌ها
            if new_coins < MIN_COINS_FOR_SESSION:
                for session in active_sessions:
                    sessions_col.update_one(
                        {"_id": session["_id"]},
                        {"$set": {"power": "off", "disabled_reason": "low_coins", "disabled_at": datetime.now(UTC)}}
                    )

                if not user.get("low_coin_warned"):
                    users_col.update_one(
                        {"user_id": uid},
                        {"$set": {"low_coin_warned": True}}
                    )
                    try:
                        bot.send_message(
                            uid,
                            "⚠️ سکه‌های شما برای ادامه فعالیت سلف کافی نیست.\nتمام سشن‌ها خاموش شدند."
                        )
                    except Exception as e:
                        print(f"[COIN ENGINE MESSAGE ERROR] User {uid}: {e}")

            else:
                # اگر سکه شارژ شد و فلگ فعال بود → ریست فلگ
                if user.get("low_coin_warned"):
                    users_col.update_one(
                        {"user_id": uid},
                        {"$set": {"low_coin_warned": False}}
                    )

        # بررسی سشن‌های خاموش برای Auto Resume
        coins = users_col.find_one({"user_id": uid}).get("coins", 0)
        if coins >= MIN_COINS_FOR_SESSION:
            # پیدا کردن سشن‌هایی که Power=off و به دلیل کمبود سکه خاموش شده‌اند
            sessions_to_resume = list(sessions_col.find({
                "user_id": uid,
                "power": "off",
                "disabled_reason": "low_coins"
            }))
            if sessions_to_resume:
                for session in sessions_to_resume:
                    sessions_col.update_one(
                        {"_id": session["_id"]},
                        {"$set": {"power": "on"}, "$unset": {"disabled_reason": 1, "disabled_at": 1}}
                    )
                try:
                    bot.send_message(
                        uid,
                        "✅ سکه‌های شما شارژ شد!\nسشن‌هایی که به دلیل کمبود سکه خاموش شده بودند دوباره فعال شدند."
                    )
                except Exception as e:
                    print(f"[AUTO RESUME MESSAGE ERROR] User {uid}: {e}")

    except Exception as e:
        print("[COIN ENGINE ERROR]", e)


def get_user_sessions_panel(uid):
    markup = types.InlineKeyboardMarkup()
    sessions = list(sessions_col.find({"user_id": uid}))

    for s in sessions:
        name = s.get("session_name", "Unnamed")
        power = s.get("power", "off")

        status_text = "🟢 ON" if power == "on" else "🔴 OFF"

        markup.row(
            types.InlineKeyboardButton(
                f"📱 {name}",
                callback_data=f"session_info_{s['_id']}"
            ),
            types.InlineKeyboardButton(
                status_text,
                callback_data=f"toggle_session_{s['_id']}"
            )
        )

    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="selfbot_main_panel"))
    return markup



# ================= Handlers =================#

import threading
import time
import requests
from flask import Flask
import os

# ================= CONFIG =================
KEEP_ALIVE_URLS = [
    "https://anime-1128-bot.onrender.com",
    "https://self-nix-bot.onrender.com",
    "https://self-nix-app.onrender.com",
    "https://self-bot-tv3l.onrender.com"
]
KEEP_ALIVE_INTERVAL = 150  # ثانیه
keep_alive_running = False
keep_alive_thread = None
keep_alive_lock = threading.Lock()

# ================= LOGGER =================
def log_event(text):
    print(f"[KEEP-ALIVE] {text}")

# ================= PING FUNCTION =================
def ping_site(url):
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            log_event(f"SUCCESS -> {url}")
        else:
            log_event(f"WARNING -> {url} | Status: {res.status_code}")
    except Exception as e:
        log_event(f"ERROR -> {url} | {e}")

# ================= LOOP =================
def keep_alive_loop():
    log_event("Keep-Alive Loop started")
    while True:
        with keep_alive_lock:
            if not keep_alive_running:
                log_event("Keep-Alive Loop stopped")
                break

        for url in KEEP_ALIVE_URLS:
            ping_site(url)

        # Sleep امن (چک کردن stop هر ثانیه)
        for _ in range(KEEP_ALIVE_INTERVAL):
            with keep_alive_lock:
                if not keep_alive_running:
                    return
            time.sleep(1)

# ================= START / STOP =================
def start_keep_alive():
    global keep_alive_running, keep_alive_thread
    with keep_alive_lock:
        if keep_alive_running:
            return False
        keep_alive_running = True
        keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
        keep_alive_thread.start()
    return True

def stop_keep_alive():
    global keep_alive_running
    with keep_alive_lock:
        if not keep_alive_running:
            return False
        keep_alive_running = False
    return True

# ================= Flask =================
app = Flask(__name__)
@app.route("/")
def home():
    return "🤖 Bot is alive ✅"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================= TeleBot Handlers =================
@bot.message_handler(commands=["ping"])
def awake_bot(message):
    if not command_allowed(message):
        return
    if message.from_user.id not in ADMIN:
        print("paaaaa")
        return
    started = start_keep_alive()
    if started:
        bot.reply_to(message, "سیستم Keep-Alive فعال شد 🔥")
    else:
        bot.reply_to(message, "قبلاً فعال بوده 👁")

@bot.message_handler(commands=["sleep"])
def sleep_bot(message):
    if not command_allowed(message):
        return
    if message.from_user.id not in ADMIN:
        return
    stopped = stop_keep_alive()
    if stopped:
        bot.reply_to(message, "سیستم Keep-Alive خاموش شد 😴")
    else:
        bot.reply_to(message, "قبلاً خاموش بوده")

@bot.message_handler(commands=["start"])
def start_panel(message):
    if not command_allowed(message):
        return

    uid = message.from_user.id
    register_user(message.from_user)

    missing = is_user_joined(uid)

    if missing:
        bot.send_message(
            uid,
            "⚠️ برای استفاده از ربات باید در کانال‌ها و گروه‌های زیر عضو شوید:",
            reply_markup=get_membership_panel(missing)
        )
        return

    bot.send_message(
        uid,
        panel_text,
        reply_markup=get_main_panel()
    )

@bot.message_handler(commands=["admin_gift"])
def give_coins_admin(message):
    if not command_allowed(message):
        return
    if message.from_user.id not in ADMIN:
        bot.send_message(message.from_user.id, "❌ شما دسترسی لازم را ندارید!")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.from_user.id, "❌ فرمت دستور: /admin_gift <آیدی> <تعداد سکه>")
        return
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        bot.send_message(message.from_user.id, "❌ آیدی و تعداد سکه باید عدد باشند!")
        return

    users_col.update_one({"user_id": target_id}, {"$inc": {"coins": amount}}, upsert=True)
    recipient = users_col.find_one({"user_id": target_id})
    recipient_name = recipient.get("first_name", "کاربر ناشناس")

    bot.send_message(message.from_user.id, f"✅ {amount} سکه به  کاربر{recipient_name} اضافه شد.")
    try:
        bot.send_message(target_id, f"🌟 {amount} سکه توسط ادمین به حساب شما اضافه شد!")
        
        send_coin_log(
    f"🔄 انتقال سکه\n"
    f"👤 از: {from_id}\n"
    f"👤 به: {recipient_name}\n"
    f"💰 مقدار: {amount}"
)
    except:
        pass

@bot.message_handler(commands=["add_baton"])
def add_required_chat(message):
    if not command_allowed(message):
        return
    if message.from_user.id not in ADMIN:
        bot.send_message(message.from_user.id, "❌ دسترسی ندارید!")
        return

    args = message.text.split(maxsplit=2)
    if len(args) != 3:
        bot.send_message(message.from_user.id, "❌ فرمت درست: /add {link_channel_or_group} {button_name}")
        return

    link = args[1]
    button_name = args[2]

    required_chats_col.insert_one({"link": link, "button_name": button_name})
    bot.send_message(message.from_user.id, f"✅ دکمه '{button_name}' اضافه شد!")
    
@bot.callback_query_handler(func=lambda c: c.data.startswith("selfbot_"))
def handle_callbacks(call):
    uid = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)
    user = users_col.find_one({"user_id": uid}) or {}

    if data == "selfbot_main_panel":
        safe_edit(call, panel_text, get_main_panel())

    elif data == "selfbot_start_self":
        coins = user.get("coins", 0)
        required = MIN_COINS
        if coins < required:
            missing = required - coins

        # پیام هشدار موقت
            msg = bot.send_message(
            uid,
            f"⚠️ سکه‌های شما کافی نیست!\nمقدار مورد نیاز: {missing} سکه"
        )

        # حذف خودکار پیام بعد 3 ثانیه
            threading.Timer(3, lambda: bot.delete_message(uid, msg.message_id)).start()
            return
    # اگر سکه کافی بود ادامه بده
        safe_edit(call, "📱 شماره خود را وارد کنید (+98...)")
        user_state[uid] = "await_phone_self"

    elif data == "selfbot_start_trial":
        if user.get("trial_used"):
            bot.answer_callback_query(call.id, "⚡ شما قبلاً سلف تست گرفتید!")
            return
        safe_edit(call, "📱 شماره خود را وارد کنید (+98...)")
        user_state[uid] = "await_phone_trial"

    elif data == "selfbot_account_info":
        first_name = user.get("first_name", "")
        username = user.get("username", "-")
        coins = user.get("coins", 0)
        referrals = users_col.count_documents({"referrer": uid})
        created_at = user.get("created_at")
        created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "-"
        msg = f"""اطلاعات شما:
اسم: {first_name}
یوزرنیم: @{username}
ایدی عددی: {uid}
تعداد زیر مجموعه: {referrals}
تعداد سکه: {coins}
تاریخ عضویت: {created_str}"""
        safe_edit(call, msg, get_user_sessions_panel(uid))

    elif data == "selfbot_referral":
        referral_link = f"https://t.me/self_nix_bot?start={uid}"
        msg = f"🌟 لینک اختصاصی زیر مجموعه شما:\n{referral_link}\nهر زیر مجموعه: {REFERRAL_REWARD} سکه✨️"
        safe_edit(call, msg, get_back_panel())

    elif data == "selfbot_buy_coins":
        msg = "تعداد سکه مورد نظر خود را ارسال کنید.\nهر ۵۰ سکه = ۵,۰۰۰ تومان"
        safe_edit(call, msg, get_back_panel())
        user_state[uid] = "await_buy_amount"

@bot.callback_query_handler(func=lambda c: c.data == "check_membership")
def check_membership_callback(call):

    uid = call.from_user.id

    missing = is_user_joined(uid)

    # اگر هنوز عضو نیست
    if missing:

        safe_edit(
            call,
            "❌ کاربر گرامی شما هنوز در بعضی کانال‌ها یا گروه‌ها عضو نشده‌اید",
            get_membership_panel(missing)
        )
        return

    # ✅ اگر عضو بود
    try:
        bot.delete_message(uid, call.message.message_id)
    except:
        pass

    msg = bot.send_message(
        uid,
        "✅ کاربر گرامی عضویت شما تایید شد\n"
        "به ربات ⦁ Self Nix خوش اومدی 🌟"
    )

    # ارسال پنل اصلی
    bot.send_message(uid, panel_text, reply_markup=get_main_panel())

    # حذف پیام تایید بعد ۱۰ ثانیه
    def delete_confirm():
        try:
            bot.delete_message(uid, msg.message_id)
        except:
            pass

    threading.Timer(10, delete_confirm).start()     
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    uid = message.from_user.id
    text = message.text.strip()
    state = user_state.get(uid)

    # ---------------- خرید سکه ----------------
    # ---------------- خرید سکه ----------------
    if state == "await_buy_amount":
        if not text.isdigit():
            bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید.")
            return

        amount = int(text)

        if amount < 50:
            bot.send_message(uid, "❌ حداقل خرید 50 سکه است.")
            return

        total = int((amount / 50) * PRICE_PER_50)

        temp_data[uid] = {
        "buy_amount": amount,
        "buy_total": total
    }

        msg = (
        f"💰 تعداد سکه: {amount}\n"
        f"💵 مبلغ قابل پرداخت: {total:,} تومان\n\n"
        f"لطفاً مبلغ را به کارت زیر واریز کنید:\n\n"
        f"شماره کارت:\n{CARD_NUMBER}\n"
        f"به نام: {CARD_NAME}\n\n"
        f"پس از واریز، عکس فیش را ارسال کنید."
    )
    
        send_coin_log(
    f"🛒 درخواست خرید\n"
    f"👤 کاربر: {uid}\n"
    f"💰 تعداد: {amount}\n"
    f"💵 مبلغ: {total} تومان"
)

        bot.send_message(uid, msg)
        user_state[uid] = "await_receipt"
        return

    # ---------------- مرحله شماره ----------------
    if state in ["await_phone_self", "await_phone_trial"]:
        # پاک کردن پیام کاربر و پیام قبلی ربات
        try: bot.delete_message(uid, message.message_id)
        except: pass
        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try: bot.delete_message(uid, prev_msg_id)
            except: pass

        temp_data[uid] = {"phone": text}
        try:
            res = requests.post(
                f"{SITE_URL}/send_phone",
                json={"phone": text, "trial": state=="await_phone_trial"},
                timeout=15
            ).json()
        except Exception as e:
            msg = bot.send_message(uid, f"❌ خطا در ارسال شماره: {e}")
            temp_data[uid]["last_msg_id"] = msg.message_id
            return

        if res.get("status") == "ok":
            msg = bot.send_message(uid, "✅ شماره تایید شد. لطفاً کد OTP را با . وارد کنید\nمثال:1.2.3.4.5")
            temp_data[uid]["last_msg_id"] = msg.message_id
            user_state[uid] = "await_otp_self" if state == "await_phone_self" else "await_otp_trial"
        else:
            msg = bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
            temp_data[uid]["last_msg_id"] = msg.message_id
        return

    # ---------------- مرحله OTP ----------------
    if state in ["await_otp_self", "await_otp_trial"]:
        # پاک کردن پیام کاربر و پیام قبلی ربات
        try: bot.delete_message(uid, message.message_id)
        except: pass
        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try: bot.delete_message(uid, prev_msg_id)
            except: pass

        phone = temp_data.get(uid, {}).get("phone")
        if not phone:
            user_state.pop(uid, None)
            return

        trial = "trial" in state
        try:
            res = requests.post(
                f"{SITE_URL}/send_code",
                json={"phone": phone, "code": text, "trial": trial},
                timeout=15
            ).json()
        except Exception as e:
            msg = bot.send_message(uid, f"❌ خطا در ارسال کد OTP: {e}")
            temp_data[uid]["last_msg_id"] = msg.message_id
            return

        if res.get("status") == "ok":
            users_col.update_one({"user_id": uid}, {"$set": {
                "phone": phone,
                "trial_active": trial,
                "trial_used": trial or users_col.find_one({"user_id": uid}).get("trial_used", False),
                "trial_end": datetime.now(UTC) + timedelta(days=TRIAL_DURATION) if trial else None
            }})
            if trial:
                start_trial_expiration(uid)
            msg = bot.send_message(uid, f"✅ {'سلف تست' if trial else 'سلف اصلی'} ساخته شد و ورود کامل شد!")
            temp_data[uid]["last_msg_id"] = msg.message_id
            user_state.pop(uid, None)
            temp_data.pop(uid, None)
        elif res.get("status") == "2fa":
            msg = bot.send_message(uid, "🔐 نیاز به رمز دو مرحله‌ای (2FA). لطفاً وارد کنید:")
            temp_data[uid]["last_msg_id"] = msg.message_id
            user_state[uid] = "await_2fa_trial" if trial else "await_2fa_self"
        else:
            msg = bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
            temp_data[uid]["last_msg_id"] = msg.message_id

    # ---------------- مرحله 2FA ----------------
    if state in ["await_2fa_self", "await_2fa_trial"]:
        # پاک کردن پیام کاربر و پیام قبلی ربات
        try: bot.delete_message(uid, message.message_id)
        except: pass
        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try: bot.delete_message(uid, prev_msg_id)
            except: pass

        phone = temp_data.get(uid, {}).get("phone")
        if not phone:
            user_state.pop(uid, None)
            return

        trial = "trial" in state
        try:
            res = requests.post(
                f"{SITE_URL}/send_2fa",
                json={"phone": phone, "password": text, "trial": trial},
                timeout=15
            ).json()
        except Exception as e:
            msg = bot.send_message(uid, f"❌ خطا در ارسال 2FA: {e}")
            temp_data[uid]["last_msg_id"] = msg.message_id
            return

        if res.get("status") == "ok":
            users_col.update_one({"user_id": uid}, {"$set": {
                "phone": phone,
                "trial_active": trial,
                "trial_used": trial or users_col.find_one({"user_id": uid}).get("trial_used", False),
                "trial_end": datetime.now(UTC) + timedelta(days=TRIAL_DURATION) if trial else None
            }})
            if trial:
                start_trial_expiration(uid)
            msg = bot.send_message(uid, f"✅ {'سلف تست' if trial else 'سلف اصلی'} ساخته شد و ورود کامل شد!")
            temp_data[uid]["last_msg_id"] = msg.message_id
            user_state.pop(uid, None)
            temp_data.pop(uid, None)
        elif res.get("status") == "2fa":
            msg = bot.send_message(uid, "🔐 رمز دو مرحله‌ای اشتباه است، دوباره وارد کنید:")
            temp_data[uid]["last_msg_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_session_"))
def toggle_session(call):
    uid = call.from_user.id
    session_id = call.data.replace("toggle_session_", "")

    try:
        obj_id = ObjectId(session_id)
    except:
        bot.answer_callback_query(call.id, "❌ ID اشتباه")
        return

    session = sessions_col.find_one({"_id": obj_id})
    if not session:
        bot.answer_callback_query(call.id, "❌ سشن پیدا نشد")
        return

    # تغییر وضعیت
    new_power = "off" if session.get("power") == "on" else "on"

    sessions_col.update_one(
        {"_id": obj_id},
        {"$set": {"power": new_power}}
    )

    bot.answer_callback_query(call.id, f"Power → {new_power.upper()}")

    # 🔥 فقط آپدیت کیبورد (بدون تغییر متن)
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_user_sessions_panel(uid)
        )
    except Exception as e:
        print("EDIT MARKUP ERROR:", e)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_buy_"))
def confirm_buy(call):
    target_id = int(call.data.split("_")[2])

    # فقط کسانی که پیام براشون فرستاده شده اجازه تایید دارند
    allowed_admins = [admin_id for admin_id, _ in admin_messages.get(target_id, [])]

# اضافه کردن سوپر ادمین به لیست
    if SUPER_ADMIN not in allowed_admins:
        allowed_admins.append(SUPER_ADMIN)

    if call.from_user.id not in allowed_admins:
        bot.answer_callback_query(call.id, "❌ اجازه ندارید این خرید را تایید کنید")
        return

    amount = temp_data[target_id]["buy_amount"]
    users_col.update_one({"user_id": target_id}, {"$inc": {"coins": amount}})

    # حذف دکمه‌ها
    for admin_id, msg_id in admin_messages.get(target_id, []):
        try:
            bot.edit_message_reply_markup(chat_id=admin_id, message_id=msg_id, reply_markup=None)
        except:
            pass

    bot.send_message(target_id, f"✅ خرید شما تایید شد.\n💰 {amount} سکه اضافه شد.")

    # لاگ به سوپرادمین
    send_coin_log(
        f"✅ خرید تایید شد\n"
        f"👤 ادمین: <a href='tg://user?id={call.from_user.id}'>{call.from_user.first_name}</a>\n"
        f"👤 کاربر: <a href='tg://user?id={target_id}'>{users_col.find_one({'user_id': target_id}).get('first_name','کاربر')}</a>\n"
        f"💰 تعداد سکه اضافه شده: {amount}",
        parse_mode="HTML"
    )

    temp_data.pop(target_id, None)
    admin_messages.pop(target_id, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_buy_"))
def reject_buy(call):
    target_id = int(call.data.split("_")[2])

    # همه admin هایی که برای این خرید پیام داشتند
    allowed_admins = [admin_id for admin_id, _ in admin_messages.get(target_id, [])]

    # همیشه سوپر ادمین را هم اضافه کن
    if SUPER_ADMIN not in allowed_admins:
        allowed_admins.append(SUPER_ADMIN)

    if call.from_user.id not in allowed_admins:
        bot.answer_callback_query(call.id, "❌ اجازه ندارید این خرید را رد کنید")
        return 

    # حذف داده موقت و دکمه‌ها
    temp_data.pop(target_id, None)
    for admin_id, msg_id in admin_messages.get(target_id, []):
        try:
            bot.edit_message_reply_markup(chat_id=admin_id, message_id=msg_id, reply_markup=None)
        except:
            pass
    admin_messages.pop(target_id, None)

    # لاگ به سوپرادمین
    send_coin_log(
        f"❌ خرید رد شد\n"
        f"👤 ادمین: <a href='tg://user?id={call.from_user.id}'>{call.from_user.first_name}</a>\n"
        f"👤 کاربر: <a href='tg://user?id={target_id}'>{users_col.find_one({'user_id': target_id}).get('first_name','کاربر')}</a>",
        parse_mode="HTML"
    )

    # اطلاع کاربر
    try:
        bot.send_message(target_id, "❌ درخواست خرید شما رد شد.")
    except:
        pass

@bot.message_handler(content_types=["photo"])
def handle_receipt(message):
    uid = message.from_user.id

    if user_state.get(uid) != "await_receipt":
        return

    data = temp_data.get(uid)
    if not data:
        return

    coins = data["buy_amount"]
    total = data["buy_total"]
    file_id = message.photo[-1].file_id

    caption = (
        f"🧾 درخواست خرید جدید\n\n"
        f"👤 کاربر: {message.from_user.first_name}\n"
        f"🆔 آیدی: {uid}\n"
        f"💰 تعداد سکه: {coins}\n"
        f"💵 مبلغ: {total:,} تومان"
    )

    # تعیین دریافت‌کننده‌ها
    if uid in ADMINS:
        # اگر خود کاربر ادمین است → پیام فقط برای سوپرادمین
        recipients = [SUPER_ADMIN]
    else:
        # کاربران عادی → پیام برای همه ADMINS
        recipients = ADMINS

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ تایید خرید", callback_data=f"confirm_buy_{uid}"),
        types.InlineKeyboardButton("❌ رد خرید", callback_data=f"reject_buy_{uid}")
    )

    admin_messages[uid] = []

    for admin in recipients:
        sent = bot.send_photo(admin, file_id, caption=caption, reply_markup=markup)
        admin_messages[uid].append((admin, sent.message_id))

    # لاگ به سوپرادمین
    send_coin_log(
        f"🛒 درخواست خرید جدید\n"
        f"👤 کاربر: <a href='tg://user?id={uid}'>{message.from_user.first_name}</a>\n"
        f"💰 تعداد سکه: {coins}\n"
        f"💵 مبلغ: {total:,} تومان",
        parse_mode="HTML"
    )

    bot.send_message(uid, "⏳ کاربر گرامی، تا تایید ادمین منتظر بمانید.")
    user_state.pop(uid, None)

@bot.callback_query_handler(func=lambda call: call.data == "open_support_menu")
def open_support_menu(call):
    new_markup = types.InlineKeyboardMarkup()
    new_markup.add(
        types.InlineKeyboardButton("🛠️ پشتیبانی", url="https://t.me/self_nix_support"),
        types.InlineKeyboardButton("💬 گپ", url="https://t.me/Nix_self_Group")
    )
    new_markup.add(
        types.InlineKeyboardButton("⬅️ بازگشت", callback_data="selfbot_main_panel")
    )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=new_markup
    )

  #===========================  

import threading
import time

def hourly_loop():
    while True:
        try:
            for user in users_col.find({}):
                manage_user_coins(user["user_id"])
        except Exception as e:
            print("Hourly deduct error:", e)
        time.sleep(3600)  # اجرای واقعی هر ۱ ساعت

# اجرای loop در thread جداگانه
threading.Thread(target=hourly_loop, daemon=True).start()



# ================= RUN BOT =================
print("Self Bot is running...")
bot.infinity_polling()
