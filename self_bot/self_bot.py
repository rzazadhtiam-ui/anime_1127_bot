import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import types
from aiogram.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# بقیه importها...


from bson import ObjectId
from datetime import datetime, timedelta, UTC
from flask import request
import threading
import requests
from pymongo import MongoClient
from update1 import setup_panel
from update1_2 import register_commands
# ================= CONFIG =================

TOKEN = "8550709057:AAEOPl9Z1IoHio-cZ2royEjHpbbtbzJXxNQ"
SITE_URL = 'https://anime-1127-bot-x0nn.onrender.com'
#BOT_URL = "https://self-bot-ssvq.onrender.com"
MIN_COIN = 2
REFERRAL_REWARD = 6
TRIAL_DURATION = 1  # روز
HOURLY_DEDUCT = 2  # تعداد سکه‌ای که هر ساعت کم می‌کنه
MIN_COINS_FOR_SESSION = 2 # حداقل سکه برای ادامه سشن
BOT_USERNAME = "tiam"
COIN_PRICES = {
    50: 5000,
    100: 9000,
    250: 22000,
    500: 42000,
    1000: 85000
}
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
sessions_col = db.sessions
required_chats_col = db1.required_chats



# ================= Bot =================
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

dp.include_router(router)


# بعد از dp.include_router(router)
register_commands(router, bot)   # ← درست این شکلیه

# ==================== START BOT ====================
async def main():
    print("🚀 در حال راه‌اندازی ربات...")
    
    # پنل Self Nix رو راه‌اندازی کن
    await setup_panel(bot)
    
    # اگر register_commands نیاز به کار خاصی داره، اینجا هم می‌تونی بذاری
    # register_commands(router, bot)  # اگر قبلاً در سطح ماژول کال کردی، دوباره لازم نیست
    
    # شروع polling
    
#==================data =================
user_state = {}
temp_data = {}
panel_text = (
    "✨ سلام و درود 🌹\n"
    "به ربات ⦁ Self Nix خوش اومدید 🙌🔥\n\n"
    "با این ربات می‌تونید امکانات اکانتتون رو بیشتر و خاص‌تر کنید 💎🚀"
)
ADMIN = [6433381392, 8588914809, 8277911482] 



SUPER_ADMIN = 6433381392
BOT_DISABLED = False
# ================= Helper =================

async def send_coin_log(text, parse_mode=None):
    try:
        await bot.send_message(SUPER_ADMIN, f"📊 گزارش سکه:\n\n{text}", parse_mode=parse_mode)
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

async def safe_edit(call, text, markup=None):
    try:
        await bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)
    except:
        await bot.send_message(call.from_user.id, text, reply_markup=markup)

def start_trial_expiration(uid):
    async def remove_trial():
        users_col.update_one(
            {"user_id": uid},
            {"$set": {"trial_active": False}}
        )

        try:
            await bot.send_message(uid, "⚡ سلف تست یک روزه شما منقضی شد!")
        except Exception as e:
            print(e)

    asyncio.create_task(delayed_remove())

    async def delayed_remove():
        await asyncio.sleep(TRIAL_DURATION * 86400)
        await remove_trial()


def register_user(user, referrer=None):
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
                "is_admin": False,
                "wins": 0,
                "referrer": referrer
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
        callback_data="open_support_menu",
        style="primary"
    )
    )
    
    return markup

def get_back_panel():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="selfbot_main_panel", style="danger"))
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
            username = chat_link.split("t.me/")[1].split("?")[0]
            return "@" + username
        if chat_link.startswith("@"):
            return chat_link
        return "@" + chat_link
    except:
        return None


def calculate_price(amount):
    if amount <= 50:
        return 5000
    elif amount <= 100:
        return int(amount * 90)
    elif amount <= 250:
        return int(amount * 88)
    elif amount <= 500:
        return int(amount * 84)
    elif amount <= 1000:
        return int(amount * 85)
    else:
        return int(amount * 80)


async def is_user_joined(user_id):
    chats = list(required_chats_col.find({}))

    missing = []

    for chat in chats:
        try:
            chat_id = resolve_chat(chat["link"])

            member = await bot.get_chat_member(
                chat_id=chat_id,
                user_id=user_id
            )

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


async def manage_user_coins(uid):
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
                        await bot.send_message(
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
                    await bot.send_message(
                        uid,
                        "✅ سکه‌های شما شارژ شد!\اکانت هایی که به دلیل کمبود سکه خاموش شده بودند دوباره فعال شدند."
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



# ================= Handlers =================

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
    "https://self-bot-ssvq.onrender.com",
    "https://self-bot-zva7.onrender.com"
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

def is_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("ban", False) if user else False

def is_bot_off(uid):
    if BOT_DISABLED and uid != SUPER_ADMIN:
        return True
    return False

# ================= Flask =================
async def block_if_banned(user_id, call=None, message=None):
    if is_banned(user_id):
        try:
            if call:
                bot.answer_callback_query(call.id, "⛔ شما بن هستید")
                await bot.send_message(user_id, "⛔ دسترسی شما محدود شده است")
            if message:
                await bot.send_message(user_id, "⛔ شما بن هستید")
        except:
            pass
        return True
    return False

# ================= TeleBot Handlers =================



@router.message(F.text == "/start")
async def start_panel(message: Message):
    if not command_allowed(message):
        return

    uid = message.from_user.id

    if is_bot_off(uid):
        return

    register_user(message.from_user)

    missing = await is_user_joined(uid)

    if missing:
        await message.answer(
            "⚠️ برای استفاده از ربات باید در کانال‌ها و گروه‌های زیر عضو شوید:",
            reply_markup=get_membership_panel(missing)
        )
        return

    await message.answer(
        panel_text,
        reply_markup=get_main_panel()
    )



@router.message(F.text == "/ping")
async def awake_bot(message: Message):
    if not command_allowed(message):
        return

    if message.from_user.id != SUPER_ADMIN:
        print("paaaaa")
        return

    started = start_keep_alive()

    if started:
        await message.answer("سیستم Keep-Alive فعال شد 🔥")
    else:
        await message.answer("قبلاً فعال بوده 👁")


@router.message(F.text == "/sleep")
async def sleep_bot(message: Message):
    if not command_allowed(message):
        return

    if message.from_user.id != SUPER_ADMIN:
        return

    stopped = stop_keep_alive()

    if stopped:
        await message.answer("سیستم Keep-Alive خاموش شد 😴")
    else:
        await message.answer("قبلاً خاموش بوده")

@router.message(F.text.startswith("/admin"))
async def admin_manage(message: Message):
    if not command_allowed(message):
        return

    if message.from_user.id not in ADMIN:
        return

    args = message.text.split()

    if len(args) < 3:
        await message.answer("فرمت: /admin add|remove <user_id>")
        return

    action = args[1].lower()
    try:
        uid = int(args[2])
    except ValueError:
        await message.answer("❌ user_id باید عدد باشد")
        return

    if action == "add":
        users_col.update_one(
            {"user_id": uid},
            {"$set": {"is_admin": True}}
        )
        await message.answer("✅ ادمین شد")

    elif action == "remove":
        users_col.update_one(
            {"user_id": uid},
            {"$set": {"is_admin": False}}
        )
        await message.answer("❌ از ادمین حذف شد")

    else:
        await message.answer("❌ اکشن نامعتبر است (add یا remove)")


from aiogram import Router, F
from aiogram.types import Message



@router.message(F.text == "/bot_off")
async def bot_off(message: Message):
    global BOT_DISABLED

    if message.from_user.id != SUPER_ADMIN:
        return

    BOT_DISABLED = True
    await message.answer("⛔ ربات خاموش شد")

@router.message(F.text == "/bot_on")
async def bot_on(message):
    global BOT_DISABLED

    if message.from_user.id != SUPER_ADMIN:
        return

    BOT_DISABLED = False
    await message.answer("✅ ربات روشن شد")

@router.message(F.text.startswith("/admin_gift"))
async def give_coins_admin(message):
    if not command_allowed(message):
        return

    if message.from_user.id not in ADMIN:
        await message.answer("❌ شما دسترسی لازم را ندارید!")
        return

    uid = message.from_user.id
    if is_bot_off(uid):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer("❌ فرمت دستور: /admin_gift <آیدی> <تعداد سکه>")
        return

    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("❌ آیدی و تعداد سکه باید عدد باشند!")
        return

    users_col.update_one(
        {"user_id": target_id},
        {"$inc": {"coins": amount}},
        upsert=True
    )

    recipient = users_col.find_one({"user_id": target_id})
    recipient_name = recipient.get("first_name", "کاربر ناشناس")

    await message.answer(
        f"✅ {amount} سکه به کاربر {recipient_name} اضافه شد."
    )

    try:
        await message.bot.send_message(
            target_id,
            f"🌟 {amount} سکه توسط ادمین به حساب شما اضافه شد!"
        )

        send_coin_log(
            f"🔄 انتقال سکه\n"
            f"👤 از: {uid}\n"
            f"👤 به: {target_id}\n"
            f"💰 مقدار: {amount}"
        )

    except:
        pass
        
        
@router.message(F.text.startswith("/add_baton"))
async def add_required_chat(message):
    if not command_allowed(message):
        return

    uid = message.from_user.id

    if uid != SUPER_ADMIN:
        await message.answer("❌ دسترسی ندارید!")
        return

    if is_bot_off(uid):
        return

    args = message.text.split(maxsplit=2)

    if len(args) != 3:
        await message.answer("❌ فرمت درست: /add_baton <link> <button_name>")
        return

    link = args[1]
    button_name = args[2]

    required_chats_col.insert_one({
        "link": link,
        "button_name": button_name
    })

    await message.answer(f"✅ دکمه '{button_name}' اضافه شد!")

@router.message(F.text.startswith("/remove_baton"))
async def remove_baton(message):
    uid = message.from_user.id

    if uid != SUPER_ADMIN:
        await message.answer("❌ دسترسی ندارید")
        return

    if is_bot_off(uid):
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer("فرمت: /remove_baton <link>")
        return

    link = args[1]

    result = required_chats_col.delete_one({"link": link})

    if result.deleted_count:
        await message.answer("✅ حذف شد")
    else:
        await message.answer("❌ پیدا نشد")

@router.callback_query(F.data.startswith("selfbot_"))
async def handle_callbacks(call):
    uid = call.from_user.id

    if is_banned(uid) or is_bot_off(uid):
        return

    data = call.data
    user = users_col.find_one({"user_id": uid}) or {}

    await call.answer()

    if data == "selfbot_main_panel":

        uid = call.from_user.id

    # مهم: پاک کردن وضعیت کاربر
        user_state.pop(uid, None)
        temp_data.pop(uid, None)

        await call.message.edit_text(
            panel_text,
            reply_markup=get_main_panel()
        )

        await call.answer()
    
    elif data == "selfbot_start_self":
        coins = user.get("coins", 0)
        required = MIN_COIN

        if coins < required:
            missing = required - coins

            msg = await call.message.bot.send_message(
                uid,
                f"⚠️ سکه‌های شما کافی نیست!\nمقدار مورد نیاز: {missing} سکه"
            )

            import threading
            threading.Timer(
                3,
                lambda: call.message.bot.delete_message(uid, msg.message_id)
            ).start()

            return

        await call.message.edit_text("📱 شماره خود را وارد کنید (+98...)")
        user_state[uid] = "await_phone_self"

    elif data == "selfbot_start_trial":
        if user.get("trial_used"):
            await call.answer("⚡ شما قبلاً سلف تست گرفتید!", show_alert=True)
            return

        await call.message.edit_text("📱 شماره خود را وارد کنید (+98...)")
        user_state[uid] = "await_phone_trial"

    elif data == "selfbot_account_info":
        first_name = user.get("first_name", "")
        username = user.get("username", "-")
        coins = user.get("coins", 0)
        referrals = users_col.count_documents({"referrer": uid})

        created_at = user.get("created_at")
        created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "-"

        msg = (
            f"اطلاعات شما:\n"
            f"اسم: {first_name}\n"
            f"یوزرنیم: @{username}\n"
            f"ایدی عددی: `{uid}`\n"
            f"تعداد زیر مجموعه: {referrals}\n"
            f"تعداد سکه: {coins}\n"
            f"تاریخ عضویت: {created_str}"
        )

        await call.message.edit_text(
            msg,
            reply_markup=get_user_sessions_panel(uid)
        )

    elif data == "selfbot_referral":
        referral_link = f"https://t.me/self_nix_bot?start={uid}"

        msg = (
            f"🌟 لینک اختصاصی زیر مجموعه شما:\n{referral_link}\n"
            f"هر زیر مجموعه: {REFERRAL_REWARD} سکه✨️\n"
            f"معادل 3 ساعت استفاده از سلف"
        )

        await call.message.edit_text(msg, reply_markup=get_back_panel())

    elif data == "selfbot_buy_coins":
        msg = (
            "💰 تعداد سکه مورد نظر خود را ارسال کنید.\n\n"
            "💵 تعرفه خرید:\n"
            "• 50 سکه = 5,000 تومان\n"
            "• 100 سکه = 9,000 تومان\n"
            "• 250 سکه = 22,000 تومان\n"
            "• 500 سکه = 42,000 تومان\n"
            "• 1000 سکه = 85,000 تومان\n\n"
            "⏳ مصرف سکه:\n"
            "هر 2 سکه معادل 1 ساعت استفاده از سلف میباشد."
        )

        await call.message.edit_text(msg, reply_markup=get_back_panel())
        user_state[uid] = "await_buy_amount"




@router.callback_query(F.data == "check_membership")
async def check_membership_callback(call):
    uid = call.from_user.id

    if is_banned(uid) or is_bot_off(uid):
        return

    missing = await is_user_joined(uid)

    await call.answer()

    # اگر هنوز عضو نیست
    if missing:
        await call.message.edit_text(
            "❌ کاربر گرامی شما هنوز در بعضی کانال‌ها یا گروه‌ها عضو نشده‌اید",
            reply_markup=get_membership_panel(missing)
        )
        return

    # اگر عضو بود
    try:
        await call.message.delete()
    except:
        pass

    msg = await call.message.bot.send_message(
        uid,
        "✅ کاربر گرامی عضویت شما تایید شد\n"
        "به ربات ⦁ Self Nix خوش اومدی 🌟\n"
        "برای استفاده دستور /start رو مجدد ارسال کنید"
    )

    # ارسال پنل اصلی
    await call.message.bot.send_message(
        uid,
        panel_text,
        reply_markup=get_main_panel()
    )

    # حذف پیام تایید بعد ۱۰ ثانیه
    import threading

    def delete_confirm():
        try:
            call.message.bot.delete_message(uid, msg.message_id)
        except:
            pass

    threading.Timer(10, delete_confirm).start()
    
    
@router.message()
async def handle_messages(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    state = user_state.get(uid)

    # ---------------- خرید سکه ----------------
# ---------------- خرید سکه ----------------
    if state == "await_buy_amount":
        if not text.isdigit():

            if block_if_banned(uid, message=message):
                return

            await message.answer("❌ لطفاً فقط عدد وارد کنید.")
            return

        amount = int(text)

        if amount < 50:
            await message.answer("❌ حداقل خرید 50 سکه است.")
            return

        total = calculate_price(amount)

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

        await message.answer(msg)
        user_state[uid] = "await_receipt"
        return

    # ---------------- مرحله شماره ----------------
    if state in ["await_phone_self", "await_phone_trial"]:

        if block_if_banned(uid, message=message):
            return

        try:
            await bot.delete_message(uid, message.message_id)
        except:
            pass

        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try:
                await bot.delete_message(uid, prev_msg_id)
            except:
                pass

        temp_data[uid] = {"phone": text}

        try:
            res = requests.post(
            f"{SITE_URL}/send_phone",
            json={
                "phone": text,
                "trial": (state == "await_phone_trial")
            },
            timeout=15
        ).json()
        except Exception as e:
            msg = await bot.send_message(uid, f"❌ خطا در ارسال شماره: {e}")
            temp_data[uid]["last_msg_id"] = msg.message_id
            return

        if res.get("status") == "ok":
            msg = await bot.send_message(
            uid,
            "✅ شماره تایید شد. کد OTP را ارسال کنید\nمثال: 1.2.3.4.5"
        )
            temp_data[uid]["last_msg_id"] = msg.message_id
            user_state[uid] = (
            "await_otp_self" if state == "await_phone_self"
            else "await_otp_trial"
        )
        else:
            msg = await bot.send_message(
            uid,
            f"❌ خطا: {res.get('message', 'نامعلوم')}"
        )
            temp_data[uid]["last_msg_id"] = msg.message_id

        return

    # ---------------- مرحله OTP ----------------
    if state in ["await_otp_self", "await_otp_trial"]:

        if block_if_banned(uid, message=message):
            return

        try:
            await bot.delete_message(uid, message.message_id)
        except:
            pass

        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try:
                await bot.delete_message(uid, prev_msg_id)
            except:
                pass

        phone = temp_data.get(uid, {}).get("phone")
        if not phone:
            user_state.pop(uid, None)
            return

        trial = (state == "await_otp_trial")

        try:
            res = requests.post(
            f"{SITE_URL}/send_code",
            json={
                "phone": phone,
                "code": text,
                "trial": trial
            },
            timeout=15
        ).json()
        except Exception as e:
            msg = await bot.send_message(uid, f"❌ خطا در ارسال کد OTP: {e}")
            temp_data[uid]["last_msg_id"] = msg.message_id
            return

        if res.get("status") == "ok":

            users_col.update_one(
            {"user_id": uid},
            {"$set": {
                "phone": phone,
                "trial_active": trial,
                "trial_used": trial or users_col.find_one(
                    {"user_id": uid}
                ).get("trial_used", False),
                "trial_end": datetime.now(UTC) + timedelta(days=TRIAL_DURATION) if trial else None
            }}
        )

            if trial:
                start_trial_expiration(uid)

            msg = await bot.send_message(
            uid,
            f"✅ {'سلف تست' if trial else 'سلف اصلی'} با موفقیت فعال شد"
        )

            temp_data.pop(uid, None)
            user_state.pop(uid, None)

        elif res.get("status") == "2fa":
            msg = await bot.send_message(
            uid,
            "🔐 ورود دو مرحله‌ای فعال است. رمز 2FA را ارسال کنید:"
        )
            user_state[uid] = (
            "await_2fa_trial" if trial else "await_2fa_self"
        )
            temp_data[uid]["last_msg_id"] = msg.message_id

        else:
            msg = await bot.send_message(
            uid,
            f"❌ خطا: {res.get('message', 'نامعلوم')}"
        )
            temp_data[uid]["last_msg_id"] = msg.message_id

        return

    # ---------------- مرحله 2FA ----------------
    if state in ["await_2fa_self", "await_2fa_trial"]:

        if block_if_banned(uid, message=message):
            return

        try:
            await bot.delete_message(uid, message.message_id)
        except:
            pass

        prev_msg_id = temp_data.get(uid, {}).get("last_msg_id")
        if prev_msg_id:
            try:
                await bot.delete_message(uid, prev_msg_id)
            except:
                pass

        phone = temp_data.get(uid, {}).get("phone")
        if not phone:
            user_state.pop(uid, None)
            return

        trial = (state == "await_2fa_trial")

        try:
            res = requests.post(
            f"{SITE_URL}/send_2fa",
            json={
                "phone": phone,
                "password": text,
                "trial": trial
            },
            timeout=15
        ).json()
        
        except Exception as e:
            msg = await bot.send_message(
            uid,
            f"❌ خطا در ارسال 2FA: {e}"
        )
            temp_data[uid]["last_msg_id"] = msg.message_id
            return
    
        if res.get("status") == "ok":

            users_col.update_one(
            {"user_id": uid},
            {"$set": {
                "phone": phone,
                "trial_active": trial,
                "trial_used": trial or users_col.find_one(
                    {"user_id": uid}
                ).get("trial_used", False),
                "trial_end": datetime.now(UTC) + timedelta(days=TRIAL_DURATION) if trial else None
            }}
        )
    
            if trial:
                start_trial_expiration(uid)

            msg = await bot.send_message(
            uid,
            f"✅ {'سلف تست' if trial else 'سلف اصلی'} با موفقیت فعال شد"
        )

            temp_data.pop(uid, None)
            user_state.pop(uid, None)

        elif res.get("status") == "2fa":

            msg = await bot.send_message(
            uid,
            "🔐 رمز دو مرحله‌ای اشتباه است، دوباره وارد کنید:"
        )

            temp_data[uid]["last_msg_id"] = msg.message_id

        else:

            msg = bot.send_message(
            uid,
            f"❌ خطا: {res.get('message', 'نامعلوم')}"
        )

            temp_data[uid]["last_msg_id"] = msg.message_id

        return

from bson import ObjectId
from bson.errors import InvalidId


@router.callback_query(F.data.startswith("toggle_session_"))
async def toggle_session(callback: CallbackQuery):

    uid = callback.from_user.id

    # ban check
    if block_if_banned(uid):
        await callback.answer("⛔ شما بن هستید", show_alert=True)
        return

    # extract session id safely
    raw_id = callback.data.replace("toggle_session_", "")

    try:
        session_id = ObjectId(raw_id)
    except InvalidId:
        await callback.answer("❌ شناسه سشن نامعتبر است", show_alert=True)
        return

    # fetch session
    session = sessions_col.find_one({"_id": session_id})

    if not session:
        await callback.answer("❌ سشن پیدا نشد", show_alert=True)
        return

    # toggle power safely
    new_power = "off"
    if session.get("power") != "on":
        new_power = "on"

    # update DB
    sessions_col.update_one(
        {"_id": session_id},
        {"$set": {"power": new_power}}
    )

    # callback feedback
    await callback.answer(f"🔁 وضعیت: {new_power.upper()}")

    # rebuild panel safely
    try:
        await callback.message.edit_text(
            "📱 لیست سشن‌های شما:",
            reply_markup=get_user_sessions_panel(uid)
        )
    except Exception as e:
        # اگر پیام تغییر نکرد یا خطا داشت
        await callback.message.answer(
            "📱 لیست سشن‌های شما:",
            reply_markup=get_user_sessions_panel(uid)
        )



@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy(callback: CallbackQuery):

    target_id = int(callback.data.split("_")[2])

    allowed_admins = [
        admin_id
        for admin_id, _ in admin_messages.get(target_id, [])
    ]

    uid = callback.from_user.id

    if block_if_banned(uid):
        await callback.answer("⛔ شما بن هستید")
        return

    if SUPER_ADMIN not in allowed_admins:
        allowed_admins.append(SUPER_ADMIN)

    if uid not in allowed_admins:
        await callback.answer(
            "❌ اجازه ندارید این خرید را تایید کنید",
            show_alert=True
        )
        return

    if target_id not in temp_data:
        await callback.answer(
            "❌ اطلاعات خرید پیدا نشد",
            show_alert=True
        )
        return

    amount = temp_data[target_id]["buy_amount"]

    users_col.update_one(
        {"user_id": target_id},
        {"$inc": {"coins": amount}}
    )

    for admin_id, msg_id in admin_messages.get(target_id, []):
        try:
            await bot.edit_message_reply_markup(
                chat_id=admin_id,
                message_id=msg_id,
                reply_markup=None
            )
        except:
            pass

    try:
        await bot.send_message(
            target_id,
            f"✅ خرید شما تایید شد.\n💰 {amount} سکه اضافه شد."
        )
    except:
        pass

    target_user = users_col.find_one(
        {"user_id": target_id}
    ) or {}

    send_coin_log(
        f"✅ خرید تایید شد\n"
        f"👤 ادمین: <a href='tg://user?id={uid}'>{callback.from_user.first_name}</a>\n"
        f"👤 کاربر: <a href='tg://user?id={target_id}'>{target_user.get('first_name','کاربر')}</a>\n"
        f"💰 تعداد سکه اضافه شده: {amount}",
        parse_mode="HTML"
    )

    temp_data.pop(target_id, None)
    admin_messages.pop(target_id, None)

    await callback.answer("✅ خرید تایید شد")

@router.callback_query(F.data.startswith("reject_buy_"))
async def reject_buy(callback: CallbackQuery):

    target_id = int(callback.data.split("_")[2])

    allowed_admins = [
        admin_id
        for admin_id, _ in admin_messages.get(target_id, [])
    ]

    uid = callback.from_user.id

    if block_if_banned(uid):
        await callback.answer("⛔ شما بن هستید")
        return

    if SUPER_ADMIN not in allowed_admins:
        allowed_admins.append(SUPER_ADMIN)

    if uid not in allowed_admins:
        await callback.answer(
            "❌ اجازه ندارید این خرید را رد کنید",
            show_alert=True
        )
        return

    temp_data.pop(target_id, None)

    for admin_id, msg_id in admin_messages.get(target_id, []):
        try:
            await bot.edit_message_reply_markup(
                chat_id=admin_id,
                message_id=msg_id,
                reply_markup=None
            )
        except:
            pass

    admin_messages.pop(target_id, None)

    target_user = users_col.find_one(
        {"user_id": target_id}
    ) or {}

    send_coin_log(
        f"❌ خرید رد شد\n"
        f"👤 ادمین: <a href='tg://user?id={uid}'>{callback.from_user.first_name}</a>\n"
        f"👤 کاربر: <a href='tg://user?id={target_id}'>{target_user.get('first_name', 'کاربر')}</a>",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            target_id,
            "❌ درخواست خرید شما رد شد."
        )
    except:
        pass

    await callback.answer("❌ خرید رد شد")
    
    
@router.message(F.photo)
async def handle_receipt(message: Message):
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

    if uid in ADMIN:
        recipients = [SUPER_ADMIN]
    else:
        recipients = ADMIN

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تایید خرید",
                    callback_data=f"confirm_buy_{uid}"
                ),
                InlineKeyboardButton(
                    text="❌ رد خرید",
                    callback_data=f"reject_buy_{uid}"
                )
            ]
        ]
    )

    admin_messages[uid] = []

    for admin in recipients:
        try:
            sent = await bot.send_photo(
                chat_id=admin,
                photo=file_id,
                caption=caption,
                reply_markup=markup
            )

            admin_messages[uid].append(
                (admin, sent.message_id)
            )

        except Exception as e:
            print(e)

    send_coin_log(
        f"🛒 درخواست خرید جدید\n"
        f"👤 کاربر: <a href='tg://user?id={uid}'>{message.from_user.first_name}</a>\n"
        f"💰 تعداد سکه: {coins}\n"
        f"💵 مبلغ: {total:,} تومان",
        parse_mode="HTML"
    )

    await message.answer(
        "⏳ کاربر گرامی، تا تایید ادمین منتظر بمانید."
    )

    user_state.pop(uid, None)

@router.callback_query(F.data == "open_support_menu")
async def open_support_menu(call: CallbackQuery):

    uid = call.from_user.id

    if block_if_banned(uid):
        await call.answer()
        return

    new_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠️ پشتیبانی",
                    url="https://t.me/self_nix_support"
                ),
                InlineKeyboardButton(
                    text="💬 گپ",
                    url="https://t.me/Nix_self_Group"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="selfbot_main_panel"
                )
            ]
        ]
    )

    await call.message.edit_reply_markup(
        reply_markup=new_markup
    )

    await call.answer()










  #===========================  
from flask import Flask, request
import os
import asyncio
import json

app = Flask(__name__)

# ================= GLOBAL LOOP =================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


# ================= HEALTH CHECK =================
@app.route("/")
def home():
    return "🤖 Bot is alive ✅"


# ================= WEBHOOK HANDLER =================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return "bad request", 403

    try:
        data = request.get_data(as_text=True)
        update = Update.model_validate(json.loads(data))

        # مهم: امن‌ترین روش برای Flask + asyncio
        asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, update),
            loop
        )

        return "OK", 200

    except Exception as e:
        print("Webhook error:", e)
        return "error", 500


# ================= SET WEBHOOK =================
async def setup_webhook():
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    webhook_url = f"{base_url}/{TOKEN}"

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_url)


# ================= STARTUP =================
async def on_startup():
    await setup_webhook()


# ================= RUN =================
if __name__ == "__main__":
    # start asyncio setup in same loop
    try:
        asyncio.run(main())
        loop.run_until_complete(on_startup())

    # Flask runs separately (thread-safe now)
        app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
    except KeyboardInterrupt:
        print("⛔ ربات متوقف شد")
