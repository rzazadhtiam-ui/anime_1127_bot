import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from pymongo import MongoClient
from aiogram import Bot, Dispatcher, Router


router = Router()
stonechi_rooms = {}

# ================= DB =================
MONGO_URL = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

mongo = MongoClient(MONGO_URL)
db = mongo["telegram_sessions"]
users_col = db["users"]

# ================= BOT HOLDER =================


# ================= DB HELPERS =================
def ensure_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {
            "$set": {"first_name": user.first_name},
            "$setOnInsert": {
                "coins": 0,
                "wins": 0,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

def add_coins(uid, amount):
    users_col.update_one({"user_id": uid}, {"$inc": {"coins": amount}})

def remove_coins(uid, amount):
    users_col.update_one({"user_id": uid}, {"$inc": {"coins": -amount}})

def get_user(uid):
    return users_col.find_one({"user_id": uid}) or {}

# ================= GAME LOGIC =================
def winner(a, b):
    if a == b:
        return None
    rules = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    return "p1" if rules[a] == b else "p2"

def choice_emoji(choice):
    return {"rock": "🪨", "paper": "📄", "scissors": "✂️"}.get(choice, choice)

# ================= KEYBOARDS =================
def waiting_kb(room_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ورود به بازی", callback_data=f"join:{room_id}", style="success")],
        [InlineKeyboardButton(text="❌ لغو بازی", callback_data=f"cancel:{room_id}", style="danger")]
    ])

def rounds_kb(room_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data=f"round:{room_id}:1"),
            InlineKeyboardButton(text="3️⃣", callback_data=f"round:{room_id}:3"),
            InlineKeyboardButton(text="5️⃣", callback_data=f"round:{room_id}:5"),
        ]
    ])

def move_kb(room_id, p1, p2):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪨", callback_data=f"move:{room_id}:{p1}:rock"),
            InlineKeyboardButton(text="📄", callback_data=f"move:{room_id}:{p1}:paper"),
            InlineKeyboardButton(text="✂️", callback_data=f"move:{room_id}:{p1}:scissors"),
        ],
        [
            InlineKeyboardButton(text="🪨", callback_data=f"move:{room_id}:{p2}:rock"),
            InlineKeyboardButton(text="📄", callback_data=f"move:{room_id}:{p2}:paper"),
            InlineKeyboardButton(text="✂️", callback_data=f"move:{room_id}:{p2}:scissors"),
        ]
    ])

def partial_kb(room_id, player):
    """Only one player's buttons (for anti-cheat)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪨", callback_data=f"move:{room_id}:{player}:rock"),
            InlineKeyboardButton(text="📄", callback_data=f"move:{room_id}:{player}:paper"),
            InlineKeyboardButton(text="✂️", callback_data=f"move:{room_id}:{player}:scissors"),
        ]
    ])

def noop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[])

# ================= ROUND SYSTEM =================
async def start_round(room_id):
    room = stonechi_rooms[room_id]
    p1, p2 = room["p1"], room["p2"]

    u1 = get_user(p1)
    u2 = get_user(p2)

    text = (
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        f"🏆 امتیازها\n"
        f"{u1.get('first_name', 'Player1')}: {room['score'][p1]}\n"
        f"{u2.get('first_name', 'Player2')}: {room['score'][p2]}\n\n"
        f"🎯 دور {room['round']}/{room['max_round']}\n"
        "⏳ نوبت: هر دو بازیکن می‌توانند انتخاب کنند\n"
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

    await bot.edit_message_text(
        text,
        room["chat_id"],
        room["msg_id"],
        reply_markup=move_kb(room_id, p1, p2)
    )

async def process_round(room_id):
    room = stonechi_rooms[room_id]
    p1, p2 = room["p1"], room["p2"]

    a, b = room["moves"][p1], room["moves"][p2]
    res = winner(a, b)

    u1 = get_user(p1)
    u2 = get_user(p2)
    p1_name = u1.get("first_name", "Player1")
    p2_name = u2.get("first_name", "Player2")

    if res == "p1":
        room["score"][p1] += 1
        winner_name = p1_name
        loser_name = p2_name
        result_emoji = "🥇"
    elif res == "p2":
        room["score"][p2] += 1
        winner_name = p2_name
        loser_name = p1_name
        result_emoji = "🥇"
    else:
        winner_name = "مساوی"
        loser_name = ""
        result_emoji = "🤝"

    # Reveal phase with countdown
    reveal_text = (
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        f"🎯 دور {room['round']} از {room['max_round']}\n\n"
        f"{choice_emoji(a)} {p1_name}\n"
        f"{choice_emoji(b)} {p2_name}\n\n"
        "⏳ اعلام نتیجه تا 3 ثانیه دیگر...\n"
        "3️⃣"
    )

    await bot.edit_message_text(
        reveal_text,
        room["chat_id"],
        room["msg_id"],
        reply_markup=noop_kb()
    )

    await asyncio.sleep(1)
    await bot.edit_message_text(reveal_text.replace("3️⃣", "2️⃣"), room["chat_id"], room["msg_id"])
    await asyncio.sleep(1)
    await bot.edit_message_text(reveal_text.replace("3️⃣", "1️⃣"), room["chat_id"], room["msg_id"])
    await asyncio.sleep(1)
    await bot.edit_message_text(reveal_text.replace("3️⃣", "0️⃣"), room["chat_id"], room["msg_id"])
    await asyncio.sleep(0.5)

    # Result text
    if res is None:
        result_text = (
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            f"🤝 مساوی در دور {room['round']}\n\n"
            "امتیازی ثبت نشد.\n"
            f"📊 امتیازات\n"
            f"{p1_name}: {room['score'][p1]}\n"
            f"{p2_name}: {room['score'][p2]}\n\n"
            "🎯 شروع دور بعدی\n"
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )
    else:
        result_text = (
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            f"🏆 نتیجه دور {room['round']}\n\n"
            f"{result_emoji} برنده: {winner_name}\n"
            f"🥈 بازنده: {loser_name}\n\n"
            f"📊 امتیازات\n"
            f"{p1_name}: {room['score'][p1]}\n"
            f"{p2_name}: {room['score'][p2]}\n\n"
            f"🎯 شروع دور بعدی\n"
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )

    await bot.edit_message_text(
        result_text,
        room["chat_id"],
        room["msg_id"],
        reply_markup=noop_kb()
    )

    await asyncio.sleep(2)

    # Reset moves
    room["moves"] = {p1: None, p2: None}
    room["round"] += 1

    if room["round"] > room["max_round"]:
        await end_game(room_id)
    else:
        await start_round(room_id)

async def end_game(room_id):
    room = stonechi_rooms[room_id]
    p1, p2 = room["p1"], room["p2"]

    s1, s2 = room["score"][p1], room["score"][p2]

    if s1 > s2:
        winner_id = p1
    elif s2 > s1:
        winner_id = p2
    else:
        winner_id = random.choice([p1, p2])

    add_coins(winner_id, room["bet"])
    users_col.update_one({"user_id": winner_id}, {"$inc": {"wins": 1}})

    w = get_user(winner_id)
    l_id = p2 if winner_id == p1 else p1
    l = get_user(l_id)

    winner_name = w.get("first_name", "برنده")
    loser_name = l.get("first_name", "بازنده")

    final_text = (
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        "🎉 اتمام بازی\n\n"
        f"📊 نتیجه نهایی\n"
        f"{max(s1, s2)} بر {min(s1, s2)}\n\n"
        f"🥇 برنده: {winner_name}\n"
        f"🥈 بازنده: {loser_name}\n\n"
        f"💰 مبلغ جایزه: {room['bet']} سکه\n"
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

    await bot.edit_message_text(
        final_text,
        room["chat_id"],
        room["msg_id"],
        reply_markup=noop_kb()
    )

    stonechi_rooms.pop(room_id, None)


def register_game(router: Router, bot):
# ================= HANDLERS =================
    @router.message(F.text.startswith("سنگچی"))
    async def create_game(message: Message):
        ensure_user(message.from_user)
    
        try:
            bet = int(message.text.split()[1])
        except:
            await message.reply("فرمت درست: سنگچی 100")
            return

        if bet < 2 or bet % 2 != 0:
            await message.reply("عدد باید زوج و حداقل ۲ باشد ❌")
            return

        uid = message.from_user.id
        user = get_user(uid)

        if user.get("coins", 0) < bet // 2:
            await message.reply("سکه کافی نیست ❌")
            return

        remove_coins(uid, bet // 2)

    # Waiting panel
        text = (
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        f"🎮 بازی: سنگچی\n"
        f"💰 شرط کل بازی: {bet} سکه\n"
        f"💵 سهم هر نفر: {bet // 2} سکه\n"
        "🏆 برنده کل مبلغ را می‌برد\n\n"
        "⏳ در انتظار ورود نفر دوم...\n"
        f"👤 سازنده: {message.from_user.first_name}\n"
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

        msg = await message.answer(text, reply_markup=waiting_kb(message.message_id))

        stonechi_rooms[message.message_id] = {
        "p1": uid,
        "p2": None,
        "chat_id": msg.chat.id,
        "msg_id": msg.message_id,
        "bet": bet,
        "score": {uid: 0},
        "moves": {uid: None},
        "round": 1,
        "max_round": None,
        "creator": uid
    }

    @router.callback_query(F.data.startswith("join:"))
    async def join(call: CallbackQuery):
        room_id = int(call.data.split(":")[1])
        uid = call.from_user.id

        room = stonechi_rooms.get(room_id)
        if not room:
            await call.answer("بازی وجود ندارد")
            return

        if room["p2"]:
            await call.answer("پر شده ❌")
            return

        if uid == room["p1"]:
            await call.answer("شما سازنده هستید ❌")
            return

        user = get_user(uid)
        if user.get("coins", 0) < room["bet"] // 2:
            await call.answer("سکه کافی نیست ❌")
            return

        remove_coins(uid, room["bet"] // 2)

        room["p2"] = uid
        room["score"][uid] = 0
        room["moves"][uid] = None

        p1_name = get_user(room["p1"]).get("first_name", "Player1")
        p2_name = call.from_user.first_name or "Player2"

        text = (
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
        f"👤 بازیکن اول: {p1_name}\n"
        f"👤 بازیکن دوم: {p2_name}\n\n"
        "🎯 تعداد دست‌ها را انتخاب کنید\n"
        "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
    )

        await call.message.edit_text(text, reply_markup=rounds_kb(room_id))

    @router.callback_query(F.data.startswith("cancel:"))
    async def cancel_game(call: CallbackQuery):
        room_id = int(call.data.split(":")[1])
        room = stonechi_rooms.get(room_id)

        if not room or call.from_user.id != room["p1"]:
            await call.answer("فقط سازنده می‌تواند لغو کند ❌")
            return
    
        if room["p2"]:
            await call.answer("بازی شروع شده و قابل لغو نیست ❌")
        return

    # Refund to creator
        add_coins(room["p1"], room["bet"] // 2)

        await bot.edit_message_text(
        "❌ بازی توسط سازنده لغو شد و سکه بازگشت داده شد.",
        room["chat_id"],
        room["msg_id"]
    )

        stonechi_rooms.pop(room_id, None)

    @router.callback_query(F.data.startswith("round:"))
    async def set_round(call: CallbackQuery):
        _, room_id, r = call.data.split(":")
        room_id = int(room_id)
        room = stonechi_rooms.get(room_id)

        if not room or call.from_user.id != room["p1"]:
            await call.answer("فقط سازنده می‌تواند تعداد دور را انتخاب کند ❌")
            return

        room["max_round"] = int(r)
        await start_round(room_id)

    @router.callback_query(F.data.startswith("move:"))
    async def move(call: CallbackQuery):
        _, room_id, player, choice = call.data.split(":")
        room_id = int(room_id)
        player = int(player)

        room = stonechi_rooms.get(room_id)
        if not room:
            return

        if call.from_user.id != player:
            await call.answer("برای شما نیست ❌")
            return

        if room["moves"].get(player):
            await call.answer("قبلا انتخاب کردی ❌")
            return

        room["moves"][player] = choice
        await call.answer("ثبت شد ✅")

        p1, p2 = room["p1"], room["p2"]

        if all(room["moves"].values()):
            await process_round(room_id)
        else:
        # Anti-cheat: show who chose, keep only other player's buttons
            who = "بازیکن اول" if player == p1 else "بازیکن دوم"
            other_player = p2 if player == p1 else p1

            text = (
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈\n"
            f"✅ {who} انتخاب خود را انجام داد\n"
            "⏳ منتظر انتخاب بازیکن دوم...\n"
            "◈ ━━━✦ RPS 𝑮𝑨𝑴𝑬 ✦━━━ ◈"
        )

            await bot.edit_message_text(
            text,
            room["chat_id"],
            room["msg_id"],
            reply_markup=partial_kb(room_id, other_player)
        )

# ================= REGISTER =================

    # Already registered via include_router in main
    
