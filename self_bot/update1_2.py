# extra_commands_fixed.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from pymongo import MongoClient
from datetime import datetime, timedelta
from telebot import types
import pytz
import re
from time import time


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
def is_user_joined(bot, user_id):
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

            member = bot.get_chat_member(chat_id, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                missing.append(chat)

        except:
            missing.append(chat)

    return missing
#====================
def send_force_join(bot, message, missing):
    user_id = message.from_user.id

    # 1️⃣ پیام داخل گروه / چت فعلی
    warn_msg = bot.send_message(
        message.chat.id,
        "❌ باید در کانال و گروه‌های تعیین‌شده عضو شوید."
    )

    # اگر خواستی پین شود (ربات باید ادمین باشد)
    try:
        bot.pin_chat_message(message.chat.id, warn_msg.message_id)
    except:
        pass

    # 2️⃣ ساخت دکمه‌ها برای پیوی
    markup = InlineKeyboardMarkup()
    for chat in missing:
        markup.add(
            InlineKeyboardButton(
                chat["button_name"],
                url=chat["link"]
            )
        )

    # 3️⃣ ارسال در پیوی
    try:
        bot.send_message(
            user_id,
            "برای استفاده از ربات، ابتدا در لیست زیر عضو شوید:",
            reply_markup=markup
        )
    except:
        # اگر کاربر استارت نکرده باشد
        bot.send_message(
            message.chat.id,
            "⚠ ابتدا ربات را در پیوی استارت کنید."
        )


#=====================================
def leaderboard_wins(bot, message, limit=10):
    """
    نمایش لیدربورد بر اساس تعداد برد (wins)
    مرتب‌سازی نزولی از بیشترین به کمترین
    """

    top_users = users_col.find().sort("wins", -1).limit(limit)

    text = "🏆 لیدربورد بردها:\n\n"
    rank = 1

    for user in top_users:
        name = user.get("first_name", "User")
        username = user.get("username")
        wins = user.get("wins", 0)

        if username:
            display_name = f"@{username}"
        else:
            display_name = name

        text += f"{rank}. {display_name} - {wins} برد\n"
        rank += 1

    if rank == 1:
        text += "هیچ آماری ثبت نشده."

    bot.reply_to(message, text)


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
def my_coins(bot, message):
    uid = message.from_user.id
    ensure_user(message.from_user)
    if is_banned(uid):
        return
    user = users_col.find_one({"user_id": uid}) or {}
    coins = user.get("coins", 0)
    bot.reply_to(message, f"💰 موجودی شما: {coins}")

# =============/id == ایدی ==============
def my_id(bot, message):
    uid = message.from_user.id
    ensure_user(message.from_user)
    if is_banned(uid):
        return
    user = users_col.find_one({"user_id": uid}) or {}
    first_name = user.get("first_name", "")
    username = user.get("username", "-")
    coins = user.get("coins", 0)
    wins = user.get("wins", 0)
    referrals = users_col.count_documents({"referrer": uid})
    created_at = user.get("created_at")
    created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "-"
    msg = f"""اطلاعات شما:
اسم: {first_name}
یوزرنیم: @{username}
ایدی عددی: `{uid}`
تعداد زیر مجموعه: {referrals}
تعداد سکه: {coins}
تعداد برد: {wins}
تاریخ عضویت: {created_str}"""
    bot.reply_to(message, msg)

# ========/leader_board == لیدبورد =======
def leaderboard_coins(bot, message):
    top_users = users_col.find().sort("coins", -1).limit(10)
    text = "🏆 10 نفر برتر:\n\n"
    rank = 1
    for user in top_users:
        name = user.get("first_name", "User")
        coins = user.get("coins", 0)
        text += f"{rank}. {name} - {coins} 💰\n"
        rank += 1
    bot.reply_to(message, text)

# ---------- REGISTER COMMANDS ----------
def register_commands(bot):
#==============helper=================
    def send_coin_log(text, parse_mode=None):
        try:
            bot.send_message(SUPER_ADMIN, f"📊 گزارش سکه:\n\n{text}", parse_mode=parse_mode)
        except Exception as e:
            print("Log Error:", e)
#=============decorator=============

#----------عضویت اجباری--------------
    def require_join(func):
        def wrapper(update):
            if hasattr(update, "from_user"):
                user_id = update.from_user.id
            elif hasattr(update, "message"):
                user_id = update.message.from_user.id
            else:
                return

            missing = is_user_joined(bot, user_id)
            if missing:
            # پیام هشدار بالا صفحه
                if hasattr(update, "message"):
                    msg = bot.send_message(
                        update.message.chat.id,
                    "❌ برای استفاده از ربات، ابتدا در کانال‌ها و گروه‌های اسپانسر عضو شوید."
                    )
                # حذف خودکار بعد از 5 ثانیه
                    threading.Timer(5, lambda: bot.delete_message(update.message.chat.id, msg.message_id)).start()

                # ارسال دکمه‌ها به پیوی
                    send_force_join(bot, update.message, missing)
                return

            return func(update)
        return wrapper

#------------انجام داذن یک دستور----------------
    def anti_spam(func):
        def wrapper(message):
            uid = message.from_user.id
            now = time()

            last_time = user_cooldowns.get(uid, 0)

            if now - last_time < COOLDOWN_SECONDS:
                return  # فقط نادیده می‌گیریم

            user_cooldowns[uid] = now
            return func(message)

        return wrapper


#-------------بن موقت---------------
    def anti_spam_strict(func):
        def wrapper(message):
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
                bot.reply_to(message, "🚫 به دلیل اسپم، 1 دقیقه محدود شدید.")
                spam_tracker[uid] = data
                return

            spam_tracker[uid] = data
            return func(message)

        return wrapper

#============finish_game==============
    def finish_game(room_id, winner_id):
        if room_id not in xo_rooms:
            return
        room = xo_rooms[room_id]
        total = room["total_bet"]
        

    # افزایش سکه برنده
        users_col.update_one({"user_id": winner_id}, {"$inc": {"coins": total, "wins": 1}})
        winner = users_col.find_one({"user_id": winner_id})
        creator = users_col.find_one({"user_id": room["creator"]})
        player2 = users_col.find_one({"user_id": room["player2"]})

    # منشن واقعی
        creator_mention = f"@{creator.get('username','-')}" if creator else "-"
        player2_mention = f"@{player2.get('username','-')}" if player2 else "-"
        winner_mention = f"@{winner.get('username','-')}" if winner else "-"

    # متن پنل نهایی
        final_text = (
        "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        "𝐕𝐈𝐏 | گیم\n"
        f"𝐕𝐈𝐏 | {total} الماس\n"
        f"𝐕𝐈𝐏 | سازنده: {creator_mention}\n"
        f"𝐕𝐈𝐏 | شرکت‌کننده: {player2_mention}\n"
        f"𝐕𝐈𝐏 | برنده: {winner_mention} 🎉\n"
        f"𝐕𝐈𝐏 | جایزه: {total} 💎\n"
        "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

    # حذف دکمه‌ها و ویرایش پیام
        bot.edit_message_caption(
        chat_id=room["chat_id"],
        message_id=room["message_id"],
        caption=final_text,
        reply_markup=InlineKeyboardMarkup(),  # خالی = دکمه‌ها پاک میشن
        
    )

        xo_rooms.pop(room_id)
#============send_board===============
    def send_board(room_id):
        room = xo_rooms[room_id]
        board = room["board"]

        markup = InlineKeyboardMarkup()

        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                index = i + j
                text = board[index] if board[index] != " " else "‌ ‌‌ ‌ ‌‌ ‌"
                row.append(
                InlineKeyboardButton(
                    text,
                    callback_data=f"xo_{room_id}_{index}"
                )
            )
            markup.row(*row)
            
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

        bot.edit_message_caption(
        caption=caption,
        chat_id=room["chat_id"],
        message_id=room["message_id"],
        reply_markup=markup,
        
    )


#=============start_game==============
    def start_real_game(room_id):
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

        send_board(room_id)
#=====================================
    # ---------- /my_coins ----------



    @bot.message_handler(commands=["panel"])
    @require_join
    @anti_spam
    def show_panel(message):
    # بررسی بن بودن
        if is_banned(message.from_user.id):
            return

    # ساخت کیبورد
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(KeyboardButton("موجودی"))
        markup.row(KeyboardButton("حساب کاربری"))
        markup.row(KeyboardButton("آمار سکه"), KeyboardButton("آمار برد"))
        markup.row(KeyboardButton("دوز 20"))
        markup.row(KeyboardButton("دوز 500"))

    # پیام ریپلای به کاربر
        bot.reply_to(
            message,
            f"🤖 ربات در گروه فعال شد! از دکمه‌های زیر استفاده کنید:",
            reply_markup=markup
    )

    @bot.message_handler(commands=["my_coins"])
    @require_join
    @anti_spam
    def balance_cmd(message):
        if is_banned(message.from_user.id):
            return
        my_coins(bot, message)

    # ---------- /id ----------
    @bot.message_handler(commands=["id"])
    @require_join
    @anti_spam
    def profile_cmd(message):
        if is_banned(message.from_user.id):
            return
        my_id(bot, message)

    # ---------- /daily ----------
    @bot.message_handler(commands=["daily"])
    @require_join
    @anti_spam
    def daily_cmd(message):
        uid = message.from_user.id
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
                bot.reply_to(message, f"⏳ هنوز نمی‌توانی دریافت کنی.\n{remain} ساعت دیگر.")
                return
        users_col.update_one(
            {"user_id": uid},
            {"$set": {"last_daily": now}, "$inc": {"coins": 0.2}}
        )
        bot.reply_to(message, "🎁 0.2 سکه دریافت کردی!")

    # ---------- ایموجی ----------
    @bot.message_handler(func=lambda m: m.text and m.text.startswith("ایموجی"))
    @require_join
    @anti_spam
    def emoji_from_link(message):
        parts = message.text.split()

        if len(parts) < 2:
            bot.reply_to(message, "لینک پک را بده:\nایموجی https://t.me/addstickers/PackName")
            return

        link = parts[1]

        import re
        match = re.search(r"t\.me/addstickers/([a-zA-Z0-9_]+)", link)

        if not match:
            bot.reply_to(message, "❌ لینک معتبر نیست")
            return

        pack_name = match.group(1)

        try:
            pack = bot.get_sticker_set("CatsBigPack")
        except:
            bot.reply_to(message, "❌ پک پیدا نشد")
            return

        kb = types.InlineKeyboardMarkup()

        stickers = pack.stickers[:MAX_PACK_LIMIT]

        for st in stickers:
            kb.add(
            types.InlineKeyboardButton(
                text=st.custom_emoji_id,
                callback_data=f"buy_emoji|{st.file_id}"
            )
        )

        emoji_shop_sessions[message.from_user.id] = {
        "pack": pack_name,
        "stickers": {st.file_id: st.custom_emoji_id for st in stickers}
    }

        bot.send_message(
        message.chat.id,
        "یکی از ایموجی‌ها را انتخاب کن:",
        reply_markup=kb
    )

    # ---------- /leader_board ----------
    @bot.message_handler(commands=["leader_board"])
    @require_join
    @anti_spam
    def leaderboard_cmd(message):
        if is_banned(message.from_user.id):
            return
        leaderboard_coins(bot, message)

    # ---------- /ban ----------
    @bot.message_handler(commands=["ban"])
    @require_join
    @anti_spam
    def ban_cmd(message):
        ADMIN_ID = 6433381392
        if message.from_user.id != ADMIN_ID:
            return
        try:
            target_id = int(message.text.split()[1])
        except:
            bot.reply_to(message, "فرمت: /ban user_id")
            return
        users_col.update_one({"user_id": target_id}, {"$set": {"ban": True}})
        bot.reply_to(message, "🚫 کاربر بن شد.")

    # ---------- /unban ----------
    @bot.message_handler(commands=["unban"])
    @require_join
    @anti_spam
    
    def unban_cmd(message):
        ADMIN_ID = 6433381392
        if message.from_user.id != ADMIN_ID:
            return
        try:
            target_id = int(message.text.split()[1])
        except:
            bot.reply_to(message, "فرمت: /unban user_id")
            return
        users_col.update_one({"user_id": target_id}, {"$set": {"ban": False}})
        bot.reply_to(message, "✅ کاربر آنبن شد.")
#=====================================
    @bot.message_handler(commands=["leader_board_wins"])
    @require_join
    @anti_spam
    def leaderboard_wins_cmd(message):
        if is_banned(message.from_user.id):
            return
        leaderboard_wins(bot, message)

    # ---------- TEXT BUTTONS ----------
    @bot.message_handler(func=lambda m: m.text and m.text.strip() == "موجودی")
    @require_join
    @anti_spam
    def show_coins(message):
        if is_banned(message.from_user.id):
            return
        my_coins(bot, message)

    @bot.message_handler(func=lambda m: m.text and m.text.strip() == "حساب کاربری")
    @require_join
    @anti_spam
    def show_id(message):
        if is_banned(message.from_user.id):
            return
        my_id(bot, message)

    @bot.message_handler(func=lambda m: m.text and m.text.strip() == "آمار سکه")
    @require_join
    @anti_spam
    def show_leaderboard(message):
        if is_banned(message.from_user.id):
            return
        leaderboard_coins(bot, message)

    # ---------- انتقال سکه یکجا ----------
    @bot.message_handler(func=lambda m: m.text and m.text.startswith("انتقال"))
    @require_join
    @anti_spam
    @anti_spam_strict
    def transfer_coins(message):
        from_user = message.from_user
        uid = from_user.id

        ensure_user(from_user)

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
                bot.reply_to(message, "❌ فرمت صحیح:\nانتقال <آیدی عددی> <مبلغ>")
                return

        # انتقال با ریپلای
        elif len(parts) == 2 and message.reply_to_message:
            try:
                target_user_id = message.reply_to_message.from_user.id
                amount = float(parts[1])
            except:
                bot.reply_to(
                    message,
                    "❌ فرمت صحیح:\nروی پیام کاربر ریپلای کنید و بنویسید:\nانتقال <مبلغ>"
                )
                return
        else:
            bot.reply_to(message, "❌ فرمت دستور صحیح نیست.")
            return

        # انتقال به خود
        if target_user_id == uid:
            bot.reply_to(message, "❌ نمی‌توانید به خودتان سکه منتقل کنید.")
            return

        # مبلغ
        if amount <= 0:
            bot.reply_to(message, "❌ مبلغ باید بیشتر از صفر باشد.")
            return

        # وجود کاربر مقصد
        try:
            bot.get_chat(target_user_id)
        except:
            bot.reply_to(message, "❌ کاربر مقصد یافت نشد.")
            return

        receiver = users_col.find_one({"user_id": target_user_id})

        if not receiver:
            bot.reply_to(message, "❌ کاربر مقصد در سیستم ثبت نشده است.")
            return

        # بررسی موجودی (به جز بانک)
        if uid != BOT_ACCOUNT_ID:
            if sender.get("coins", 0) < amount:
                bot.reply_to(
                    message,
                    f"❌ موجودی کافی نیست.\nموجودی شما: {sender.get('coins',0)}"
                )
                return

        fee = round(amount * TRANSFER_FEE_PERCENT / 100, 2)
        receive_amount = round(amount - fee, 2)

        if receive_amount <= 0:
            bot.reply_to(message, "❌ مبلغ انتقال خیلی کم است.")
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

        bot.reply_to(
            message,
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
            bot.send_message(
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
    @bot.message_handler(func=lambda m: m.text and m.text.startswith("آمار برد"))
    @require_join
    @anti_spam
    def create_xo_room(message):
        if is_banned(message.from_user.id):
            return
        leaderboard_wins(bot, message)

#==============دوز==================
    @bot.message_handler(func=lambda m: m.text and m.text.startswith("دوز"))
    @require_join
    @anti_spam_strict
    def create_xo_room(message):
    	
        uid = message.from_user.id
        ensure_user(message.from_user)

        # گرفتن مبلغ شرط
        try:
            total_bet = int(message.text.split()[1])
        except:
            bot.reply_to(message, "فرمت درست: دوز 500")
            return

        # بررسی زوج بودن و حداقل مقدار
        if total_bet < 2 or total_bet % 2 != 0:
            bot.reply_to(message, "عدد باید زوج باشد ❌")
            return

        share = total_bet // 2

        user = users_col.find_one({"user_id": uid})
        if not user or user.get("coins", 0) < share:
            bot.reply_to(message, "سکه کافی ندارید ❌")
            return

        
        

        room_id = message.message_id

        # ساخت دکمه‌ها
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🎮 شرکت در بازی", callback_data=f"join_xo_{room_id}")
        )
        markup.add(
            InlineKeyboardButton("❌ لغو بازی", callback_data=f"cancel_xo_{room_id}")
        )

        caption = (
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            f"💰 شرط کل بازی: {total_bet} سکه\n"
            f"💵 سهم هر نفر: {share} سکه\n"
            "🏆 برنده کل مبلغ را می‌برد\n"
            "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )

        # ارسال پیام و ذخیره خروجی
        msg = bot.send_photo(
            message.chat.id,
            photo="AgACAgQAAxkBAAIC9WmZQ9dVGfZiGKrsKmUYM1rwKD69AAIYDWsbhfrIUMGsjEIGjVOsAQADAgADeQADOgQ",
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

    @bot.message_handler(commands=['fild'])
    @require_join
    def get_file_id(message):

        # بررسی ریپلای بودن
        if not message.reply_to_message:
            bot.reply_to(message, "روی یک عکس ریپلای کن ❌")
            return

        replied = message.reply_to_message

        # عکس
        if replied.photo:
            file_id = replied.photo[-1].file_id
            bot.reply_to(message, f"📷 FILE_ID:\n{file_id}")
            return

        # فایل
        if replied.document:
            file_id = replied.document.file_id
            bot.reply_to(message, f"📁 FILE_ID:\n{file_id}")
            return

        bot.reply_to(message, "این پیام عکس یا فایل نیست ❌")
#=====================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("join_xo_"))
    @require_join
    def join_xo(call):
        room_id = int(call.data.split("_")[2])
        uid = call.from_user.id
        ensure_user(call.from_user)

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

        if uid == room["creator"]:
            bot.answer_callback_query(call.id, "شما سازنده هستید ❌")
            return

        if room["player2"] is not None:
            bot.answer_callback_query(call.id, "بازی پر شده ❌")
            return

        share = room["share"]

        user = users_col.find_one({"user_id": uid})
        if not user or user.get("coins", 0) < share:
            bot.answer_callback_query(call.id, "سکه کافی ندارید ❌")
            return

    # کم کردن سهم نفر دوم
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": -share}})
        
        users_col.update_one({"user_id": room["creator"]}, {"$inc": {"coins": -room["share"]}})

        room["player2"] = uid

        bot.edit_message_caption(
    caption="🎮 هر دو بازیکن وارد شدند!\nدر حال شروع...",
    chat_id=room["chat_id"],
    message_id=room["message_id"]
)

        start_real_game(room_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_xo_"))
    @require_join
    def cancel_xo(call):
        room_id = int(call.data.split("_")[2])
        uid = call.from_user.id

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

    # فقط سازنده بتواند لغو کند
        if uid != room["creator"]:
            bot.answer_callback_query(call.id, "فقط سازنده می‌تواند لغو کند ❌")
            return

    # اگر نفر دوم وارد شده باشد، دیگر لغو مجاز نیست
        if room["player2"] is not None:
            bot.answer_callback_query(call.id, "بازی شروع شده و قابل لغو نیست ❌")
            return

    # حذف پیام
        try:
            bot.edit_message_caption(
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                caption="❌ بازی توسط سازنده لغو شد.",
                reply_markup=InlineKeyboardMarkup()
        )
        except:
            pass

        xo_rooms.pop(room_id)
        bot.answer_callback_query(call.id, "بازی لغو شد ✅")

#=====================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("xo_"))
    @require_join
    def handle_xo_move(call):
        _, room_id, index = call.data.split("_")
        room_id = int(room_id)
        index = int(index)
        uid = call.from_user.id

        if room_id not in xo_rooms:
            return

        room = xo_rooms[room_id]

        if uid != room["turn"]:
            bot.answer_callback_query(call.id, "نوبت شما نیست ❌")
            return

        if room["board"][index] != " ":
            bot.answer_callback_query(call.id, "این خانه پر است ❌")
            return
            
        if room["player2"] is None:
    # هنوز نفر دوم وارد نشده، بازی ادامه دارد
            bot.answer_callback_query(call.id, "نفر دوم هنوز وارد نشده ❌")
            return 

        symbol = room["symbols"][uid]
        room["board"][index] = symbol

        # برد
        if check_winner(room["board"], symbol):
            finish_game(room_id, uid)
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
                "𝐕𝐈𝐏 | گیم XO\n"
                f"𝐕𝐈𝐏 | {room['total_bet']} الماس\n"
                f"𝐕𝐈𝐏 | سازنده: {creator_mention}\n"
                f"𝐕𝐈𝐏 | شرکت‌کننده: {player2_mention}\n"
                "◈ ━━━✦ 𝑿𝑶 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
            )

            bot.edit_message_caption(
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                caption=final_text,
                reply_markup=InlineKeyboardMarkup(),  # دکمه‌ها حذف شوند
                
            )

            xo_rooms.pop(room_id)
            return

        # تغییر نوبت و ادامه بازی
        room["turn"] = room["player2"] if uid == room["creator"] else room["creator"]
        send_board(room_id)



    @bot.message_handler(content_types=['new_chat_members'])
    @require_join
    def welcome_new_members(message):
        for new_user in message.new_chat_members:
        # بررسی بن بودن
            if is_banned(new_user.id):
                continue

        # ساخت کیبورد پنل
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(KeyboardButton("موجودی"))
        markup.row(KeyboardButton("حساب کاربری"))
        markup.row(KeyboardButton("آمار سکه"), KeyboardButton("آمار برد"))
        markup.row(KeyboardButton("دوز 20"))
        markup.row(KeyboardButton("دوز 500"))
        markup.row(KeyboardButton(" ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌ ‌"))
        # ارسال پیام پنل به کاربر جدید
        for new_user in message.new_chat_members:
            bot.send_message(
                message.chat.id,
                f"به ربات self nix خوش آمدید {new_user.first_name}!\nپنل برای شما آماده شد.",
                reply_markup=markup
    )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_emoji|"))
    def buy_emoji(call):
        uid = call.from_user.id
        ensure_user(call.from_user)

        _, file_id = call.data.split("|")

        pack_data = emoji_shop_sessions.get(uid, {})
        emoji_id = pack_data.get(file_id)

        if not emoji_id:
            bot.answer_callback_query(call.id, "ایموجی پیدا نشد ❌")
            return

        user = users_col.find_one({"user_id": uid})
        price = DEFAULT_EMOJI_PRICE

        if not user or user.get("coins", 0) < price:
            bot.answer_callback_query(call.id, "سکه کافی نیست ❌")
            return

        users_col.update_one(
        {"user_id": uid},
        {
            "$inc": {"coins": -price},
            "$set": {
                "xo_emoji": emoji_id,
                "xo_sticker": file_id
            }
        }
    )

        bot.answer_callback_query(call.id, "خرید انجام شد ✅")
