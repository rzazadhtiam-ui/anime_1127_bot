import asyncio
from datetime import datetime, timedelta

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest, GetFullChannelRequest
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import ChatBannedRights

from self_storage import Storage
from multi_lang import multi_lang, edit_auto, reply_auto

db = Storage()

# ================= TIME SYSTEM =================
TIME_UNITS = {
    "دقیقه": 60,
    "ساعت": 3600,
    "روز": 86400,
    "هفته": 604800,
    "ماه": 2592000,
    "سال": 31536000,
}

# ================= UTIL =================
def safe_name(user):
    if not user:
        return "کاربر"
    return user.first_name or "کاربر"

# ===========================================================
# ENTITY SAFE
# ===========================================================
async def get_entities(client, chat_id, user_id=None):
    """
    این تابع هم چت و هم کاربر (اگر user_id داده شده) را برمی‌گرداند
    """
    chat = await client.get_entity(chat_id)

    user = None
    if user_id:
        try:
            user = await client.get_entity(user_id)
        except Exception:
            user = None

    return chat, user
    

def parse_time_and_reason(args):
    if not args:
        return None, None, None, ""
    parts = args.strip().split()
    if not parts[0].isdigit():
        return None, None, None, args
    val = int(parts[0])
    if len(parts) >= 2 and parts[1] in TIME_UNITS:
        unit = parts[1]
        delta = timedelta(seconds=val * TIME_UNITS[unit])
        reason = " ".join(parts[2:])
    else:
        unit = "دقیقه"
        delta = timedelta(minutes=val)
        reason = " ".join(parts[1:])
    return delta, val, unit, reason

# ================= OWNER CHECK =================
def owner_only(event, owner_id):
    return owner_id and event.sender_id == owner_id

# ================= ENTITY SAFE =================
# ================= ENTITY SAFE =================
async def get_target_user(event):
    rep = await event.get_reply_message()
    if not rep:
        return None
    # اگر پیام یک لیست باشه (TotalList) یا sender نداشته باشه
    try:
        if hasattr(rep, "sender") and rep.sender:
            return rep.sender
        if hasattr(rep, "from_id") and rep.from_id:
            return await event.client.get_entity(rep.from_id.user_id if hasattr(rep.from_id, "user_id") else rep.from_id)
    except:
        pass
    # fallback آخر
    try:
        return await event.client.get_entity(rep.peer_id.user_id)
    except:
        return None

# ================= TELEGRAM ACTIONS =================
async def mute_user(client, chat_id, user_id, delta):
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        if delta is None:
            delta = timedelta(days=3650)
        rights = ChatBannedRights(send_messages=True, until_date=datetime.utcnow() + delta)
        await client(EditBannedRequest(chat, user, rights))
        return True
    except:
        return False

async def unmute_user(client, chat_id, user_id):
    chat, user = await get_entities(client, chat_id, user_id)
    
    if not getattr(chat, "megagroup", False):
        return False  # فقط سوپرگروپ‌ها قابل سکوت/آن‌سکوت هستن
    
    rights = ChatBannedRights(
        send_messages=False,
        send_media=False,
        send_stickers=False,
        send_gifs=False,
        send_games=False,
        send_inline=False,
        send_polls=False,
        change_info=False,
        invite_users=False,
        pin_messages=False,
        until_date=None
    )
    await client(EditBannedRequest(chat, user, rights))
    return True
        
        

async def ban_user(client, chat_id, user_id, delta):
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        if delta is None:
            delta = timedelta(days=3650)
        rights = ChatBannedRights(view_messages=True, until_date=datetime.utcnow() + delta)
        await client(EditBannedRequest(chat, user, rights))
        return True
    except:
        return False

async def unban_user(client, chat_id, user_id):
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        rights = ChatBannedRights(view_messages=False)
        await client(EditBannedRequest(chat, user, rights))
        return True
    except:
        return False

async def lock_group(client, chat_id, delta):
    try:
        chat = await client.get_entity(chat_id)
        if delta is None:
            delta = timedelta(days=3650)
        rights = ChatBannedRights(send_messages=True, until_date=datetime.utcnow() + delta)
        await client(EditBannedRequest(chat, None, rights))
        return True
    except:
        return False

async def unlock_group(client, chat_id):
    try:
        chat = await client.get_entity(chat_id)
        rights = ChatBannedRights(send_messages=False)
        await client(EditBannedRequest(chat, None, rights))
        return True
    except:
        return False

async def pin_msg(client, chat_id, msg_id):
    await client(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, silent=False))

async def unpin_msg(client, chat_id, msg_id):
    await client(UpdatePinnedMessageRequest(peer=chat_id, id=msg_id, unpin=True))

async def timed_unpin(client, chat_id, msg_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await unpin_msg(client, chat_id, msg_id)
    except:
        pass

# ================= WELCOME ENGINE (FIXED) =================

def get_group_welcome(chat_id):
    return {
        "status": bool(db.get_group_key(chat_id, "welcome_enabled")),
        "text": db.get_group_key(chat_id, "welcome_message") or ""
    }

def set_group_welcome(chat_id, text, status):
    db.set_group_key(chat_id, "welcome_message", text or "")
    db.set_group_key(chat_id, "welcome_enabled", bool(status))


async def get_member_count(client, chat_id):
    try:
        full = await client(GetFullChannelRequest(chat_id))
        return getattr(full.full_chat, "participants_count", 0) or 0
    except Exception:
        return 0


def escape_markdown(text: str):
    if not text:
        return ""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text


async def welcome_new_user(client, event):
    if not (event.user_joined or event.user_added):
        return

    settings = get_group_welcome(event.chat_id)
    if not settings["status"]:
        return

    template = settings["text"] or "خوش آمدی {منشن_کاربر} 👋"

    try:
        chat = await event.get_chat()
        group_name = escape_markdown(getattr(chat, "title", "گروه"))
    except:
        group_name = "گروه"

    member_count = await get_member_count(client, event.chat_id)

    try:
        users = await event.get_users()
    except:
        return

    texts = []

    for user in users:
        if not user:
            continue

        name = escape_markdown(safe_name(user))
        mention = f"[{name}](tg://user?id={user.id})"

        text = template \
            .replace("{منشن_کاربر}", mention) \
            .replace("{نام_کاربر}", name) \
            .replace("{نام_گروه}", group_name) \
            .replace("{شماره_ورودی}", str(member_count))

        texts.append(text)

    if texts:
        try:
            await event.reply("\n".join(texts), parse_mode="md")
        except:
            # اگر markdown خطا داد، ساده بفرست
            await event.reply("\n".join([t.replace("[", "").replace("]", "") for t in texts]))
# ================= CHAT TYPE =================
async def get_chat_type(event):
    chat = await event.get_chat()
    if getattr(chat, "megagroup", False):
        return "supergroup"
    if event.is_group:
        return "group"
    if event.is_channel:
        return "channel"
    if event.is_private:
        return "pv"
    return "unknown"

# ================= REGISTER HANDLERS =================
def register_group_handlers(client, owner_id):

    @client.on(events.ChatAction)
    async def welcome_handler(event):
        await welcome_new_user(client, event)

    # ---------- سکوت ----------
    @client.on(events.NewMessage)
    @multi_lang([".سکوت گپ", ".mute group", ".mute gap"])
    async def mute_handler(event):
        if not owner_only(event, owner_id):
            return

    # گرفتن کاربر هدف
        rep = await event.get_reply_message()
        if not rep:
            return await edit_auto(event, "باید روی کاربر ریپلای کنی")

        user = await rep.get_sender()

    # گرفتن زمان و دلیل، اگر نبود delta = None
        delta, val, unit, reason = parse_time_and_reason(event.ml_args)

    # اگر delta None بود، سکوت نامحدود
        await mute_user(client, event.chat_id, user.id, delta)

        mention = f"[{user.first_name}](tg://user?id={user.id})"

        if val:
            if reason:
                msg = f"کاربر {mention} به مدت {val} {unit} به دلیل {reason} سکوت شد"
            else:
                msg = f"کاربر {mention} به مدت {val} {unit} سکوت شد"
        else:
            msg = f"کاربر {mention} سکوت شد "

        await edit_auto(event, msg)

    # ---------- حذف سکوت ----------
    @client.on(events.NewMessage)
    @multi_lang([".حذف سکوت گپ", ".unmute group"])
    async def unmute_handler(event):
        if not owner_only(event, owner_id):
            return
        user = await get_target_user(event)
        if not user:
            return
        await unmute_user(client, event.chat_id, user.id)
        await edit_auto(event, "کاربر آزاد شد")

    # ---------- بن ----------
    @client.on(events.NewMessage)
    @multi_lang([".بن", ".bun"])
    async def ban_handler(event):
        if not owner_only(event, owner_id):
            return
        user = await get_target_user(event)
        if not user:
            return await edit_auto(event, "روی کاربر ریپلای کن")
        delta, val, unit, reason = parse_time_and_reason(event.ml_args)
        ok = await ban_user(client, event.chat_id, user.id, delta)
        if not ok:
            return await edit_auto(event, "خطا در بن")
        mention = f"[{safe_name(user)}](tg://user?id={user.id})"
        msg = f"کاربر {mention} بن شد"
        if val:
            msg = f"کاربر {mention} برای {val} {unit} بن شد"
            if reason:
                msg += f"\nدلیل: {reason}"
        await edit_auto(event, msg)

    # ---------- حذف بن ----------
    @client.on(events.NewMessage)
    @multi_lang([".حذف بن", ".unban"])
    async def unban_handler(event):
        if not owner_only(event, owner_id):
            return
        user = await get_target_user(event)
        if not user:
            return
        await unban_user(client, event.chat_id, user.id)
        await edit_auto(event, "کاربر آنبن شد")

    # ---------- پین ----------
    @client.on(events.NewMessage)
    @multi_lang([".پین", ".pin"])
    async def pin_handler(event):
        if not owner_only(event, owner_id):
            return
        rep = await event.get_reply_message()
        if not rep:
            return
        delta, val, unit, _ = parse_time_and_reason(event.ml_args)
        await pin_msg(client, event.chat_id, rep.id)
        if val:
            seconds = val * TIME_UNITS[unit]
            asyncio.create_task(timed_unpin(client, event.chat_id, rep.id, seconds))
            await reply_auto(event, f"پیام برای {val} {unit} پین شد")
        else:
            await edit_auto(event, "پیام پین شد")

    # ---------- حذف پین ----------
    @client.on(events.NewMessage)
    @multi_lang([".حذف پین", ".unpin"])
    async def unpin_handler(event):
        if not owner_only(event, owner_id):
            return
        rep = await event.get_reply_message()
        if not rep:
            return
        await unpin_msg(client, event.chat_id, rep.id)
        await edit_auto(event, "پیام آنپین شد")

    # ---------- دستور نوع چت ----------
    @client.on(events.NewMessage(pattern=r"\.type$"))
    async def chat_type_cmd(event):
        chat_type = await get_chat_type(event)
        types_text = {
            "supergroup": "🧩 این چت سوپرگروه است",
            "group": "👥 این چت گروه معمولی است",
            "channel": "📢 این چت کانال است",
            "pv": "💬 این چت خصوصی است",
            "unknown": "❓ نوع چت مشخص نشد"
        }
        await event.edit(types_text.get(chat_type, "❓ نامشخص"))

# ================= WELCOME COMMANDS =================

    # فعال کردن خوش‌آمد
    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی روشن", ".welcome on"])
    async def welcome_on(event):
        if not owner_only(event, owner_id):
            return

        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], True)

        await edit_auto(event, "سیستم خوش‌آمد فعال شد ✅")


    # غیرفعال کردن خوش‌آمد
    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی خاموش", ".welcome off"])
    async def welcome_off(event):
        if not owner_only(event, owner_id):
            return

        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], False)

        await edit_auto(event, "سیستم خوش‌آمد غیرفعال شد ❌")


    # تنظیم متن خوش‌آمد
    @client.on(events.NewMessage)
    @multi_lang([".متن خوشامدگویی", ".set welcome"])
    async def set_welcome(event):
        if not owner_only(event, owner_id):
            return

        text = event.ml_args
        if not text:
            return await edit_auto(event, "بعد از دستور، متن خوش‌آمد را بنویس")

        set_group_welcome(event.chat_id, text, True)

        await edit_auto(event, "متن خوش‌آمد ذخیره و فعال شد ✅")


    # مشاهده وضعیت خوش‌آمد
    @client.on(events.NewMessage)
    @multi_lang([".نمایش خوشامدگویی", ".welcome status"])
    async def welcome_status(event):
        if not owner_only(event, owner_id):
            return

        settings = get_group_welcome(event.chat_id)

        status = "فعال ✅" if settings["status"] else "غیرفعال ❌"
        text = settings["text"] or "تنظیم نشده"

        msg = f"وضعیت: {status}\n\nمتن:\n{text}"
        await edit_auto(event, msg)
