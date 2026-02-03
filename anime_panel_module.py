# anime_panel_module.py
from telebot import types

# =============================
# GLOBALS
# =============================
anime_col = None
bot_instance = None
admin_check = None
OWNER = None
PAGE_SIZE = 8  # تعداد آیتم در هر صفحه کیبورد

# =============================
# DATABASE FUNCTIONS
# =============================
def get_anime(name):
    """بر اساس نام انیمه دیتا برگرداند"""
    return anime_col.find_one({"name": name})

def create_anime_if_not_exists(name):
    """اگر انیمه وجود نداشت ایجاد کن"""
    if not get_anime(name):
        anime_col.insert_one({
            "name": name,
            "direct": None,
            "seasons": {}
        })

# =============================
# UTILITY FUNCTIONS
# =============================
def paginate_items(items, page=0):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    return items[start:end], len(items) > end

# =============================
# KEYBOARDS
# =============================
def anime_keyboard(page=0):
    markup = types.InlineKeyboardMarkup()
    all_anime = list(anime_col.find())
    page_items, has_next = paginate_items(all_anime, page)

    for anime in page_items:
        markup.add(types.InlineKeyboardButton(
            anime["name"], callback_data=f"anime:{anime['name']}"
        ))

    if page > 0:
        markup.add(types.InlineKeyboardButton("⬅️ قبلی", callback_data=f"anime_page:{page-1}"))
    if has_next:
        markup.add(types.InlineKeyboardButton("بعدی ➡️", callback_data=f"anime_page:{page+1}"))

    return markup

def season_keyboard(anime):
    markup = types.InlineKeyboardMarkup()
    data = get_anime(anime)
    seasons = data.get("seasons", {})

    for season in seasons.keys():
        markup.add(types.InlineKeyboardButton(
            f"Season {season}", callback_data=f"season:{anime}:{season}"
        ))
    return markup

def episode_keyboard(anime, season):
    markup = types.InlineKeyboardMarkup()
    data = get_anime(anime)
    episodes = data.get("seasons", {}).get(season, {})

    if not episodes:
        markup.add(types.InlineKeyboardButton("❌ هیچ قسمتی موجود نیست", callback_data="noop"))
        return markup

    for ep in episodes.keys():
        markup.add(types.InlineKeyboardButton(
            f"Episode {ep}", callback_data=f"episode:{anime}:{season}:{ep}"
        ))

    if data.get("direct"):
        markup.add(types.InlineKeyboardButton(
            "🎬 نسخه کامل", callback_data=f"direct:{anime}"
        ))
    return markup

# =============================
# COMMAND HANDLERS
# =============================
def anime_cmd(message):
    if anime_col.count_documents({}) == 0:
        bot_instance.reply_to(message, "❌ انیمه‌ای موجود نیست")
        return
    bot_instance.send_message(
        message.chat.id,
        "📺 لیست انیمه‌ها:",
        reply_markup=anime_keyboard()
    )

def add_anime_cmd(message):
    if not admin_check(message.from_user.id):
        return

    if not message.reply_to_message:
        bot_instance.reply_to(message, "⚠️ لطفاً روی فایل ریپلای کنید")
        return

    parts = message.text.replace("/add_anime", "").strip().split("|")
    parts = [p.strip() for p in parts]
    anime = parts[0]
    create_anime_if_not_exists(anime)

    file = getattr(message.reply_to_message, 'document', None)
    if not file:
        bot_instance.reply_to(message, "⚠️ فایل ارسال نشده است")
        return

    if len(parts) == 1:
        anime_col.update_one({"name": anime}, {"$set": {"direct": file.file_id}})
        bot_instance.reply_to(message, "✅ انیمه مستقیم ذخیره شد")
        return

    if len(parts) == 3:
        season = parts[1]
        ep = parts[2]
        anime_col.update_one(
            {"name": anime},
            {"$set": {f"seasons.{season}.{ep}": file.file_id}}
        )
        bot_instance.reply_to(message, f"✅ قسمت {ep} فصل {season} ذخیره شد")

def remove_anime_cmd(message):
    if not admin_check(message.from_user.id):
        return

    parts = message.text.replace("/remov_anime", "").strip().split("|")
    parts = [p.strip() for p in parts]
    anime = parts[0]

    if len(parts) == 1:
        anime_col.delete_one({"name": anime})
        bot_instance.reply_to(message, "✅ انیمه حذف شد")
        return

    if len(parts) == 2:
        anime_col.update_one({"name": anime}, {"$unset": {f"seasons.{parts[1]}": ""}})
        bot_instance.reply_to(message, f"✅ فصل {parts[1]} حذف شد")
        return

    if len(parts) == 3:
        anime_col.update_one({"name": anime}, {"$unset": {f"seasons.{parts[1]}.{parts[2]}": ""}})
        bot_instance.reply_to(message, f"✅ قسمت {parts[2]} فصل {parts[1]} حذف شد")

def echo_cmd(message):
    if not admin_check(message.from_user.id):
        return
    if not message.reply_to_message:
        return

    msg = message.reply_to_message
    for dialog in bot_instance.get_updates():
        try:
            bot_instance.copy_message(dialog.message.chat.id, msg.chat.id, msg.message_id)
        except Exception as e:
            print(f"[ECHO ERROR] {e}")

def echo_admin_cmd(message):
    if not admin_check(message.from_user.id):
        return
    if not message.reply_to_message:
        return

    msg = message.reply_to_message
    for admin in admin_check.__self__.find():
        try:
            bot_instance.copy_message(admin["user_id"], msg.chat.id, msg.message_id)
        except Exception as e:
            print(f"[ECHO_ADMIN ERROR] {e}")

def admin_list_cmd(message):
    if message.from_user.id != OWNER:
        return
    text = "💼 Admin List:\n"
    for admin in admin_check.__self__.find():
        text += f"user_id: {admin['user_id']}\n"
    bot_instance.reply_to(message, text)

def send_request_cmd(message):
    text = message.text.replace("/send_request", "").strip()
    if not text:
        bot_instance.reply_to(message, "⚠️ لطفاً متن درخواست خود را ارسال کنید")
        return
    bot_instance.send_message(
        OWNER,
        f"📩 درخواست/پیشنهاد از {message.from_user.id}:\n\n{text}"
    )
    bot_instance.reply_to(message, "✅ درخواست شما ارسال شد")

# =============================
# CALLBACK HANDLER
# =============================
def callback_handler(call):
    try:
        data = call.data.split(":")
        if data[0] == "anime":
            anime = data[1]
            info = get_anime(anime)
            if not info:
                bot_instance.answer_callback_query(call.id, "❌ انیمه موجود نیست")
                return

            if info.get("direct") and not info.get("seasons"):
                bot_instance.send_document(call.message.chat.id, info["direct"])
                return

            bot_instance.edit_message_text(
                f"{anime} - Seasons",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=season_keyboard(anime)
            )

        elif data[0] == "anime_page":
            page = int(data[1])
            bot_instance.edit_message_text(
                "📺 لیست انیمه‌ها:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=anime_keyboard(page)
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
            file_id = info.get("seasons", {}).get(season, {}).get(ep)
            if file_id:
                bot_instance.send_document(call.message.chat.id, file_id)
            else:
                bot_instance.answer_callback_query(call.id, "❌ فایل پیدا نشد")

        elif data[0] == "direct":
            anime = data[1]
            info = get_anime(anime)
            if info.get("direct"):
                bot_instance.send_document(call.message.chat.id, info["direct"])
            else:
                bot_instance.answer_callback_query(call.id, "❌ فایل پیدا نشد")
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")

# =============================
# REGISTER FUNCTION
# =============================
def register_anime_panel(bot, db, is_admin_func, owner_id):
    global anime_col, bot_instance, admin_check, OWNER

    bot_instance = bot
    anime_col = db["anime_panel"]
    admin_check = is_admin_func
    OWNER = owner_id

    # COMMANDS
    bot.message_handler(commands=["anime"])(anime_cmd)
    bot.message_handler(commands=["add_anime"])(add_anime_cmd)
    bot.message_handler(commands=["remov_anime"])(remove_anime_cmd)
    bot.message_handler(commands=["echo"])(echo_cmd)
    bot.message_handler(commands=["echo_admin"])(echo_admin_cmd)
    bot.message_handler(commands=["admin_list"])(admin_list_cmd)
    bot.message_handler(commands=["send_request"])(send_request_cmd)

    # CALLBACK
    bot.callback_query_handler(func=lambda call: True)(callback_handler)
