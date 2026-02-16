import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import requests
from pymongo import MongoClient
from update1 import PanelManager
# ================= CONFIG =================
TOKEN = "8550709057:AAFzGO1-sCzxIHqJ0raZkB1yg9AqeO1PrJU"
SITE_URL = 'https://anime-1127-bot-x0nn.onrender.com'
MIN_COINS = 10
REFERRAL_REWARD = 25
PRICE_PER_50 = 1000
TRIAL_DURATION = 1  # روز

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
sessions_col = db.sessions
required_chats_col = db1.required_chats



# ================= Bot =================
bot = telebot.TeleBot(TOKEN)
panel_manager = PanelManager(bot)
#==================data =================
user_state = {}
temp_data = {}
panel_text = (
    "✨ سلام و درود 🌹\n"
    "به ربات ⦁ Self Nix خوش اومدید 🙌🔥\n\n"
    "با این ربات می‌تونید امکانات اکانتتون رو بیشتر و خاص‌تر کنید 💎🚀"
)
ADMINS = [6433381392, 8588914809, 8277911482] 

# ================= Helper =================
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
    uid = user.id
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({
            "user_id": uid,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
            "coins": 0,
            "created_at": datetime.utcnow(),
            "trial_used": False
        })

def get_main_panel():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 فعال سازی سلف ✨️", callback_data="selfbot_start_self"))
    markup.add(types.InlineKeyboardButton("⚡️ سلف تست(یک روزه)⚡️", callback_data="selfbot_start_trial"))
    markup.row(
        types.InlineKeyboardButton("💼 حساب کاربری👤", callback_data="selfbot_account_info"),
        types.InlineKeyboardButton("🌟 زیر مجموعه گیری 🔗", callback_data="selfbot_referral")
    )
    markup.add(types.InlineKeyboardButton("🛍 خرید سکه 💰", callback_data="selfbot_buy_coins"))
    
    markup.add(types.InlineKeyboardButton("💬گپ🗣",
    
      url="https://t.me/+UFkNow4CYBNmZGY8"))
    
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



# ================= Handlers =================
@bot.message_handler(commands=["start"])
def start_panel(message):

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
    if message.from_user.id not in ADMINS:
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
    except:
        pass

@bot.message_handler(commands=["add"])
def add_required_chat(message):
    if message.from_user.id not in ADMINS:
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
        if coins < MIN_COINS:
            bot.answer_callback_query(call.id, f"💎 حداقل {MIN_COINS} سکه نیاز دارید! شما {coins} دارید.")
            return
        safe_edit(call, "📱 شماره خود را وارد کنید (+98...) برای سلف اصلی")
        user_state[uid] = "await_phone_self"

    elif data == "selfbot_start_trial":
        if user.get("trial_used"):
            bot.answer_callback_query(call.id, "⚡ شما قبلاً سلف تست گرفتید!")
            return
        safe_edit(call, "📱 شماره خود را وارد کنید (+98...) برای سلف تست یک روزه")
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
        safe_edit(call, msg, get_back_panel())

    elif data == "selfbot_referral":
        referral_link = f"https://t.me/self_nix_bot?start={uid}"
        msg = f"🌟 لینک اختصاصی زیر مجموعه شما:\n{referral_link}\nهر زیر مجموعه: {REFERRAL_REWARD} سکه✨️"
        safe_edit(call, msg, get_back_panel())

    elif data == "selfbot_buy_coins":
        msg = f"تعداد سکه مورد نظر خود را ارسال کنید. هر ۵۰ سکه: {PRICE_PER_50} تومان"
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

    # خرید سکه
    if state == "await_buy_amount":
        if not text.isdigit():
            bot.send_message(uid, "❌ لطفاً عدد وارد کنید.")
            return
        amount = int(text)
        total = int((amount / 50) * PRICE_PER_50)
        bot.send_message(uid, f"💰 تعداد {amount} سکه برابر است با {total} تومان")
        user_state.pop(uid, None)
        return

    # شماره
    if state in ["await_phone_self", "await_phone_trial"]:
        temp_data[uid] = {"phone": text}
        try:
            res = requests.post(f"{SITE_URL}/send_phone", json={"phone": text, "trial": state=="await_phone_trial"}, timeout=15).json()
        except Exception as e:
            bot.send_message(uid, f"❌ خطا در ارسال شماره: {e}")
            return

        if res.get("status") == "ok":
            bot.send_message(uid, "✅ شماره ثبت شد. لطفاً کد OTP را وارد کنید:")
            user_state[uid] = "await_otp_self" if state == "await_phone_self" else "await_otp_trial"
        else:
            bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
        return

    # OTP و 2FA
    if state in ["await_otp_self", "await_otp_trial", "await_2fa_self", "await_2fa_trial"]:
        phone = temp_data.get(uid, {}).get("phone")
        if not phone:
            bot.send_message(uid, "❌ شماره پیدا نشد. دوباره /start بزنید.")
            user_state.pop(uid, None)
            return

        trial = "trial" in state
        if "otp" in state:
            # ارسال کد OTP
            try:
                res = requests.post(f"{SITE_URL}/send_code", json={"phone": phone, "code": text, "trial": trial}, timeout=15).json()
            except Exception as e:
                bot.send_message(uid, f"❌ خطا در ارسال کد: {e}")
                return
        else:
            # ارسال 2FA
            try:
                res = requests.post(f"{SITE_URL}/send_2fa", json={"phone": phone, "password": text, "trial": trial}, timeout=15).json()
            except Exception as e:
                bot.send_message(uid, f"❌ خطا در ارسال 2FA: {e}")
                return

        if res.get("status") == "ok":
            users_col.update_one({"user_id": uid}, {"$set": {
                "phone": phone,
                "trial_active": trial,
                "trial_used": trial or users_col.find_one({"user_id": uid}).get("trial_used", False),
                "trial_end": datetime.utcnow() + timedelta(days=TRIAL_DURATION) if trial else None
            }})
            if trial:
                start_trial_expiration(uid)
                bot.send_message(uid, "✅ سلف تست یک روزه ساخته شد و ورود کامل شد!")
            else:
                bot.send_message(uid, "✅ سلف اصلی ساخته شد و ورود کامل شد!")
            user_state.pop(uid, None)
            temp_data.pop(uid, None)

        elif res.get("status") == "2fa":
            bot.send_message(uid, "🔐 نیاز به رمز دو مرحله‌ای (2FA). لطفاً وارد کنید:")
            user_state[uid] = "await_2fa_trial" if trial else "await_2fa_self"
        else:
            bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")

# ================= RUN BOT =================
print("Self Bot is running...")
bot.infinity_polling()