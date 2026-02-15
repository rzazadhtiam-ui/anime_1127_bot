import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import requests
from pymongo import MongoClient

# ================= CONFIG =================
SITE_URL = 'https://anime-1127-bot-x0nn.onrender.com'
MIN_COINS = 10
REFERRAL_REWARD = 25
INVITED_REWARD = 5
TRIAL_DURATION = 1
PRICE_PER_50 = 1000

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
users_col = db.users
sessions_col = db.sessions

# ================= حافظه موقت =================
user_state = {}
temp_data = {}

# ================= ماژول =================
def setup_self_bot(bot, TOKEN):

    # ---------- Safe Edit ----------
    def safe_edit(call, text, markup=None):
        try:
            bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(call.from_user.id, text, reply_markup=markup)

    # ---------- Helper ----------
    def add_coins(user_id: int, amount: int):
        user = users_col.find_one({"user_id": user_id}) or {"user_id": user_id, "coins": 0}
        new_total = user.get("coins", 0) + amount
        users_col.update_one({"user_id": user_id}, {"$set": {"coins": new_total}}, upsert=True)
        check_coins(user_id)

    def check_coins(user_id: int):
        user = users_col.find_one({"user_id": user_id})
        if not user:
            return
        coins = user.get("coins", 0)
        if coins < MIN_COINS:
            phone = user.get("phone")
            if phone:
                session = sessions_col.find_one({"phone": phone})
                if session and session.get("power") == "on":
                    sessions_col.update_one({"phone": phone}, {"$set": {"power": "off"}})

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
        try:
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
        except:
            pass

    # ---------- Keyboards ----------
    def get_main_panel():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 فعال سازی سلف ✨️", callback_data="selfbot_start_self"))
        markup.add(types.InlineKeyboardButton("⚡️ سلف تست(یک روزه)⚡️", callback_data="selfbot_start_trial"))
        markup.row(
            types.InlineKeyboardButton("💼 حساب کاربری👤", callback_data="selfbot_account_info"),
            types.InlineKeyboardButton("🌟 زیر مجموعه گیری 🔗", callback_data="selfbot_referral")
        )
        markup.add(types.InlineKeyboardButton("🛍 خرید سکه 💰", callback_data="selfbot_buy_coins"))
        markup.add(types.InlineKeyboardButton("🗣گپ 💬", url="https://t.me/+UFkNow4CYBNmZGY8"))
        return markup

    def get_back_panel():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="selfbot_main_panel"))
        return markup

    # ---------- Start ----------
    @bot.message_handler(commands=["start"])
    def start_panel(message):
        register_user(message.from_user)
        uid = message.from_user.id
        bot.send_message(
            uid,
            """✨ سلام و درود 🌹
به ربات ⦁ Self Nix خوش اومدید 🙌🔥
با این ربات می‌تونید امکانات اکانتتون رو بیشتر و خاص‌تر کنید 💎🚀""",
            reply_markup=get_main_panel()
        )

    # ---------- Callbacks ----------
    @bot.callback_query_handler(func=lambda c: c.data.startswith("selfbot_"))
    def handle_callbacks(call):
        uid = call.from_user.id
        data = call.data
        bot.answer_callback_query(call.id)

        if data == "selfbot_main_panel":
            safe_edit(call, "پنل اصلی:", get_main_panel())

        elif data == "selfbot_start_self":
            user = users_col.find_one({"user_id": uid}) or {}
            coins = user.get("coins", 0)

            if coins < MIN_COINS:
                bot.answer_callback_query(call.id, f"💎 حداقل {MIN_COINS} سکه نیاز دارید! شما {coins} دارید.")
                return

            safe_edit(call, "📱 شماره خود را وارد کنید (+98...)")
            user_state[uid] = "await_phone_self"

        elif data == "selfbot_start_trial":
            user = users_col.find_one({"user_id": uid}) or {}

            if user.get("trial_used"):
                bot.answer_callback_query(call.id, "⚡ شما قبلاً سلف تست گرفتید!")
                return

            safe_edit(call, "📱 شماره خود را وارد کنید (+98...) برای سلف تست")
            user_state[uid] = "await_phone_trial"

        elif data == "selfbot_account_info":
            user = users_col.find_one({"user_id": uid})
            if not user:
                bot.answer_callback_query(call.id, "❌ شما هنوز هیچ سلفی فعال نکرده‌اید!")
                return

            first_name = user.get("first_name", "")
            last_name = user.get("last_name", "")
            username = user.get("username", "ثبت نشده")
            coins = user.get("coins", 0)
            referrals = users_col.count_documents({"referrer": uid})
            created_at = user.get("created_at")
            created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "ثبت نشده"

            msg = f"""اطلاعات شما:
اسم: {first_name} {last_name}
یوزرنیم: @{username}
ایدی عددی: {uid}
تعداد زیر مجموعه: {referrals}
تعداد سکه: {coins}
تاریخ عضویت: {created_str}"""

            safe_edit(call, msg, get_back_panel())

        elif data == "selfbot_referral":
            referral_link = f"https://t.me/self_nix_bot?start={uid}"
            msg = f"""🌟 لینک اختصاصی زیر مجموعه شما:
{referral_link}
با دعوت افراد سکه رایگان بگیرید!
هر زیر مجموعه: {REFERRAL_REWARD} سکه✨️"""

            safe_edit(call, msg, get_back_panel())

        elif data == "selfbot_buy_coins":
            msg = f"""به ربات ⦁ Self Nix خوش آمدید

با خرید سکه می‌توانید سلف داشته باشید
قیمت هر ۵۰ سکه: {PRICE_PER_50} تومان

تعداد سکه مورد نظر خود را ارسال کنید:"""

            safe_edit(call, msg, get_back_panel())
            user_state[uid] = "await_buy_amount"

    # ---------- Messages ----------
    @bot.message_handler(func=lambda m: True)
    def handle_messages(message):
        uid = message.from_user.id
        text = message.text.strip()

        # خرید سکه
        if user_state.get(uid) == "await_buy_amount":
            if not text.isdigit():
                bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید.")
                return

            amount = int(text)
            if amount <= 0:
                bot.send_message(uid, "❌ عدد معتبر نیست.")
                return

            total = int((amount / 50) * PRICE_PER_50)
            bot.send_message(uid, f"💰 تعداد {amount} سکه برابر است با {total} تومان")
            user_state.pop(uid, None)
            return

        # شماره سلف
        if user_state.get(uid) in ["await_phone_self", "await_phone_trial"]:
            temp_data[uid] = {"phone": text}
            bot.send_message(uid, "✅ شماره دریافت شد. لطفاً کد OTP تلگرام را وارد کنید:")

            if user_state[uid] == "await_phone_self":
                user_state[uid] = "await_otp_self"
            else:
                user_state[uid] = "await_otp_trial"
            return

        # OTP و 2FA
        if user_state.get(uid) in ["await_otp_self", "await_otp_trial", "await_2fa_self", "await_2fa_trial"]:

            if uid not in temp_data:
                user_state.pop(uid, None)
                return

            phone = temp_data[uid]["phone"]
            route = "send_code" if "otp" in user_state[uid] else "send_2fa"

            try:
                res = requests.post(
                    f"{SITE_URL}/{route}",
                    json={"phone": phone, "code" if route == "send_code" else "password": text},
                    timeout=15
                ).json()
            except Exception as e:
                bot.send_message(uid, f"❌ خطا در ارتباط با سایت: {str(e)}")
                return

            if res.get("status") == "ok":

                if "trial" in user_state[uid]:
                    users_col.update_one({"user_id": uid}, {"$set": {
                        "phone": phone,
                        "trial_active": True,
                        "trial_end": datetime.utcnow() + timedelta(days=TRIAL_DURATION),
                        "trial_used": True
                    }}, upsert=True)

                    start_trial_expiration(uid)
                    bot.send_message(uid, "✅ سلف تست یک روزه ساخته شد و ورود کامل شد!")

                else:
                    users_col.update_one({"user_id": uid}, {"$set": {"phone": phone}}, upsert=True)
                    bot.send_message(uid, "✅ سشن ساخته شد و ورود کامل شد!")

                user_state.pop(uid, None)
                temp_data.pop(uid, None)

            elif res.get("status") == "2fa":
                bot.send_message(uid, "🔐 نیاز به رمز دو مرحله‌ای (2FA). لطفاً رمز را وارد کنید:")

                if "trial" in user_state[uid]:
                    user_state[uid] = "await_2fa_trial"
                else:
                    user_state[uid] = "await_2fa_self"

            else:
                bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
