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
TRIAL_DURATION = 1  # روز
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

# ================= کلاس ماژول =================
class SelfBotModule:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.setup_handlers()

    # ---------- Helpers ----------
    def safe_edit(self, call, text, markup=None):
        try:
            self.bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)
        except:
            self.bot.send_message(call.from_user.id, text, reply_markup=markup)

    def add_coins(self, user_id: int, amount: int):
        user = users_col.find_one({"user_id": user_id}) or {"user_id": user_id, "coins": 0}
        new_total = user.get("coins", 0) + amount
        users_col.update_one({"user_id": user_id}, {"$set": {"coins": new_total}}, upsert=True)
        self.check_coins(user_id)

    def check_coins(self, user_id: int):
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

    def start_trial_expiration(self, uid):
        def remove_trial():
            users_col.update_one({"user_id": uid}, {"$set": {"trial_active": False}})
            try:
                self.bot.send_message(uid, "⚡ سلف تست یک روزه شما منقضی شد!")
            except:
                pass
        threading.Timer(TRIAL_DURATION * 86400, remove_trial).start()

    def register_user(self, user):
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
    def get_main_panel(self):
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

    def get_back_panel(self):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="selfbot_main_panel"))
        return markup

    # ---------- Handlers ----------
    def setup_handlers(self):
        bot = self.bot

        @bot.message_handler(commands=["start"])
        def start_panel(message):
            self.register_user(message.from_user)
            uid = message.from_user.id
            bot.send_message(
                uid,
                "✨ سلام و درود 🌹\nبه ربات ⦁ Self Nix خوش اومدید 🙌🔥\nبا این ربات می‌تونید امکانات اکانتتون رو بیشتر و خاص‌تر کنید 💎🚀",
                reply_markup=self.get_main_panel()
            )

        @bot.callback_query_handler(func=lambda c: c.data.startswith("selfbot_"))
        def handle_callbacks(call):
            uid = call.from_user.id
            data = call.data
            bot.answer_callback_query(call.id)

            if data == "selfbot_main_panel":
                self.safe_edit(call, "پنل اصلی:", self.get_main_panel())

            elif data == "selfbot_start_self":
                self.safe_edit(call, "📱 شماره خود را وارد کنید (+98...)")
                user_state[uid] = "await_phone_self"

            elif data == "selfbot_start_trial":
                user = users_col.find_one({"user_id": uid}) or {}
                if user.get("trial_used"):
                    bot.answer_callback_query(call.id, "⚡ شما قبلاً سلف تست گرفتید!")
                    return
                self.safe_edit(call, "📱 شماره خود را وارد کنید (+98...) برای سلف تست")
                user_state[uid] = "await_phone_trial"

            elif data == "selfbot_account_info":
                user = users_col.find_one({"user_id": uid})
                if not user:
                    self.safe_edit(call, "❌ شما هنوز هیچ سلفی فعال نکرده‌اید!", self.get_back_panel())
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
                self.safe_edit(call, msg, self.get_back_panel())

            elif data == "selfbot_referral":
                referral_link = f"https://t.me/self_nix_bot?start={uid}"
                msg = f"""🌟 لینک اختصاصی زیر مجموعه شما:
{referral_link}
با دعوت افراد سکه رایگان بگیرید!
هر زیر مجموعه: {REFERRAL_REWARD} سکه✨️"""
                self.safe_edit(call, msg, self.get_back_panel())

            elif data == "selfbot_buy_coins":
                msg = f"به ربات ⦁ Self Nix خوش آمدید\n\nبا خرید سکه می‌توانید سلف داشته باشید\nقیمت هر ۵۰ سکه: {PRICE_PER_50} تومان\n\nتعداد سکه مورد نظر خود را ارسال کنید:"
                self.safe_edit(call, msg, self.get_back_panel())
                user_state[uid] = "await_buy_amount"

        @bot.message_handler(func=lambda m: True)
        def handle_messages(message):
            uid = message.from_user.id
            text = message.text.strip()
            state = user_state.get(uid)
            if not state:
                return

            # خرید سکه
            if state == "await_buy_amount":
                if not text.isdigit():
                    bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید.")
                    return
                amount = int(text)
                if amount <= 0:
                    bot.send_message(uid, "❌ عدد معتبر نیست.")
                    return
                total = int((amount / 50) * PRICE_PER_50)
                bot.send_message(uid, f"💰 تعداد {amount} سکه برابر است با {total} تومان")
                user_state.pop(uid)
                return

            # ثبت شماره و ارسال به سایت
            if state in ["await_phone_self", "await_phone_trial"]:
                temp_data[uid] = {"phone": text}
                try:
                    res = requests.post(f"{SITE_URL}/send_phone", json={"phone": text}, timeout=15).json()
                    if res.get("status") == "ok":
                        bot.send_message(uid, "✅ شماره ثبت شد. کد OTP را که تلگرام فرستاد وارد کنید:")
                        user_state[uid] = "await_otp"
                    else:
                        bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
                except Exception as e:
                    bot.send_message(uid, f"❌ خطا در ارتباط با سایت: {str(e)}")
                return

            # دریافت OTP
            if state == "await_otp":
                phone = temp_data[uid]["phone"]
                code = text
                try:
                    res = requests.post(f"{SITE_URL}/send_code", json={"phone": phone, "code": code}, timeout=15).json()
                    status = res.get("status")
                    if status == "ok":
                        bot.send_message(uid, "✅ سشن ساخته شد و ذخیره شد!")
                        user_state.pop(uid)
                        temp_data.pop(uid)
                    elif status == "2fa":
                        bot.send_message(uid, "🔐 نیاز به کد دو مرحله‌ای (2FA) دارید. لطفاً رمز 2FA را وارد کنید:")
                        user_state[uid] = "await_2fa"
                    else:
                        bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
                except Exception as e:
                    bot.send_message(uid, f"❌ خطا در ارتباط با سایت: {str(e)}")
                return

            # دریافت 2FA
            if state == "await_2fa":
                phone = temp_data[uid]["phone"]
                password = text
                try:
                    res = requests.post(f"{SITE_URL}/send_2fa", json={"phone": phone, "password": password}, timeout=15).json()
                    if res.get("status") == "ok":
                        bot.send_message(uid, "✅ سشن ساخته شد و ورود کامل شد!")
                        user_state.pop(uid)
                        temp_data.pop(uid)
                    else:
                        bot.send_message(uid, f"❌ خطا: {res.get('message','نامعلوم')}")
                except Exception as e:
                    bot.send_message(uid, f"❌ خطا در ارتباط با سایت: {str(e)}")
