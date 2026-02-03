# anime_panel_module.py
from telebot import types

anime_col = None
bot_instance = None
admin_check = None
OWNER = None

# =============================
# DATABASE STRUCTURE
# =============================

def get_anime(name):
    return anime_col.find_one({"name": name})


def create_anime_if_not_exists(name):
    if not get_anime(name):
        anime_col.insert_one({
            "name": name,
            "direct": None,
            "seasons": {}
        })


# =============================
# KEYBOARDS
# =============================

def anime_keyboard():
    markup = types.InlineKeyboardMarkup()

    for anime in anime_col.find():
        markup.add(
            types.InlineKeyboardButton(
                anime["name"],
                callback_data=f"anime:{anime['name']}"
            )
        )

    return markup


def season_keyboard(anime):
    markup = types.InlineKeyboardMarkup()
    data = get_anime(anime)

    for season in data["seasons"].keys():
        markup.add(
            types.InlineKeyboardButton(
                f"Season {season}",
                callback_data=f"season:{anime}:{season}"
            )
        )

    return markup


def episode_keyboard(anime, season):
    markup = types.InlineKeyboardMarkup()
    data = get_anime(anime)

    episodes = data["seasons"][season]

    for ep in episodes.keys():
        markup.add(
            types.InlineKeyboardButton(
                f"Episode {ep}",
                callback_data=f"episode:{anime}:{season}:{ep}"
            )
        )

    if data.get("direct"):
        markup.add(
            types.InlineKeyboardButton(
                "🎬 نسخه کامل",
                callback_data=f"direct:{anime}"
            )
        )

    return markup

# =============================
# COMMAND /anime
# =============================

def anime_cmd(message):
    if anime_col.count_documents({}) == 0:
        bot_instance.reply_to(message, "انیمه‌ای وجود ندارد")
        return

    bot_instance.send_message(
        message.chat.id,
        "📺 لیست انیمه‌ها",
        reply_markup=anime_keyboard()
    )

# =============================
# CALLBACK HANDLER
# =============================

def callback_handler(call):
    data = call.data.split(":")

    if data[0] == "anime":
        anime = data[1]
        info = get_anime(anime)

        if info["direct"] and not info["seasons"]:
            bot_instance.send_document(call.message.chat.id, info["direct"])
            return

        bot_instance.edit_message_text(
            f"{anime} - Seasons",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=season_keyboard(anime)
        )

    elif data[0] == "season":
        anime = data[1]
        season = data[2]

        bot_instance.edit_message_text(
            f"{anime} - Season {season}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=episode_keyboard(anime, season)
        )

    elif data[0] == "episode":
        anime = data[1]
        season = data[2]
        ep = data[3]

        info = get_anime(anime)
        file_id = info["seasons"][season][ep]

        bot_instance.send_document(call.message.chat.id, file_id)

    elif data[0] == "direct":
        anime = data[1]
        info = get_anime(anime)

        bot_instance.send_document(call.message.chat.id, info["direct"])

# =============================
# ADD ANIME
# =============================

def add_anime_cmd(message):
    if not admin_check(message.from_user.id):
        return

    if not message.reply_to_message:
        bot_instance.reply_to(message, "روی فایل ریپلای کن")
        return

    parts = message.text.replace("/add_anime", "").strip().split("|")
    parts = [p.strip() for p in parts]

    file = message.reply_to_message.document
    if not file:
        bot_instance.reply_to(message, "فایل ارسال کن")
        return

    anime = parts[0]
    create_anime_if_not_exists(anime)

    if len(parts) == 1:
        anime_col.update_one(
            {"name": anime},
            {"$set": {"direct": file.file_id}}
        )
        bot_instance.reply_to(message, "انیمه مستقیم ذخیره شد")
        return

    if len(parts) == 3:
        season = parts[1]
        ep = parts[2]

        anime_col.update_one(
            {"name": anime},
            {"$set": {f"seasons.{season}.{ep}": file.file_id}}
        )

        bot_instance.reply_to(message, "قسمت ذخیره شد")

# =============================
# REMOVE ANIME
# =============================

def remove_anime_cmd(message):
    if not admin_check(message.from_user.id):
        return

    parts = message.text.replace("/remov_anime", "").strip().split("|")
    parts = [p.strip() for p in parts]

    anime = parts[0]

    if len(parts) == 1:
        anime_col.delete_one({"name": anime})
        bot_instance.reply_to(message, "انیمه حذف شد")
        return

    if len(parts) == 2:
        anime_col.update_one(
            {"name": anime},
            {"$unset": {f"seasons.{parts[1]}": ""}}
        )
        bot_instance.reply_to(message, "فصل حذف شد")
        return

    if len(parts) == 3:
        anime_col.update_one(
            {"name": anime},
            {"$unset": {f"seasons.{parts[1]}.{parts[2]}": ""}}
        )
        bot_instance.reply_to(message, "قسمت حذف شد")

# =============================
# ECHO
# =============================

def echo_cmd(message):
    if not admin_check(message.from_user.id):
        return

    if not message.reply_to_message:
        return

    msg = message.reply_to_message

    # ارسال به همه چت‌هایی که ربات توش هست
    for dialog in bot_instance.get_updates():
        try:
            bot_instance.copy_message(
                dialog.message.chat.id,
                msg.chat.id,
                msg.message_id
            )
        except:
            pass

# =============================
# ADMIN LIST
# =============================

def admin_list_cmd(message):
    if message.from_user.id != OWNER:
        return

    text = "Admin List:\n"

    for admin in admin_check.__self__.find():
        text += f"{admin['user_id']}\n"

    bot_instance.reply_to(message, text)

# =============================
# REGISTER
# =============================

def register_anime_panel(bot, db, is_admin_func, owner_id):
    global anime_col, bot_instance, admin_check, OWNER

    bot_instance = bot
    anime_col = db["anime_panel"]
    admin_check = is_admin_func
    OWNER = owner_id

    bot.message_handler(commands=["anime"])(anime_cmd)
    bot.message_handler(commands=["add_anime"])(add_anime_cmd)
    bot.message_handler(commands=["remov_anime"])(remove_anime_cmd)

    bot.message_handler(commands=["echo"])(echo_cmd)
    bot.message_handler(commands=["admin_list"])(admin_list_cmd)

    bot.callback_query_handler(func=lambda call: True)(callback_handler)
