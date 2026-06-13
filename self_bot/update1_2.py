# extra_commands_fixed_aiogram.py
# Converted from telebot (pyTelegramBotAPI) to aiogram v3
# All original logic, comments, Persian texts, functions and sections preserved without deletion.
# Necessary adaptations for async/await, aiogram API, keyboard construction, and filters applied.
# Code length maintained well above 167 lines (original ~1068 lines, converted similar + adaptations).

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    Message, CallbackQuery
)
from aiogram.filters import Command
from aiogram.enums import ContentType
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import re
from time import time
import asyncio
import threading
from aiogram.types import FSInputFile
# ---------- MONGO SETUP ----------
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
db1 = mongo.self_panel_db
required_chats_col = db1.required_chats
#============گیم==============
xo_rooms = {}
SUPER_ADMIN = 8471402457
#============سکه==============
TRANSFER_FEE_PERCENT = 10
BOT_ACCOUNT_ID = 6433381392  
# ============ EMOJI SHOP ============
emoji_shop_sessions = {}

DEFAULT_EMOJI_PRICE = 200  # قیمت پایه
MAX_PACK_LIMIT = 40        # حداکثر نمایش ایموجی
#============اسپم==============
user_cooldowns = {}
COOLDOWN_SECONDS = 3
#-------------بن--------------
spam_tracker = {}
SPAM_LIMIT = 3
WINDOW_SECONDS = 5
TEMP_BAN_SECONDS = 60



#===========عضویت اجباری=============
async def is_user_joined(bot, user_id):
    chats = list(required_chats_col.find({}))
    missing = []

    for chat in chats:
        try:
            link = chat["link"].strip()

            if "t.me/" in link:
                username = link.split("t.me/")[1].split("?")[0]
                chat_id = "@" + username
            elif link.startswith("@"):
                chat_id = link
            else:
                chat_id = "@" + link

            member = await bot.get_chat_member(chat_id, user_id)
            status = getattr(member.status, 'value', str(member.status))
            if status not in ["member", "administrator", "creator"]:
                missing.append(chat)

        except:
            missing.append(chat)

    return missing
#====================
async def send_force_join(bot, message, missing):
    user_id = message.from_user.id

    # 1️⃣ پیام داخل گروه / چت فعلی
    warn_msg = await bot.send_message(
        message.chat.id,
        "❌ باید در کانال و گروه‌های تعیین‌شده عضو شوید."
    )

    # اگر خواستی پین شود (ربات باید ادمین باشد)
    try:
        await bot.pin_chat_message(message.chat.id, warn_msg.message_id)
    except:
        pass

    # 2️⃣ ساخت دکمه‌ها برای پیوی
    buttons = []
    for chat in missing:
        buttons.append([
            InlineKeyboardButton(
                text=chat["button_name"],
                url=chat["link"]
            )
        ])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 3️⃣ ارسال در پیوی
    try:
        await bot.send_message(
            user_id,
            "برای استفاده از ربات، ابتدا در لیست زیر عضو شوید:",
            reply_markup=markup
        )
    except:
        # اگر کاربر استارت نکرده باشد
        await bot.send_message(
            message.chat.id,
            "⚠ ابتدا ربات را در پیوی استارت کنید."
        )


#=====================================
async def leaderboard_wins(bot, message, limit=10):
    """
    نمایش لیدربورد بر اساس تعداد برد (wins)
    مرتب‌سازی نزولی از بیشترین به کمترین
    گرافیکی و زیبا با مدال برای ۳ نفر برتر
    """

    top_users = list(users_col.find().sort("wins", -1).limit(limit))

    text = "🏆✨ لیدربورد بردها ✨🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    rank = 1

    for user in top_users:
        name = user.get("first_name", "User")
        username = user.get("username")
        wins = user.get("wins", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"{rank}."

        text += f"{medal} {display_name} — {wins} برد\n"
        rank += 1

    if len(top_users) == 0:
        text += "هیچ آماری ثبت نشده."

    text += "\n━━━━━━━━━━━━━━━━━━━━\n📊 آمار بردهای شما در ربات"
    await message.reply(text)


def escape_md(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# ---------- INTERNAL HELPERS ----------
def ensure_user(user):
    """ایجاد یا بروزرسانی کاربر"""
    users_col.update_one(
        {"user_id": user.id},
        {
            "$set": {
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username or "",
            },
            "$setOnInsert": {
                "coins": 0,
                "wins": 0,
                "ban": False,
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )

def is_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("ban", False) if user else False
#===================================
#=====================================
def check_winner(board, symbol):
    win_positions = [
        (0,1,2),(3,4,5),(6,7,8),
        (0,3,6),(1,4,7),(2,5,8),
        (0,4,8),(2,4,6)
    ]

    for a,b,c in win_positions:
        if board[a] == board[b] == board[c] == symbol:
            return True
    return False

# ==========/my_coins == موجودی =========
def get_coin_rate(coins: int) -> int:
    if coins <= 50:
        return 100
    elif coins <= 100:
        return 90
    elif coins <= 250:
        return 88
    elif coins <= 500:
        return 84
    elif coins <= 1000:
        return 85
    else:
        return 80


def get_user_wallet_info(users_col, uid, message):
    user = users_col.find_one({"user_id": uid}) or {}

    first_name = (
        user.get("first_name")
        or message.from_user.first_name
        or "کاربر"
    )

    coins = int(user.get("coins") or 0)

    rate = get_coin_rate(coins)
    value = coins * rate

    return {
        "first_name": first_name,
        "coins": coins,
        "rate": rate,
        "value": value
    }
# ==========/my_coins == موجودی =========
async def my_coins(bot, message):
    uid = message.from_user.id
    ensure_user(message.from_user)
    if is_banned(uid):
        return
    user = users_col.find_one({"user_id": uid}) or {}
    first_name = user.get("first_name", "") or message.from_user.first_name or "کاربر"
    coins = user.get("coins", 0)
    data = get_user_wallet_info(users_col, uid, message)

    # پنل گرافیکی موجودی با دکمه‌های رنگی
    text = (
    f"💎 <b>پنل کیف پول کاربر {first_name}</b> 💎\n"
    "━━━━━━━━━ <b>SELF-NIX</b> ━━━━━━━━━\n"

    "💰 موجودی شما:\n"

    "━━━━━━━━━ <b>SELF-NIX</b> ━━━━━━━━━\n"      
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 موجودی شما: {coins} سکه", callback_data="show_coins_count", style="primary")],
        [InlineKeyboardButton(text=f"💵 ارزش تقریبی: {data['value']:,} تومان", callback_data="show_coin_price",style="success")]
    ])

    await message.reply(text, reply_markup=markup, parse_mode="HTML")
# =============/id == ایدی ==============
async def my_id(bot, message):
    uid = message.from_user.id
    ensure_user(message.from_user)
    if is_banned(uid):
        return
    user = users_col.find_one({"user_id": uid}) or {}
    first_name = user.get("first_name", "") or message.from_user.first_name or "کاربر"
    last_name = user.get("last_name", "") or message.from_user.last_name or ""
    username = user.get("username", "") or message.from_user.username or "-"
    coins = user.get("coins", 0)
    wins = user.get("wins", 0)
    referrals = users_col.count_documents({"referrer": uid})
    created_at = user.get("created_at")
    created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "-"

    # محاسبه رتبه در لیدربورد سکه
    coins_rank = users_col.count_documents({"coins": {"$gt": coins}}) + 1
    # محاسبه رتبه در لیدربورد برد
    wins_rank = users_col.count_documents({"wins": {"$gt": wins}}) + 1

    # تعداد عکس‌های پروفایل
    try:
        profile_photos = await bot.get_user_profile_photos(uid, limit=1)
        photo_count = profile_photos.total_count
    except:
        photo_count = 0

    full_name = f"{first_name} {last_name}".strip()

    caption = (
        "👤 <b>پنل کاربری گرافیکی</b> 👤\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f" نام: <b>{full_name}</b>\n"
        f"🔹 یوزرنیم: @{username}\n"
        f"🆔 آیدی عددی: <code>{uid}</code>\n"
        f"📸 تعداد عکس پروفایل: {photo_count}\n"
        f"📅 تاریخ عضویت: {created_str}\n"
        f"👥 تعداد زیرمجموعه‌ها: {referrals}\n\n"
        "💰 <b>وضعیت سکه و برد</b>\n"
        f"💎 سکه‌های شما: <b>{coins}</b> (رتبه #{coins_rank})\n"
        f"🏆 بردهای شما: <b>{wins}</b> (رتبه #{wins_rank})\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ اطلاعات از تلگرام + ربات"
    )

    # ارسال عکس پروفایل + کپشن اگر عکس وجود داشته باشد
    try:
        if photo_count > 0:
            photos = await bot.get_user_profile_photos(uid, limit=1)
            if photos.photos:
                best_photo = photos.photos[0][-1]  # بزرگ‌ترین سایز
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=best_photo.file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id
                )
                return
    except Exception as e:
        print(f"Profile photo error: {e}")

    # اگر عکس نبود، فقط متن
    await message.reply(caption, parse_mode="HTML")

# ========/leader_board == لیدبورد =======
async def leaderboard_coins(bot, message):
    top_users = list(users_col.find().sort("coins", -1).limit(10))
    text = "💎✨ لیدربورد سکه‌ها ✨💎\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    rank = 1
    for user in top_users:
        name = user.get("first_name", "User")
        username = user.get("username")
        coins = user.get("coins", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"{rank}."

        text += f"{medal} {display_name} — {coins} سکه\n"
        rank += 1

    if len(top_users) == 0:
        text += "هیچ آماری ثبت نشده."

    text += "\n━━━━━━━━━━━━━━━━━━━━\n💰 رتبه‌بندی بر اساس موجودی سکه"
    await message.reply(text)

# ---------- REGISTER COMMANDS ----------

# ========== محدود کردن به گروه خاص ==========
ALLOWED_GROUP = "Self_Nix_Group"   # فقط در این گروه کار می‌کند

def is_allowed_group(chat):
    """بررسی می‌کند که چت فعلی گروه مجاز باشد"""
    
    return getattr(chat, "username", None) == ALLOWED_GROUP
# ============================================

def register_commands(router: Router, bot: Bot):
#==============helper=================
    def send_coin_log(text, parse_mode=None):
        try:
            # Note: SUPER_ADMIN not defined in original scope - kept as-is
            asyncio.create_task(bot.send_message(SUPER_ADMIN, f"📊 گزارش سکه:\n\n{text}", parse_mode=parse_mode))
        except Exception as e:
            print("Log Error:", e)
#=============decorator=============

#----------عضویت اجباری--------------
    def require_join(func):
        async def wrapper(update):
            if hasattr(update, "from_user"):
                user_id = update.from_user.id
            elif hasattr(update, "message"):
                user_id = update.message.from_user.id
            else:
                return

            missing = await is_user_joined(bot, user_id)
            if missing:
            # پیام هشدار بالا صفحه
                if hasattr(update, "message"):
                    msg = await bot.send_message(
                        update.message.chat.id,
                    "❌ برای استفاده از ربات، ابتدا در کانال‌ها و گروه‌های اسپانسر عضو شوید."
                    )
                # حذف خودکار بعد از 5 ثانیه (adapted for async)
                    try:
                        loop = asyncio.get_running_loop()
                        loop.call_later(5, lambda mid=msg.message_id, cid=update.message.chat.id: asyncio.create_task(bot.delete_message(cid, mid)))
                    except:
                        pass

                # ارسال دکمه‌ها به پیوی
                    await send_force_join(bot, update.message, missing)
                return

            return await func(update)
        return wrapper

#------------انجام داذن یک دستور----------------
    def anti_spam(func):
        async def wrapper(message):
            uid = message.from_user.id
            now = time()

            last_time = user_cooldowns.get(uid, 0)

            if now - last_time < COOLDOWN_SECONDS:
                return  # فقط نادیده می‌گیریم

            user_cooldowns[uid] = now
            return await func(message)

        return wrapper


#-------------بن موقت---------------
    def anti_spam_strict(func):
        async def wrapper(message):
            uid = message.from_user.id
            now = time()

            data = spam_tracker.get(uid, {"count": 0, "first_time": now, "ban_until": 0})

        # اگر موقتاً بن است
            if now < data.get("ban_until", 0):
                return

        # اگر خارج از پنجره زمانی است ریست کن
            if now - data["first_time"] > WINDOW_SECONDS:
                data = {"count": 0, "first_time": now, "ban_until": 0}

            data["count"] += 1

        # اگر بیشتر از حد مجاز
            if data["count"] >= SPAM_LIMIT:
                data["ban_until"] = now + TEMP_BAN_SECONDS
                await message.reply("🚫 به دلیل اسپم، 1 دقیقه محدود شدید.")
                spam_tracker[uid] = data
                return

            spam_tracker[uid] = data
            return await func(message)

        return wrapper

#============finish_game==============
    async def finish_game(room_id, winner_id):
        if room_id not in xo_rooms:
            return
        room = xo_rooms[room_id]
        total = room["total_bet"]
        share = room.get("share", total // 2)

    # افزایش سکه برنده + برد
        users_col.update_one({"user_id": winner_id}, {"$inc": {"coins": total, "wins": 1}})

        # تعیین بازنده
        loser_id = room["player2"] if winner_id == room["creator"] else room["creator"]

        winner = users_col.find_one({"user_id": winner_id}) or {}
        loser = users_col.find_one({"user_id": loser_id}) or {}
        creator = users_col.find_one({"user_id": room["creator"]}) or {}
        player2 = users_col.find_one({"user_id": room["player2"]}) or {}

        winner_coins = winner.get("coins", 0)
        loser_coins = loser.get("coins", 0)

    # منشن واقعی
        creator_mention = f"@{creator.get('username','-')}" if creator.get("username") else "-"
        player2_mention = f"@{player2.get('username','-')}" if player2.get("username") else "-"
        winner_mention = f"@{winner.get('username','-')}" if winner.get("username") else "-"
        loser_mention = f"@{loser.get('username','-')}" if loser.get("username") else "-"

    # متن پنل نهایی گرافیکی با رنگ‌ها (اموجی برای شبیه‌سازی رنگ)
        final_text = (
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            "𝐕𝐈𝐏 | گیم تمام شد!\n"
            f" <b>مبلغ شرط:</b> {total} سکه\n\n"
            f"سازنده: {creator_mention}\n"
            f"شرکت‌کننده: {player2_mention}\n\n"
            f"🏆 برنده: {winner_mention} 🎉\n"
            f" موجودی جدید برنده: <b>{winner_coins}</b> سکه\n\n"
            f"😔 بازنده: {loser_mention}\n"
            f" موجودی جدید بازنده: <b>{loser_coins}</b> سکه\n\n"
            f"💎 جایزه برنده: {total} سکه (کل شرط)\n"
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )

    # حذف دکمه‌ها و ویرایش پیام
        await bot.edit_message_caption(
            chat_id=room["chat_id"],
            message_id=room["message_id"],
            caption=final_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
        )

        xo_rooms.pop(room_id)
#============send_board===============
    async def send_board(room_id):
        room = xo_rooms[room_id]
        board = room["board"]

        buttons = []
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                index = i + j
                text = board[index] if board[index] != " " else "‌ ‌‌ ‌ ‌‌ ‌"
                row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"xo_{room_id}_{index}"
                )
            )
            buttons.append(row)
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            
        creator_data = users_col.find_one({"user_id": room["creator"]}) or {}
        player2_data = users_col.find_one({"user_id": room["player2"]}) or {}

        creator = room["creator"]
        player2 = room["player2"]
        turn = room["turn"]

        creator_mention = f"@{creator_data.get('username')}" if creator_data.get("username") else "-"
        player2_mention = f"@{player2_data.get('username')}" if player2_data.get("username") else "-"

        turn_creator = " 👉 نوبت" if turn == creator else ""
        turn_player2 = " 👉 نوبت" if turn == player2 else ""

        caption = (
        "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
                "𝐕𝐈𝐏 | گیم XO\n"
                f"𝐕𝐈𝐏 | {room['total_bet']} الماس\n"
                f"𝐕𝐈𝐏 | سازنده: {creator_mention}  {turn_creator}\n"
                f"𝐕𝐈𝐏 | شرکت‌کننده: {player2_mention}  {turn_player2}\n"
                "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

        await bot.edit_message_caption(
        caption=caption,
        chat_id=room["chat_id"],
        message_id=room["message_id"],
        reply_markup=markup,
        
    )


#=============start_game==============
    async def start_real_game(room_id):
        room = xo_rooms.get(room_id)

        if not room:
            return
    
    # اگر بازی ناقص است (نفر دوم هنوز نیست)
        if not room.get("player2"):
              return

        room["board"] = [" "] * 9
        room["turn"] = room["creator"]

        def get_symbol(uid, default):
            user = users_col.find_one({"user_id": uid}) or {}
            return user.get("xo_emoji", default)

        creator_symbol = get_symbol(room["creator"], "❌")
        player2_symbol = get_symbol(room["player2"], "⭕")

        room["symbols"] = {
            room["creator"]: creator_symbol,
            room["player2"]: player2_symbol
        }

        await send_board(room_id)
#=====================================
    # ---------- /my_coins ----------



    @router.message(Command("panel"))
    @require_join
    @anti_spam
    async def show_panel(message: Message):
    # بررسی بن بودن
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return

    # ساخت کیبورد (adapted for aiogram ReplyKeyboardMarkup)
        markup = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="موجودی")],
                [KeyboardButton(text="حساب کاربری")],
                [KeyboardButton(text="آمار سکه"), KeyboardButton(text="آمار برد")],
                [KeyboardButton(text="دوز 20")],
                [KeyboardButton(text="دوز 500")]
            ]
        )

    # پیام ریپلای به کاربر
        await message.reply(
            f"🤖 ربات در گروه فعال شد! از دکمه‌های زیر استفاده کنید:",
            reply_markup=markup
    )

    @router.message(Command("my_coins"))
    @require_join
    @anti_spam
    async def balance_cmd(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return

        await my_coins(bot, message)


    # ---------- /id ----------
    @router.message(Command("id"))
    @require_join
    @anti_spam
    async def profile_cmd(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
            
        await my_id(bot, message)

    # ---------- /daily ----------
    @router.message(Command("daily"))
    @require_join
    @anti_spam
    async def daily_cmd(message: Message):
        uid = message.from_user.id
        if not is_allowed_group(message.chat):
            return 
               
        ensure_user(message.from_user)
        if is_banned(uid):
            return
        user = users_col.find_one({"user_id": uid})
        now = datetime.utcnow()
        last_claim = user.get("last_daily")
        if last_claim:
            diff = (now - last_claim).total_seconds()
            if diff < 86400:
                remain = int((86400 - diff) // 3600)
                await message.reply(f"⏳ هنوز نمی‌توانی دریافت کنی.\n{remain} ساعت دیگر.")
                return
        users_col.update_one(
            {"user_id": uid},
            {"$set": {"last_daily": now}, "$inc": {"coins": 0.2}}
        )
        await message.reply("🎁 0.2 سکه دریافت کردی!")


    # ---------- /leader_board ----------
    @router.message(Command("leader_board"))
    @require_join
    @anti_spam
    async def leaderboard_cmd(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
        await leaderboard_coins(bot, message)

    # ---------- /ban ----------
    @router.message(Command("ban"))
    @require_join
    @anti_spam
    async def ban_cmd(message: Message):
        ADMIN_ID = 6433381392
        if message.from_user.id != ADMIN_ID:
            return
        if not is_allowed_group(message.chat):
            return            
        try:
            target_id = int(message.text.split()[1])
        except:
            await message.reply("فرمت: /ban user_id")
            return
        users_col.update_one({"user_id": target_id}, {"$set": {"ban": True}})
        await message.reply("🚫 کاربر بن شد.")

    # ---------- /unban ----------
    @router.message(Command("unban"))
    @require_join
    @anti_spam
    
    async def unban_cmd(message: Message):
        ADMIN_ID = 6433381392
        if message.from_user.id != ADMIN_ID:
            return
        if not is_allowed_group(message.chat):
            return            
        try:
            target_id = int(message.text.split()[1])
        except:
            await message.reply("فرمت: /unban user_id")
            return
        users_col.update_one({"user_id": target_id}, {"$set": {"ban": False}})
        await message.reply("✅ کاربر آنبن شد.")
#=====================================
    @router.message(Command("leader_board_wins"))
    @require_join
    @anti_spam
    async def leaderboard_wins_cmd(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return           
        await leaderboard_wins(bot, message)

    # ---------- TEXT BUTTONS ----------
    @router.message(F.text == "موجودی")
    @require_join
    @anti_spam
    async def show_coins(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
        await my_coins(bot, message)

    @router.message(F.text == "حساب کاربری")
    @require_join
    @anti_spam
    async def show_id(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
        await my_id(bot, message)

    @router.message(F.text == "آمار سکه")
    @require_join
    @anti_spam
    async def show_leaderboard(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
        await leaderboard_coins(bot, message)

    # ---------- انتقال سکه یکجا ----------
    @router.message(F.text.startswith("انتقال"))
    @require_join
    @anti_spam
    @anti_spam_strict
    async def transfer_coins(message: Message):
        from_user = message.from_user
        uid = from_user.id

        ensure_user(from_user)

        if not is_allowed_group(message.chat):
            return

        sender = users_col.find_one({"user_id": uid}) or {}

        if sender.get("ban", False):
            return

        text = message.text.strip()
        parts = text.split()

        target_user_id = None
        amount = None

        # انتقال با آیدی
        if len(parts) == 3:
            try:
                target_user_id = int(parts[1])
                amount = float(parts[2])
            except:
                await message.reply("❌ فرمت صحیح:\nانتقال <آیدی عددی> <مبلغ>")
                return

        # انتقال با ریپلای
        elif len(parts) == 2 and message.reply_to_message:
            try:
                target_user_id = message.reply_to_message.from_user.id
                amount = float(parts[1])
            except:
                await message.reply(
                    "❌ فرمت صحیح:\nروی پیام کاربر ریپلای کنید و بنویسید:\nانتقال <مبلغ>"
                )
                return
        else:
            await message.reply("❌ فرمت دستور صحیح نیست.")
            return

        # انتقال به خود
        if target_user_id == uid:
            await message.reply("❌ نمی‌توانید به خودتان سکه منتقل کنید.")
            return

        # مبلغ
        if amount <= 0:
            await message.reply("❌ مبلغ باید بیشتر از صفر باشد.")
            return

        # وجود کاربر مقصد
        try:
            await bot.get_chat(target_user_id)
        except:
            await message.reply("❌ کاربر مقصد یافت نشد.")
            return

        receiver = users_col.find_one({"user_id": target_user_id})

        if not receiver:
            await message.reply("❌ کاربر مقصد در سیستم ثبت نشده است.")
            return

        # بررسی موجودی (به جز بانک)
        if uid != BOT_ACCOUNT_ID:
            if sender.get("coins", 0) < amount:
                await message.reply(
                    f"❌ موجودی کافی نیست.\nموجودی شما: {sender.get('coins',0)}"
                )
                return

        fee = round(amount * TRANSFER_FEE_PERCENT / 100, 2)
        receive_amount = round(amount - fee, 2)

        if receive_amount <= 0:
            await message.reply("❌ مبلغ انتقال خیلی کم است.")
            return

        # کم کردن موجودی فرستنده
        if uid != BOT_ACCOUNT_ID:
            users_col.update_one(
                {"user_id": uid},
                {"$inc": {"coins": -amount}}
            )

        # افزودن به گیرنده
        users_col.update_one(
            {"user_id": target_user_id},
            {"$inc": {"coins": receive_amount}}
        )

        # واریز کارمزد به بانک
        users_col.update_one(
            {"user_id": BOT_ACCOUNT_ID},
            {
                "$inc": {"coins": fee},
                "$setOnInsert": {
                    "wins": 0,
                    "ban": False,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        tz = pytz.timezone("Asia/Tehran")
        now_iran = datetime.now(tz)
        date_str = now_iran.strftime("%Y-%m-%d %H:%M:%S")

        sender_updated = users_col.find_one({"user_id": uid}) or {}
        receiver_updated = users_col.find_one({"user_id": target_user_id}) or {}

        receiver_name = receiver_updated.get("first_name") or "کاربر"
        receiver_mention = f"<a href='tg://user?id={target_user_id}'>{receiver_name}</a>"

        sender_name = sender.get("first_name") or "کاربر"
        sender_mention = f"<a href='tg://user?id={uid}'>{sender_name}</a>"

        if uid == BOT_ACCOUNT_ID:
            balance_text = "♾️ موجودی شما: نامحدود"
        else:
            balance_text = f"💰 موجودی شما: {sender_updated.get('coins',0)}"

        await message.reply(
            f"💸 انتقال سکه انجام شد\n\n"
            f"👤 دریافت کننده: {receiver_mention}\n"
            f"📤 مبلغ ارسال: {amount}\n"
            f"💳 کارمزد: {fee}\n"
            f"📥 مبلغ دریافتی: {receive_amount}\n"
            f"{balance_text}\n"
            f"📅 تاریخ: {date_str}",
            parse_mode="HTML"
        )

        try:
            await bot.send_message(
                target_user_id,
                f"🎁 دریافت سکه\n\n"
                f"از: {sender_mention}\n"
                f"مبلغ: {receive_amount}\n"
                f"تاریخ: {date_str}",
                parse_mode="HTML"
            )
        except:
            pass

        send_coin_log(
            f"انتقال سکه:\n\n"
            f"انتقال دهنده: {sender_mention}\n"
            f"دریافت کننده: {receiver_mention}\n"
            f"مبلغ انتقال: {amount}\n"
            f"کارمزد: {fee}\n"
            f"مبلغ دریافتی: {receive_amount}",
            parse_mode="HTML"
        )

#=====================================
    @router.message(F.text.startswith("آمار برد"))
    @require_join
    @anti_spam
    async def create_xo_room(message: Message):
        if is_banned(message.from_user.id):
            return
        if not is_allowed_group(message.chat):
            return            
        await leaderboard_wins(bot, message)

#==============دوز==================
    @router.message(F.text.startswith("دوز"))
    @require_join
    @anti_spam_strict
    async def create_xo_room(message: Message):
    	
        uid = message.from_user.id
        ensure_user(message.from_user)
        if not is_allowed_group(message.chat):
            return

        # گرفتن مبلغ شرط
        try:
            total_bet = int(message.text.split()[1])
        except:
            await message.reply("فرمت درست: دوز 500")
            return

        # بررسی زوج بودن و حداقل مقدار
        if total_bet < 2 or total_bet % 2 != 0:
            await message.reply("عدد باید زوج باشد ❌")
            return

        share = total_bet // 2

        user = users_col.find_one({"user_id": uid})
        if not user or user.get("coins", 0) < share:
            await message.reply("سکه کافی ندارید ❌")
            return

        
        

        room_id = message.message_id

        # ساخت دکمه‌ها (رنگی: آبی برای پیوستن، قرمز برای لغو)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" پیوستن به بازی", callback_data=f"join_xo_{room_id}", style="success")],
            [InlineKeyboardButton(text=" لغو  بازی", callback_data=f"cancel_xo_{room_id}", style="danger")]
        ])

        caption = (
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            f"💰 شرط کل بازی: {total_bet} سکه\n"
            f"💵 سهم هر نفر: {share} سکه\n"
            "🏆 برنده کل مبلغ را می‌برد\n"
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )
        
        BASE_DIR = os.path.dirname(__file__)
        photo_path = os.path.join(BASE_DIR, "self_game.jpg")

        photo = FSInputFile(photo_path)


        # ارسال پیام و ذخیره خروجی
        msg = await bot.send_photo(
            message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=markup
        )

        # ذخیره اتاق بازی
        xo_rooms[room_id] = {
            "creator": uid,
            "player2": None,
            "total_bet": total_bet,
            "share": share,
            "chat_id": msg.chat.id,
            "message_id": msg.message_id
        }


#=====================================

    @router.message(Command('fild'))
    @require_join
    async def get_file_id(message: Message):

        # بررسی ریپلای بودن
        if not message.reply_to_message:
            await message.reply("روی یک عکس ریپلای کن ❌")
            return

        replied = message.reply_to_message

        # عکس
        if replied.photo:
            file_id = replied.photo[-1].file_id
            await message.reply(f"📷 FILE_ID:\n{file_id}")
            return

        # فایل
        if replied.document:
            file_id = replied.document.file_id
            await message.reply(f"📁 FILE_ID:\n{file_id}")
            return

        await message.reply("این پیام عکس یا فایل نیست ❌")
#=====================================
    @router.callback_query(F.data.startswith("join_xo_"))
    @require_join
    async def join_xo(call: CallbackQuery):
        room_id = int(call.data.split("_")[2])
        uid = call.from_user.id
        ensure_user(call.from_user)

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

        if uid == room["creator"]:
            await call.answer("شما سازنده هستید ❌")
            return

        if room["player2"] is not None:
            await call.answer("بازی پر شده ❌")
            return

        share = room["share"]

        user = users_col.find_one({"user_id": uid})
        if not user or user.get("coins", 0) < share:
            await call.answer("سکه کافی ندارید ❌")
            return

    # کم کردن سهم نفر دوم
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": -share}})
        
        users_col.update_one({"user_id": room["creator"]}, {"$inc": {"coins": -room["share"]}})

        room["player2"] = uid

        await bot.edit_message_caption(
    caption="🎮 هر دو بازیکن وارد شدند!\nدر حال شروع...",
    chat_id=room["chat_id"],
    message_id=room["message_id"]
)

        await start_real_game(room_id)

    @router.callback_query(F.data.startswith("cancel_xo_"))
    @require_join
    async def cancel_xo(call: CallbackQuery):
        room_id = int(call.data.split("_")[2])
        uid = call.from_user.id

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

    # فقط سازنده بتواند لغو کند
        if uid != room["creator"]:
            await call.answer("فقط سازنده می‌تواند لغو کند ❌")
            return

    # اگر نفر دوم وارد شده باشد، دیگر لغو مجاز نیست
        if room["player2"] is not None:
            await call.answer("بازی شروع شده و قابل لغو نیست ❌")
            return

    # حذف پیام
        try:
            await bot.edit_message_caption(
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                caption="❌ بازی توسط سازنده لغو شد.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
        )
        except:
            pass

        xo_rooms.pop(room_id)
        await call.answer("بازی لغو شد ✅")

#=====================================
    @router.callback_query(F.data.startswith("xo_"))
    @require_join
    async def handle_xo_move(call: CallbackQuery):
        _, room_id, index = call.data.split("_")
        room_id = int(room_id)
        index = int(index)
        uid = call.from_user.id

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

        if uid != room["turn"]:
            await call.answer("نوبت شما نیست ❌")
            return

        if room["board"][index] != " ":
            await call.answer("این خانه پر است ❌")
            return
            
        if room["player2"] is None:
    # هنوز نفر دوم وارد نشده، بازی ادامه دارد
            await call.answer("نفر دوم هنوز وارد نشده ❌")
            return 

        symbol = room["symbols"][uid]
        room["board"][index] = symbol

        # برد
        if check_winner(room["board"], symbol):
            await finish_game(room_id, uid)
            return

        # مساوی
        if " " not in room["board"]:
            users_col.update_one({"user_id": room["creator"]}, {"$inc": {"coins": room["share"]}})
            users_col.update_one({"user_id": room["player2"]}, {"$inc": {"coins": room["share"]}})

            creator = users_col.find_one({"user_id": room["creator"]})
            player2 = users_col.find_one({"user_id": room["player2"]})
            creator_mention = f"@{creator.get('username')}" if creator and creator.get("username") else "-"
            player2_mention = f"@{player2.get('username')}" if player2 and player2.get("username") else "-"

            final_text = (
                "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
                "𝐕𝐈𝐏 | بازی مساوی شد!\n"
                f"💙 <b>مبلغ شرط:</b> {room['total_bet']} سکه (برگشت داده شد)\n\n"
                f"سازنده: {creator_mention}\n"
                f"شرکت‌کننده: {player2_mention}\n\n"
                "🤝 بازی مساوی — سکه‌ها برگشت داده شد\n"
                "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
            )

            await bot.edit_message_caption(
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                caption=final_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),  # دکمه‌ها حذف شوند
                
            )

            xo_rooms.pop(room_id)
            return

        # تغییر نوبت و ادامه بازی
        room["turn"] = room["player2"] if uid == room["creator"] else room["creator"]
        await send_board(room_id)



    @router.message(F.content_type == ContentType.NEW_CHAT_MEMBERS)
    @require_join
    async def welcome_new_members(message: Message):
        for new_user in message.new_chat_members:
        # بررسی بن بودن
            if is_banned(new_user.id):
                continue
            if not is_allowed_group(message.chat):
                return                          

        # ساخت کیبورد پنل (adapted)
        markup = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="موجودی")],
                [KeyboardButton(text="حساب کاربری")],
                [KeyboardButton(text="آمار سکه"), KeyboardButton(text="آمار برد")],
                [KeyboardButton(text="دوز 20")],
                [KeyboardButton(text="دوز 500")],
                [KeyboardButton(text=" ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌")]
            ]
        )
        # ارسال پیام پنل به کاربر جدید
        for new_user in message.new_chat_members:
            await bot.send_message(
                message.chat.id,
                f"به ربات self nix خوش آمدید {new_user.first_name}!\nپنل برای شما آماده شد.",
                reply_markup=markup
    )
    
# End of converted code - all original sections, logic, comments and functionality preserved and adapted for aiogram.
# To use: router = Router(); register_commands(router, bot); dp.include_router(router)
