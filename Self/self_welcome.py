# ===========================================================
# self_GroupTools.py — ماژول مدیریت گروه اصلاح شده
# ===========================================================

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest, GetParticipantsRequest
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantsAdmins
from self_storage import Storage

# کانکتور دیتابیس MongoDB سبک و چند اکانته
db = Storage()

# ==============================
# تنظیمات خوشامدگویی
# ==============================
def get_group_welcome(chat_id):
    return {
        "welcome_status": db.get_group_key(chat_id, "welcome_enabled"),
        "welcome_text": db.get_group_key(chat_id, "welcome_message")
    }

def set_group_welcome(chat_id, text, status):
    db.set_group_key(chat_id, "welcome_message", text)
    db.set_group_key(chat_id, "welcome_enabled", status)

# ==============================
# وضعیت کاربران
# ==============================
def add_silenced_user(user_id):
    db.set_user_key(user_id, "silence", "is_silenced", True)

def remove_silenced_user(user_id):
    db.set_user_key(user_id, "silence", "is_silenced", False)

def add_blocked_user(user_id):
    db.set_user_key(user_id, "block", "is_blocked", True)

def remove_blocked_user(user_id):
    db.set_user_key(user_id, "block", "is_blocked", False)

# ==============================
# توابع کمکی
# ==============================
async def mute_user(bot, chat_id, user_id):
    rights = ChatBannedRights(until_date=None, send_messages=True)
    await bot(EditBannedRequest(chat_id, user_id, rights))
    add_silenced_user(user_id)

async def unmute_user(bot, chat_id, user_id):
    rights = ChatBannedRights(until_date=None, send_messages=False)
    await bot(EditBannedRequest(chat_id, user_id, rights))
    remove_silenced_user(user_id)

async def ban_user(bot, chat_id, user_id):
    rights = ChatBannedRights(until_date=None, view_messages=True)
    await bot(EditBannedRequest(chat_id, user_id, rights))
    add_blocked_user(user_id)

async def unban_user(bot, chat_id, user_id):
    rights = ChatBannedRights(until_date=0, send_messages=False, view_messages=False)
    await bot(EditBannedRequest(chat_id, user_id, rights))
    remove_blocked_user(user_id)

async def pin_message(bot, chat_id, msg_id):
    await bot(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, silent=False))

async def unpin_message(bot, chat_id, msg_id):
    await bot(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, silent=False, unpin=True))

async def get_admins(bot, chat_id):
    admins = await bot(GetParticipantsRequest(
        channel=chat_id,
        filter=ChannelParticipantsAdmins(),
        offset=0,
        limit=300
    ))
    return admins.participants

# ==============================
# خوشامدگویی کاربران جدید
# ==============================
async def welcome_new_user(bot, event):
    chat_id = event.chat_id
    group_settings = get_group_welcome(chat_id)
    if not group_settings.get("welcome_status", False):
        return
    if event.user_added or event.user_joined:
        user = await event.get_user()
        text = group_settings.get("welcome_text", "به گروه خوش آمدید!")
        await event.reply(f"{user.first_name} عزیز، {text}")

# ==============================
# هندلر دستورات گروه
# ==============================
def register_group_handlers(client):
    # خوشامدگویی هنگام ورود
    client.on(events.ChatAction)(lambda event: welcome_new_user(client, event))

    @client.on(events.NewMessage(pattern=r"^\..+"))
    async def cmd_handler(event):
        chat_id = event.chat_id
        msg = event.raw_text.strip()

        # دستورات ریپلای‌دار
        commands_with_reply = {
            ".سکوت گپ": "mute",
            ".حذف سکوت گپ": "unmute",
            ".بن": "ban",
            ".حذف بن": "unban",
            ".پین": "pin",
            ".حذف پین": "unpin"
        }

        # دستورات بدون ریپلای
        commands_no_reply = {
            ".خوشامدگویی روشن": "welcome_on",
            ".خوشامدگویی خاموش": "welcome_off",
            ".متن خوشامدگویی": "set_welcome_text",
            ".نمایش خوشامدگویی": "show_welcome",
            ".ریست خوشامدگویی": "reset_welcome"
        }

        # اجرای دستورات ریپلای‌دار
        if msg in commands_with_reply:
            rep = await event.get_reply_message()
            if not rep:
                return await event.reply("⚠️ لطفاً روی پیام کاربر ریپلای کنید.")
            user_id = rep.sender_id
            action = commands_with_reply[msg]

            if action == "mute":
                await mute_user(client, chat_id, user_id)
                await event.edit(f"کاربر {rep.sender.first_name} سکوت شد ✔️")
            elif action == "unmute":
                await unmute_user(client, chat_id, user_id)
                await event.edit(f"سکوت کاربر {rep.sender.first_name} حذف شد ✔️")
            elif action == "ban":
                await ban_user(client, chat_id, user_id)
                await event.edit(f"کاربر {rep.sender.first_name} بن شد 🚫")
            elif action == "unban":
                await unban_user(client, chat_id, user_id)
                await event.edit(f"بن کاربر {rep.sender.first_name} حذف شد ✔️")
            elif action == "pin":
                await pin_message(client, chat_id, rep.id)
                await event.edit("پیام پین شد ✔️")
            elif action == "unpin":
                await unpin_message(client, chat_id, rep.id)
                await event.edit("پیام پین حذف شد ✔️")

        # اجرای دستورات بدون ریپلای
        elif any(msg.startswith(cmd) for cmd in commands_no_reply):
            if msg.startswith(".متن خوشامدگویی"):
                text = msg.replace(".متن خوشامدگویی", "").strip()
                set_group_welcome(chat_id, text, get_group_welcome(chat_id).get("welcome_status", False))
                await event.edit("متن خوشامد ثبت شد ✔️")
            elif msg == ".خوشامدگویی روشن":
                txt = get_group_welcome(chat_id).get("welcome_text", "")
                set_group_welcome(chat_id, txt, True)
                await event.edit("خوشامدگویی روشن شد ✔️")
            elif msg == ".خوشامدگویی خاموش":
                txt = get_group_welcome(chat_id).get("welcome_text", "")
                set_group_welcome(chat_id, txt, False)
                await event.edit("خوشامدگویی خاموش شد ❌")
            elif msg == ".نمایش خوشامدگویی":
                txt = get_group_welcome(chat_id).get("welcome_text", "هیچ متنی ثبت نشده است.")
                await event.edit(f"متن خوشامدگویی:\n{txt}")
            elif msg == ".ریست خوشامدگویی":
                set_group_welcome(chat_id, "", False)
                await event.edit("خوشامدگویی ریست شد ✔️")
