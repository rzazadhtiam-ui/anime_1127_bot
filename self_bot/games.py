# ================================================================
# games.py — ماژول بازی‌های کامل برای هسته بات telebot (Self Nix)
# هماهنگ کامل با self_bot.py + update1_2.py + update1.py
# به‌روزرسانی شده طبق درخواست کاربر (رولت ۴ نفره + مین‌روب بزرگ + حذف تیک‌بات)
# ================================================================

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import random
import time

# ================= MONGO (دقیقاً مثل هسته) =================
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

# ================= ROOMS =================
rps_rooms = {}
mines_rooms = {}
roulette_rooms = {}
coinflip_rooms = {}

# ================= HELPERS =================
def ensure_user(user):
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
                "created_at": time.time(),
            },
        },
        upsert=True,
    )

def is_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("ban", False) if user else False

def get_coins(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("coins", 0) if user else 0

def update_coins(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})

# ================= رپس (PvP + vs بات) =================
def register_rps(bot):
    @bot.message_handler(func=lambda m: m.text and m.text.lower().startswith(("سنگ کاغذ قیگی", "rps")))
    def create_rps(message):
        if is_banned(message.from_user.id):
            return
        ensure_user(message.from_user)

        parts = message.text.strip().split()
        vs_bot = False
        total_bet = 0

        if len(parts) >= 2:
            if parts[1].lower() in ["بات", "bot"]:
                vs_bot = True
                if len(parts) > 2:
                    try:
                        total_bet = int(parts[2])
                    except:
                        bot.reply_to(message, "فرمت: رپس بات 100")
                        return
            else:
                try:
                    total_bet = int(parts[1])
                except:
                    bot.reply_to(message, "فرمت: رپس 100 یا رپس بات 100")
                    return

        if total_bet < 10 or total_bet % 2 != 0:
            bot.reply_to(message, "مبلغ باید زوج و حداقل ۱۰ سکه باشه ❌")
            return

        share = total_bet // 2
        uid = message.from_user.id
        if get_coins(uid) < share:
            bot.reply_to(message, "سکه کافی نداری ❌")
            return

        room_id = message.message_id
        rps_rooms[room_id] = {
            "creator": uid,
            "player2": None,
            "total_bet": total_bet,
            "share": share,
            "chat_id": message.chat.id,
            "message_id": None,
            "vs_bot": vs_bot,
            "choices": {}
        }

        markup = InlineKeyboardMarkup()
        if vs_bot:
            markup.add(InlineKeyboardButton("🎮 شروع با ربات", callback_data=f"rps_start_bot_{room_id}"))
        else:
            markup.add(InlineKeyboardButton("🎮 شرکت در بازی", callback_data=f"rps_join_{room_id}"))
        markup.add(InlineKeyboardButton("❌ لغو", callback_data=f"rps_cancel_{room_id}"))

        msg = bot.send_message(
            message.chat.id,
            f"🎮 رپس با شرط {total_bet} سکه\nسهم هر نفر: {share} سکه\nبرنده همه رو می‌بره!",
            reply_markup=markup
        )
        rps_rooms[room_id]["message_id"] = msg.message_id

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("rps_join_", "rps_start_bot_", "rps_cancel_", "rps_choice_")))
    def rps_handler(call):
        data = call.data
        uid = call.from_user.id
        if is_banned(uid):
            return
        ensure_user(call.from_user)

        if data.startswith("rps_join_"):
            room_id = int(data.split("_")[2])
            if room_id not in rps_rooms:
                return
            room = rps_rooms[room_id]
            if uid == room["creator"] or room["player2"]:
                bot.answer_callback_query(call.id, "نمی‌تونی جوین شی ❌")
                return

            share = room["share"]
            if get_coins(uid) < share:
                bot.answer_callback_query(call.id, "سکه کافی نداری ❌")
                return

            update_coins(uid, -share)
            update_coins(room["creator"], -share)

            room["player2"] = uid

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✊ سنگ", callback_data=f"rps_choice_{room_id}_rock"),
                InlineKeyboardButton("✋ کاغذ", callback_data=f"rps_choice_{room_id}_paper"),
                InlineKeyboardButton("✌️ قیچی", callback_data=f"rps_choice_{room_id}_scissors")
            )
            bot.edit_message_text("انتخاب کن!", chat_id=room["chat_id"], message_id=room["message_id"], reply_markup=markup)

        elif data.startswith("rps_start_bot_"):
            room_id = int(data.split("_")[3])
            if room_id not in rps_rooms:
                return
            room = rps_rooms[room_id]
            if uid != room["creator"]:
                return

            share = room["share"]
            update_coins(uid, -share)

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✊ سنگ", callback_data=f"rps_choice_{room_id}_rock_bot"),
                InlineKeyboardButton("✋ کاغذ", callback_data=f"rps_choice_{room_id}_paper_bot"),
                InlineKeyboardButton("✌️ قیچی", callback_data=f"rps_choice_{room_id}_scissors_bot")
            )
            bot.edit_message_text("انتخاب کن (vs ربات)!", chat_id=room["chat_id"], message_id=room["message_id"], reply_markup=markup)

        elif data.startswith("rps_cancel_"):
            room_id = int(data.split("_")[2])
            if room_id in rps_rooms and uid == rps_rooms[room_id]["creator"]:
                bot.edit_message_text("❌ بازی لغو شد", chat_id=rps_rooms[room_id]["chat_id"], message_id=rps_rooms[room_id]["message_id"])
                rps_rooms.pop(room_id)

        elif data.startswith("rps_choice_"):
            parts = data.split("_")
            room_id = int(parts[2])
            choice = parts[3]
            if room_id not in rps_rooms:
                return
            room = rps_rooms[room_id]

            if room["vs_bot"]:
                bot_choice = random.choice(["rock", "paper", "scissors"])
                user_choice = choice.replace("_bot", "")
                result = get_rps_result(user_choice, bot_choice, room["creator"], None, room["total_bet"])
                bot.edit_message_text(result, chat_id=room["chat_id"], message_id=room["message_id"])
                rps_rooms.pop(room_id)
                return

            room["choices"][uid] = choice
            if len(room["choices"]) == 2:
                p1 = room["creator"]
                p2 = room["player2"]
                c1 = room["choices"].get(p1)
                c2 = room["choices"].get(p2)
                result = get_rps_result(c1, c2, p1, p2, room["total_bet"])
                bot.edit_message_text(result, chat_id=room["chat_id"], message_id=room["message_id"])
                rps_rooms.pop(room_id)

    def get_rps_result(c1, c2, p1, p2, total):
        if c1 == c2:
            update_coins(p1, total // 2)
            if p2:
                update_coins(p2, total // 2)
            return f"مساوی! هر نفر {total//2} سکه برگشت خورد 🤝"

        wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
        if (c1, c2) in wins:
            winner, loser = p1, p2
        else:
            winner, loser = p2, p1

        update_coins(winner, total)
        w_user = users_col.find_one({"user_id": winner})
        w_name = w_user.get("first_name", "کاربر") if w_user else "کاربر"
        return f"🏆 برنده: {w_name}\n💎 جایزه: {total} سکه"

# ================= مین‌روب (۴×۴ با ۶ بمب - پنل بزرگ‌تر) =================
def register_mines(bot):
    @bot.message_handler(func=lambda m: m.text and m.text.lower().startswith(("مین روب", "mines")))
    def create_mines(message):
        if is_banned(message.from_user.id):
            return
        ensure_user(message.from_user)

        parts = message.text.strip().split()
        total_bet = 50
        if len(parts) > 1:
            try:
                total_bet = int(parts[1])
            except:
                pass

        if total_bet < 10:
            total_bet = 50

        uid = message.from_user.id
        if get_coins(uid) < total_bet:
            bot.reply_to(message, "سکه کافی نداری ❌")
            return

        room_id = message.message_id
        size = 4
        total_cells = size * size
        num_mines = 6
        mines = set(random.sample(range(total_cells), num_mines))

        mines_rooms[room_id] = {
            "creator": uid,
            "total_bet": total_bet,
            "chat_id": message.chat.id,
            "message_id": None,
            "mines": mines,
            "opened": set(),
            "game_over": False,
            "size": size
        }

        markup = create_mines_markup(room_id)
        msg = bot.send_message(
            message.chat.id,
            f"💣 مین‌روب (۴×۴ با ۶ بمب)\nشرط: {total_bet} سکه\nروی خانه‌ها کلیک کن",
            reply_markup=markup
        )
        mines_rooms[room_id]["message_id"] = msg.message_id

    def create_mines_markup(room_id):
        room = mines_rooms[room_id]
        size = room["size"]
        markup = InlineKeyboardMarkup()
        for i in range(size):
            row = []
            for j in range(size):
                idx = i * size + j
                if idx in room["opened"]:
                    text = "💥" if idx in room["mines"] else "💎"
                else:
                    text = "‌   ‌"
                row.append(InlineKeyboardButton(text, callback_data=f"mine_{room_id}_{idx}"))
            markup.row(*row)
        return markup

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mine_"))
    def mine_click(call):
        parts = call.data.split("_")
        room_id = int(parts[1])
        idx = int(parts[2])
        if room_id not in mines_rooms:
            return
        room = mines_rooms[room_id]
        if room["game_over"] or idx in room["opened"]:
            return

        room["opened"].add(idx)

        if idx in room["mines"]:
            room["game_over"] = True
            update_coins(room["creator"], -room["total_bet"])
            bot.edit_message_text(
                f"💥 باختی! روی بمب زدی\nشرط {room['total_bet']} سکه از دست رفت",
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                reply_markup=create_mines_markup(room_id)
            )
            mines_rooms.pop(room_id)
            return

        total_cells = room["size"] * room["size"]
        if len(room["opened"]) == total_cells - len(room["mines"]):
            room["game_over"] = True
            update_coins(room["creator"], room["total_bet"])
            bot.edit_message_text(
                f"🎉 بردی! همه بمب‌ها رو پیدا کردی\nجایزه: {room['total_bet']} سکه",
                chat_id=room["chat_id"],
                message_id=room["message_id"],
                reply_markup=create_mines_markup(room_id)
            )
            mines_rooms.pop(room_id)
            return

        bot.edit_message_reply_markup(
            chat_id=room["chat_id"],
            message_id=room["message_id"],
            reply_markup=create_mines_markup(room_id)
        )

# ================= رولت روسی (۴ نفره واقعی + انتخاب هدف) =================
def register_roulette(bot):
    @bot.message_handler(func=lambda m: m.text and m.text.lower().startswith(("رولت روسی", "roulette")))
    def create_roulette(message):
        if is_banned(message.from_user.id):
            return
        ensure_user(message.from_user)

        uid = message.from_user.id
        total_bet = 30
        parts = message.text.strip().split()
        if len(parts) > 1:
            try:
                total_bet = int(parts[1])
            except:
                pass

        if get_coins(uid) < total_bet:
            bot.reply_to(message, "سکه کافی نداری ❌")
            return

        room_id = message.message_id
        roulette_rooms[room_id] = {
            "creator": uid,
            "total_bet": total_bet,
            "chat_id": message.chat.id,
            "message_id": None,
            "players": [uid],
            "started": False,
            "current_turn": 0,
            "chambers": [0]*5 + [1],
            "chamber_index": 0,
            "alive": [True]
        }
        random.shuffle(roulette_rooms[room_id]["chambers"])

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎮 جوین شو (نیاز به ۴ نفر)", callback_data=f"roulette_join_{room_id}"))
        markup.add(InlineKeyboardButton("❌ لغو", callback_data=f"roulette_cancel_{room_id}"))

        msg = bot.send_message(
            message.chat.id,
            f"🔫 رولت روسی (۴ نفره واقعی)\nشرط هر نفر: {total_bet} سکه\n"
            "وقتی ۴ نفر جوین شدن بازی شروع می‌شه.\n"
            "هر نوبت می‌تونی انتخاب کنی به کی شلیک کنی!",
            reply_markup=markup
        )
        roulette_rooms[room_id]["message_id"] = msg.message_id

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("roulette_join_", "roulette_cancel_", "roulette_shoot_")))
    def roulette_handler(call):
        data = call.data
        uid = call.from_user.id
        if is_banned(uid):
            return
        ensure_user(call.from_user)

        if data.startswith("roulette_join_"):
            room_id = int(data.split("_")[2])
            if room_id not in roulette_rooms:
                return
            room = roulette_rooms[room_id]

            if uid in room["players"]:
                bot.answer_callback_query(call.id, "قبلاً جوین شدی")
                return
            if len(room["players"]) >= 4:
                bot.answer_callback_query(call.id, "بازی پر شده")
                return

            share = room["total_bet"]
            if get_coins(uid) < share:
                bot.answer_callback_query(call.id, "سکه کافی نداری ❌")
                return

            update_coins(uid, -share)
            room["players"].append(uid)
            room["alive"].append(True)

            # ساخت متن با منشن بازیکنان
            players_text = "\n".join([f"• {get_player_name(p)}" for p in room["players"]])

            if len(room["players"]) == 4:
                room["started"] = True
                room["current_turn"] = 0
                random.shuffle(room["players"])
                random.shuffle(room["alive"])

                markup = create_roulette_shoot_markup(room_id)
                bot.edit_message_text(
                    f"🔫 رولت روسی شروع شد!\n"
                    f"بازیکنان:\n{players_text}\n\n"
                    f"نوبت: {get_player_name(room['players'][0])}\n"
                    "انتخاب کن به کی شلیک کنی:",
                    chat_id=room["chat_id"],
                    message_id=room["message_id"],
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("🎮 جوین شو (نیاز به ۴ نفر)", callback_data=f"roulette_join_{room_id}"))
                markup.add(InlineKeyboardButton("❌ لغو", callback_data=f"roulette_cancel_{room_id}"))

                bot.edit_message_text(
                    f"🔫 رولت روسی\n"
                    f"{len(room['players'])}/۴ نفر جوین شدن:\n{players_text}\n\n"
                    "منتظر بقیه بازیکنان...",
                    chat_id=room["chat_id"],
                    message_id=room["message_id"],
                    reply_markup=markup,
                    parse_mode="HTML"
                )

        elif data.startswith("roulette_cancel_"):
            room_id = int(data.split("_")[2])
            if room_id in roulette_rooms and uid == roulette_rooms[room_id]["creator"]:
                for p in roulette_rooms[room_id]["players"]:
                    update_coins(p, roulette_rooms[room_id]["total_bet"])
                bot.edit_message_text("❌ بازی لغو شد و سکه‌ها برگشت خورد", chat_id=roulette_rooms[room_id]["chat_id"], message_id=roulette_rooms[room_id]["message_id"])
                roulette_rooms.pop(room_id)

        elif data.startswith("roulette_shoot_"):
            parts = data.split("_")
            room_id = int(parts[2])
            target_idx = int(parts[3])
            if room_id not in roulette_rooms:
                return
            room = roulette_rooms[room_id]
            if not room["started"]:
                return

            current_player_idx = room["current_turn"]
            current_player = room["players"][current_player_idx]
            if uid != current_player:
                bot.answer_callback_query(call.id, "نوبت تو نیست!")
                return

            target_player = room["players"][target_idx]

            bullet = room["chambers"][room["chamber_index"]]
            room["chamber_index"] = (room["chamber_index"] + 1) % 6

            if bullet == 1:
                room["alive"][target_idx] = False
                update_coins(target_player, -room["total_bet"])

                alive_players = [p for i, p in enumerate(room["players"]) if room["alive"][i]]
                if len(alive_players) == 1:
                    winner = alive_players[0]
                    update_coins(winner, room["total_bet"] * 4)
                    bot.edit_message_text(
                        f"💥 {get_player_name(target_player)} حذف شد از بازی!\n"
                        f"🏆 برنده نهایی: {get_player_name(winner)}\n"
                        f"جایزه: {room['total_bet'] * 4} سکه",
                        chat_id=room["chat_id"],
                        message_id=room["message_id"]
                    )
                    roulette_rooms.pop(room_id)
                    return
                else:
                    room["current_turn"] = (current_player_idx + 1) % 4
                    while not room["alive"][room["current_turn"]]:
                        room["current_turn"] = (room["current_turn"] + 1) % 4

                    markup = create_roulette_shoot_markup(room_id)
                    bot.edit_message_text(
                        f"💥 {get_player_name(target_player)} حذف شد!\n"
                        f"نوبت بعدی: {get_player_name(room['players'][room['current_turn']])}",
                        chat_id=room["chat_id"],
                        message_id=room["message_id"],
                        reply_markup=markup
                    )
            else:
                room["current_turn"] = (current_player_idx + 1) % 4
                while not room["alive"][room["current_turn"]]:
                    room["current_turn"] = (room["current_turn"] + 1) % 4

                markup = create_roulette_shoot_markup(room_id)
                bot.edit_message_text(
                    f"✅ {get_player_name(target_player)} زنده ماند!\n"
                    f"نوبت بعدی: {get_player_name(room['players'][room['current_turn']])}",
                    chat_id=room["chat_id"],
                    message_id=room["message_id"],
                    reply_markup=markup
                )

    def create_roulette_shoot_markup(room_id):
        room = roulette_rooms[room_id]
        markup = InlineKeyboardMarkup()
        for i, player in enumerate(room["players"]):
            if room["alive"][i]:
                name = get_player_name(player)
                markup.add(InlineKeyboardButton(f"🔫 شلیک به {name}", callback_data=f"roulette_shoot_{room_id}_{i}"))
        return markup

    def get_player_name(user_id):
        user = users_col.find_one({"user_id": user_id})
        return user.get("first_name", "کاربر") if user else "کاربر"

# ================= پرتاب سکه =================
def register_coinflip(bot):
    @bot.message_handler(func=lambda m: m.text and m.text.lower().startswith(("شیر یا خط", "coinflip", "flip")))
    def create_flip(message):
        if is_banned(message.from_user.id):
            return
        ensure_user(message.from_user)

        uid = message.from_user.id
        total_bet = 20
        parts = message.text.strip().split()
        if len(parts) > 1:
            try:
                total_bet = int(parts[1])
            except:
                pass

        if get_coins(uid) < total_bet:
            bot.reply_to(message, "سکه کافی نداری ❌")
            return

        room_id = message.message_id
        coinflip_rooms[room_id] = {
            "creator": uid,
            "total_bet": total_bet,
            "chat_id": message.chat.id,
            "message_id": None
        }

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🪙 شیر", callback_data=f"flip_{room_id}_heads"),
            InlineKeyboardButton("🪙 خط", callback_data=f"flip_{room_id}_tails")
        )

        msg = bot.send_message(
            message.chat.id,
            f"🪙 پرتاب سکه\nشرط: {total_bet} سکه\nانتخاب کن!",
            reply_markup=markup
        )
        coinflip_rooms[room_id]["message_id"] = msg.message_id

    @bot.callback_query_handler(func=lambda call: call.data.startswith("flip_"))
    def flip_handler(call):
        parts = call.data.split("_")
        room_id = int(parts[1])
        choice = parts[2]
        if room_id not in coinflip_rooms:
            return
        room = coinflip_rooms[room_id]

        result = random.choice(["heads", "tails"])
        emoji = "🪙 شیر" if result == "heads" else "🪙 خط"

        if choice == result:
            update_coins(room["creator"], room["total_bet"])
            text = f"{emoji}\n🎉 بردی! جایزه: {room['total_bet']} سکه"
        else:
            update_coins(room["creator"], -room["total_bet"])
            text = f"{emoji}\n😢 باختی! {room['total_bet']} سکه از دست رفت"

        bot.edit_message_text(text, chat_id=room["chat_id"], message_id=room["message_id"])
        coinflip_rooms.pop(room_id)

# ================= ثبت همه بازی‌ها (تیک بات حذف شد) =================
def register_games(bot):
    register_rps(bot)
    register_mines(bot)
    register_roulette(bot)
    register_coinflip(bot)

print("✅ ماژول بازی‌ها به‌روزرسانی شد (رولت ۴ نفره واقعی + مین‌روب ۴×۴ با ۶ بمب + تیک‌بات حذف)")
