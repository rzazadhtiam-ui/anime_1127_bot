# ===========================================================
# self_GroupTools.py — FINAL STABLE OWNER VERSION
# ===========================================================

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest, GetFullChannelRequest
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import ChatBannedRights
from self_storage import Storage

db = Storage()

OWNER_ID = None


# ==============================
# OWNER CHECK SAFE
# ==============================
def owner_only(event):
    if OWNER_ID is None:
        return False
    return event.sender_id == OWNER_ID


# ==============================
# WELCOME SETTINGS
# ==============================
def get_group_welcome(chat_id):
    return {
        "status": db.get_group_key(chat_id, "welcome_enabled"),
        "text": db.get_group_key(chat_id, "welcome_message")
    }

def set_group_welcome(chat_id, text, status):
    db.set_group_key(chat_id, "welcome_message", text)
    db.set_group_key(chat_id, "welcome_enabled", status)


# ==============================
# USER STATUS
# ==============================
def add_silenced_user(chat_id, user_id):
    db.set_group_user_key(chat_id, user_id, "mute", True)

def remove_silenced_user(chat_id, user_id):
    db.set_group_user_key(chat_id, user_id, "mute", False)

def add_blocked_user(chat_id, user_id):
    db.set_group_user_key(chat_id, user_id, "ban", True)

def remove_blocked_user(chat_id, user_id):
    db.set_group_user_key(chat_id, user_id, "ban", False)


# ==============================
# TELEGRAM ACTIONS SAFE
# ==============================
async def mute_user(client, chat_id, user_id):
    rights = ChatBannedRights(send_messages=True)
    await client(EditBannedRequest(chat_id, user_id, rights))
    add_silenced_user(chat_id, user_id)

async def unmute_user(client, chat_id, user_id):
    rights = ChatBannedRights()
    await client(EditBannedRequest(chat_id, user_id, rights))
    remove_silenced_user(chat_id, user_id)

async def ban_user(client, chat_id, user_id):
    rights = ChatBannedRights(view_messages=True)
    await client(EditBannedRequest(chat_id, user_id, rights))
    add_blocked_user(chat_id, user_id)

async def unban_user(client, chat_id, user_id):
    rights = ChatBannedRights(until_date=None)
    await client(EditBannedRequest(chat_id, user_id, rights))
    remove_blocked_user(chat_id, user_id)

async def pin_message(client, chat_id, msg_id):
    try:
        await client(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, silent=False))
    except:
        pass

async def unpin_message(client, chat_id, msg_id):
    try:
        await client(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, unpin=True))
    except:
        pass


# ==============================
# GET GROUP MEMBER COUNT
# ==============================
async def get_member_count(client, chat_id):
    try:
        full = await client(GetFullChannelRequest(chat_id))
        return full.full_chat.participants_count
    except:
        return 0


# ==============================
# WELCOME ENGINE FINAL
# ==============================
async def welcome_new_user(client, event):
    try:
        if not (event.user_joined or event.user_added):
            return

        settings = get_group_welcome(event.chat_id)
        if not settings.get("status"):
            return

        text_template = settings.get("text") or "خوش آمدید"

        chat = await event.get_chat()
        group_name = getattr(chat, "title", "گروه")

        member_count = await get_member_count(client, event.chat_id)

        users = await event.get_users()

        mentions = []

        for user in users:

            mention = f"[{user.first_name}](tg://user?id={user.id})"
            username = f"@{user.username}" if user.username else "ندارد"

            text = text_template

            text = text.replace("{منشن_کاربر}", mention)
            text = text.replace("{نام_کاربر}", user.first_name or "")
            text = text.replace("{ایدی_کاربر}", username)
            text = text.replace("{ایدی_عددی_کاربر}", str(user.id))
            text = text.replace("{نام_گروه}", group_name)
            text = text.replace("{شماره_ورودی}", str(member_count))

            mentions.append(text)

        final_text = "\n".join(mentions)
        await event.reply(final_text, link_preview=False)

    except Exception as e:
        print("WELCOME ERROR:", e)


# ==============================
# HANDLERS
# ==============================
def register_group_handlers(client, owner_id):
    global OWNER_ID
    OWNER_ID = owner_id


    @client.on(events.ChatAction)
    async def welcome_handler(event):
        await welcome_new_user(client, event)


    @client.on(events.NewMessage(pattern=r"^\..+"))
    async def commands(event):

        if not owner_only(event):
            return

        chat_id = event.chat_id
        msg = event.raw_text.strip()

        commands_reply = {
            ".سکوت گپ": "mute",
            ".حذف سکوت گپ": "unmute",
            ".بن": "ban",
            ".حذف بن": "unban",
            ".پین": "pin",
            ".حذف پین": "unpin"
        }

        commands_no_reply = [
            ".خوشامدگویی روشن",
            ".خوشامدگویی خاموش",
            ".متن خوشامدگویی",
            ".نمایش خوشامدگویی",
            ".ریست خوشامدگویی"
        ]

        # =========================
        # COMMANDS WITH REPLY
        # =========================
        if msg in commands_reply:

            rep = await event.get_reply_message()
            if not rep:
                return await event.reply("روی پیام کاربر ریپلای کن")

            user = await rep.get_sender()
            user_id = user.id
            action = commands_reply[msg]

            if action == "mute":
                await mute_user(client, chat_id, user_id)
                await event.reply(f"{user.first_name} سکوت شد")

            elif action == "unmute":
                await unmute_user(client, chat_id, user_id)
                await event.reply(f"{user.first_name} آزاد شد")

            elif action == "ban":
                await ban_user(client, chat_id, user_id)
                await event.reply(f"{user.first_name} بن شد")

            elif action == "unban":
                await unban_user(client, chat_id, user_id)
                await event.reply(f"{user.first_name} آنبن شد")

            elif action == "pin":
                await pin_message(client, chat_id, rep.id)
                await event.reply("پین شد")

            elif action == "unpin":
                await unpin_message(client, chat_id, rep.id)
                await event.reply("آنپین شد")

        # =========================
        # COMMANDS WITHOUT REPLY
        # =========================
        elif any(msg.startswith(cmd) for cmd in commands_no_reply):

            if msg.startswith(".متن خوشامدگویی"):
                text = msg.replace(".متن خوشامدگویی", "").strip()
                current = get_group_welcome(chat_id)
                set_group_welcome(chat_id, text, current.get("status", False))
                await event.reply("متن ذخیره شد")

            elif msg == ".خوشامدگویی روشن":
                current = get_group_welcome(chat_id)
                set_group_welcome(chat_id, current.get("text", ""), True)
                await event.reply("روشن شد")

            elif msg == ".خوشامدگویی خاموش":
                current = get_group_welcome(chat_id)
                set_group_welcome(chat_id, current.get("text", ""), False)
                await event.reply("خاموش شد")

            elif msg == ".نمایش خوشامدگویی":
                current = get_group_welcome(chat_id)
                await event.reply(current.get("text", "ثبت نشده"))

            elif msg == ".ریست خوشامدگویی":
                set_group_welcome(chat_id, "", False)
                await event.reply("ریست شد")
