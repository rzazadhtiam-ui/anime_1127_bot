import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from pymongo import MongoClient
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
def register_game(dp, bot):
    router.bot = bot
    dp.include_router(router)

def bot():
    return router.bot

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

def kb(room_id, p1, p2):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("✊", callback_data=f"move:{room_id}:{p1}:rock"),
            InlineKeyboardButton("✋", callback_data=f"move:{room_id}:{p1}:paper"),
            InlineKeyboardButton("✌️", callback_data=f"move:{room_id}:{p1}:scissors"),
        ],
        [
            InlineKeyboardButton("✊", callback_data=f"move:{room_id}:{p2}:rock"),
            InlineKeyboardButton("✋", callback_data=f"move:{room_id}:{p2}:paper"),
            InlineKeyboardButton("✌️", callback_data=f"move:{room_id}:{p2}:scissors"),
        ]
    ])

# ================= ROUND SYSTEM =================
async def start_round(room_id):
    room = stonechi_rooms[room_id]
    p1, p2 = room["p1"], room["p2"]

    u1 = get_user(p1)
    u2 = get_user(p2)

    text = (
        "🎮 StoneChi\n\n"
        f"{u1.get('first_name')} : {room['score'][p1]}\n"
        f"{u2.get('first_name')} : {room['score'][p2]}\n\n"
        f"Round {room['round']}/{room['max_round']}"
    )

    await bot().edit_message_text(
        text,
        room["chat_id"],
        room["msg_id"],
        reply_markup=kb(room_id, p1, p2)
    )

async def process_round(room_id):
    room = stonechi_rooms[room_id]
    p1, p2 = room["p1"], room["p2"]

    a, b = room["moves"][p1], room["moves"][p2]
    res = winner(a, b)

    if res == "p1":
        room["score"][p1] += 1
    elif res == "p2":
        room["score"][p2] += 1

    room["moves"] = {p1: None, p2: None}

    await asyncio.sleep(1)

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

    await bot().edit_message_text(
        f"🏆 پایان بازی\nبرنده: {winner_id}\nجایزه: {room['bet']}",
        room["chat_id"],
        room["msg_id"]
    )

    stonechi_rooms.pop(room_id, None)


def register_game(router: Router, bot: Bot):
# ================= HANDLERS =================
    @router.message(F.text.startswith("سنگچی"))
    async def create_game(message: Message):
        ensure_user(message.from_user)

        try:
            bet = int(message.text.split()[1])
        except:
            await message.answer("سنگچی 500")
            return

        if bet % 2 != 0:
            await message.answer("عدد باید زوج باشد")
            return

        uid = message.from_user.id
        user = get_user(uid)

        if user.get("coins", 0) < bet // 2:
            await message.answer("سکه کافی نیست")
            return

        remove_coins(uid, bet // 2)

        msg = await message.answer(
        "🎮 RPS Game",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Join", callback_data=f"join:{message.message_id}")]
        ])
    )

        stonechi_rooms[message.message_id] = {
        "p1": uid,
        "p2": None,
        "chat_id": msg.chat.id,
        "msg_id": msg.message_id,
        "bet": bet,
        "score": {uid: 0},
        "moves": {},
        "round": 1,
        "max_round": None
    }

    @router.callback_query(F.data.startswith("join:"))
    async def join(call: CallbackQuery):
        room_id = int(call.data.split(":")[1])
        uid = call.from_user.id

        room = stonechi_rooms.get(room_id)
        if not room:
            return

        if room["p2"]:
            await call.answer("پر شده")
            return

        room["p2"] = uid
        room["score"][uid] = 0
        room["moves"][uid] = None

        await call.message.edit_text(
        "انتخاب تعداد دور",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton("1", callback_data=f"round:{room_id}:1"),
                InlineKeyboardButton("3", callback_data=f"round:{room_id}:3"),
                InlineKeyboardButton("5", callback_data=f"round:{room_id}:5"),
            ]
        ])
    )

    @router.callback_query(F.data.startswith("round:"))
    async def set_round(call: CallbackQuery):
        _, room_id, r = call.data.split(":")
        room_id = int(room_id)

        room = stonechi_rooms[room_id]
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
            await call.answer("برای شما نیست")
            return

        room["moves"][player] = choice
        await call.answer("ثبت شد")

        if all(room["moves"].values()):
            await process_round(room_id)
