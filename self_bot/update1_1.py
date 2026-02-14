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
TRIAL_DURATION = 1  # مدت سلف تست یک روزه
PRICE_PER_50 = 1000  # قیمت هر ۵۰ سکه برای خرید

# ================= MongoDB =================
mongo_uri = "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@" \
            "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017" \
            "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"

mongo = MongoClient(mongo_uri)
db = mongo.telegram_sessions
users_col = db.users
sessions_col = db.sessions

# ================= حافظه موقت =================
user_state = {}
temp_data = {}

# ================= ماژول قابل import =================
def setup_self_bot(bot, TOKEN):

    # ================= Helper Functions =================
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

    def add_referral(inviter_id: int, invited_id: int):
        invited = users_col.find_one({"user_id": invited_id})
        if invited and invited.get("referrer"):
            return
        users_col.update_one({"user_id": invited_id}, {"$set": {"referrer": inviter_id}}, upsert=True)
        add_coins(inviter_id, REFERRAL_REWARD)
        add_coins(invited_id, INVITED_REWARD)

    def start_trial_expiration(uid):
        """غیر فعال کردن trial بعد از 1 روز"""
        def remove_trial():
            users_col.update_one({"user_id": uid}, {"$set": {"trial_active": False}})
            try:
                bot.send_message(uid, "⚡ سلف تست یک روزه شما منقضی شد!")
            except:
                pass
        delay = TRIAL_DURATION * 24 * 3600
        threading.Timer(delay, remove_trial).start()

    # ================= Keyboards =================
    def get_main_panel():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 فعال سازی سلف ✨️", callback_data="start_self"))
        markup.add(types.InlineKeyboardButton("⚡️ سلف تست(یک روزه)⚡️", callback_data="start_trial"))
        markup.add(
            types.InlineKeyboardButton("💼 حساب کاربری👤", callback_data="account_info"),
            types.InlineKeyboardButton("🌟 زیر مجموعه گیری 🔗", callback_data="referral")
        )
        markup.add(types.InlineKeyboardButton("🛍 خرید الماس 💰", callback_data="buy_coins"))
        markup.add(types.InlineKeyboardButton("🗣گپ 💬", url="https://t.me/+UFkNow4CYBNmZGY8"))
        return markup

    def get_back_panel():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="main_panel"))
        return markup

    # ================= User Registration =================
    def register_user(user):
        """ذخیره اطلاعات کاربر هنگام اولین ورود"""
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

    # ================= Handlers =================
    @bot.message_handler(commands=["start"])
    def start_panel(message):
        register_user(message.from_user)
        uid = message.from_user.id
        bot.send_message(
            uid,
            "👋 سلام! به ربات سلف‌  ⦁ Self Nix خوش آمدید 🌹\nبرای مشاهده امکانات، دکمه‌ها را استفاده کنید.",
            reply_markup=get_main_panel()
        )

    @bot.callback_query_handler(func=lambda c: True)
    def handle_callbacks(call):
        uid = call.from_user.id
        data = call.data

        if data == "main_panel":
            bot.edit_message_text("پنل اصلی:", uid, call.message.message_id, reply_markup=get_main_panel())
            return

        # ---------- سلف واقعی ----------
        if data == "start_self":
            user = users_col.find_one({"user_id": uid})
            coins = user.get("coins", 0) if user else 0
            if coins < MIN_COINS:
                bot.answer_callback_query(call.id, f"💎 حداقل {MIN_COINS} سکه نیاز دارید! شما {coins} دارید.")
                return
            bot.edit_message_text("📱 شماره خود را وارد کنید (+98...)", uid, call.message.message_id)
            user_state[uid] = "await_phone_self"

        # ---------- سلف تست ----------
        elif data == "start_trial":
            user = users_col.find_one({"user_id": uid})
            if user and user.get("trial_used"):
                bot.answer_callback_query(call.id, "⚡ شما قبلاً سلف تست گرفتید!")
                return
            bot.edit_message_text("📱 شماره خود را وارد کنید (+98...) برای سلف تست", uid, call.message.message_id)
            user_state[uid] = "await_phone_trial"

        # ---------- حساب کاربری ----------
        elif data == "account_info":
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
            referral_link = f"https://t.me/YourBotUsername?start={uid}"

            msg = f"""اطلاعات شما:
اسم: {first_name} {last_name}
یوزرنیم: @{username}
ایدی عددی: {uid}
تعداد زیر مجموعه: {referrals}
تعداد سکه: {coins}
تاریخ عضویت: {created_str}

زیر مجموعه:
لینک زیر مجموعه گیری: {referral_link}
با دعوت افراد سکه رایگان بگیر
هر زیر مجموعه: {REFERRAL_REWARD} الماس✨️"""
            bot.edit_message_text(msg, uid, call.message.message_id, reply_markup=get_back_panel())

        # ---------- زیر مجموعه ----------
        elif data == "referral":
            referral_link = f"https://t.me/self_nix_bot?start={uid}"
            msg = f"""🌟 لینک اختصاصی زیر مجموعه شما:
{referral_link}
با دعوت افراد سکه رایگان بگیرید!
هر زیر مجموعه: {REFERRAL_REWARD} الماس✨️"""
            bot.edit_message_text(msg, uid, call.message.message_id, reply_markup=get_back_panel())

        # ---------- خرید الماس ----------
        elif data == "buy_coins":
            msg = f"""به ربات سلف‌  ⦁ Self Nix خوش آمدید

با خرید الماس می‌توانید سلف داشته باشید
قیمت هر ۵۰ سکه: {PRICE_PER_50} تومان

تعداد الماس مورد نظر خود را ارسال کنید:"""
            bot.edit_message_text(msg, uid, call.message.message_id, reply_markup=get_back_panel())
            user_state[uid] = "await_buy_amount"

    # ================= Message Handler =================
    @bot.message_handler(func=lambda m: True)
    def handle_messages(message):
        uid = message.from_user.id
        text = message.text.strip()

        # ---------- خرید الماس ----------
        if user_state.get(uid) == "await_buy_amount":
            try:
                amount = int(text)
                total = (amount / 50) * PRICE_PER_50
                bot.send_message(uid, f"💰 تعداد {amount} سکه برابر است با {total} تومان")
                user_state.pop(uid)
            except:
                bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید.")
            return

        # ---------- شماره سلف واقعی ----------
        if user_state.get(uid) == "await_phone_self":
            temp_data[uid] = {"phone": text}
            bot.send_message(uid, "✅ شماره دریافت شد. لطفاً کد OTP تلگرام را وارد کنید:")
            user_state[uid] = "await_otp_self"
            return

        # ---------- شماره سلف تست ----------
        if user_state.get(uid) == "await_phone_trial":
            temp_data[uid] = {"phone": text}
            bot.send_message(uid, "✅ شماره دریافت شد. لطفاً کد OTP تلگرام را وارد کنید:")
            user_state[uid] = "await_otp_trial"
            return

        # ---------- OTP و 2FA ----------
        if user_state.get(uid) in ["await_otp_self", "await_otp_trial", "await_2fa_self", "await_2fa_trial"]:
            phone = temp_data[uid]["phone"]
            code_or_pass = text
            route = ""
            next_state = ""
            if user_state[uid] == "await_otp_self":
                route = "send_code"
                next_state = "await_2fa_self"
            elif user_state[uid] == "await_otp_trial":
                route = "send_code"
                next_state = "await_2fa_trial"
            elif user_state[uid] == "await_2fa_self":
                route = "send_2fa"
            elif user_state[uid] == "await_2fa_trial":
                route = "send_2fa"

            try:
                res = requests.post(
                    f"{SITE_URL}/{route}",
                    json={"phone": phone, "code" if "otp" in route else "password": code_or_pass}
                ).json()
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
                    user_state.pop(uid)
                    temp_data.pop(uid)
                elif res.get("status") == "2fa":
                    bot.send_message(uid, "🔐 نیاز به رمز دو مرحله‌ای (2FA). لطفاً رمز را وارد کنید:")
                    user_state[uid] = next_state
                else:
                    bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
            except Exception as e:
                bot.send_message(uid, f"❌ خطا در ارتباط با سایت: {str(e)}")
            return

# ================= فقط وقتی import شد اجرا شود =================

    print("update1_1.py")
