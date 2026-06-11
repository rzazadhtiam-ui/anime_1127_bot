# ================================================================
# self_welcome_fixed.py — نسخه کامل فیکس‌شده با تمام درخواست‌ها
# شامل: چک ادمین، پشتیبانی آیدی عددی، منطق چک وضعیت قبلی، لیست سکوت/بن گپ، متن پیش‌فرض خوش‌آمدگویی
# ================================================================

import asyncio
from datetime import datetime, timedelta

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest, GetFullChannelRequest, GetParticipantRequest
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantAdmin, ChannelParticipantCreator

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
# ENTITY SAFE + RESOLVE TARGET (پشتیبانی آیدی عددی و @یوزرنیم)
# ===========================================================
async def get_entities(client, chat_id, user_id=None):
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

async def resolve_target(event):
    """Resolve target from reply OR numeric ID OR @username"""
    # Reply priority
    rep = await event.get_reply_message()
    if rep and getattr(rep, "sender_id", None):
        try:
            return await event.client.get_entity(rep.sender_id)
        except:
            pass

    # From args (supports .command ID or .command @user)
    text = (event.raw_text or "").strip()
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        return None

    target_str = parts[1].strip()
    if target_str.isdigit():
        try:
            return await event.client.get_entity(int(target_str))
        except:
            return None
    elif target_str.startswith("@"):
        try:
            return await event.client.get_entity(target_str)
        except:
            return None
    return None

async def is_group_admin(client, chat_id, user_id):
    """Check if user is admin/creator in the group"""
    try:
        participant = await client(GetParticipantRequest(chat_id, user_id))
        p = getattr(participant, "participant", None)
        if p is None:
            return False
        return isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except:
        return False

# ================= OWNER CHECK =================
def owner_only(event, owner_id):
    return owner_id and event.sender_id == owner_id

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
        return False
    rights = ChatBannedRights(
        send_messages=False, send_media=False, send_stickers=False,
        send_gifs=False, send_games=False, send_inline=False,
        send_polls=False, change_info=False, invite_users=False,
        pin_messages=False, until_date=None
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

# ================= WELCOME ENGINE =================
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
    except:
        return 0

def escape_markdown(text: str):
    if not text:
        return ""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

async def welcome_new_user(client, event):
    if not (event.user_joined or event.user_added):
        return

    settings = get_group_welcome(event.chat_id)
    if not settings["status"]:
        return

    # متن پیش‌فرض اگر کاربر متنی تنظیم نکرده باشد
    DEFAULT_WELCOME = "خوش آمدی {منشن_کاربر} 👋\nبه گروه {نام_گروه} خوش اومدی!"
    template = settings["text"] or DEFAULT_WELCOME

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
            await event.reply("\n".join([t.replace("[", "").replace("]", "") for t in texts]))

# ================= REGISTER HANDLERS =================
def register_group_handlers(client, owner_id):

    @client.on(events.ChatAction)
    async def welcome_handler(event):
        await welcome_new_user(client, event)

    # ---------- سکوت گپ (با چک ادمین + آیدی + منطق قبلاً بودن) ----------
    @client.on(events.NewMessage)
    @multi_lang([".سکوت گپ", ".mute group", ".mute gap"])
    async def mute_handler(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید. دستور اعمال نشد.")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "باید روی کاربر ریپلای کنی یا آیدی/یوزرنیم وارد کنی")

        muted_list = db.get_muted_users(event.chat_id)
        if user.id in muted_list:
            return await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) قبلاً سکوت شده بود.**")

        delta, val, unit, reason = parse_time_and_reason(event.ml_args or "")
        ok = await mute_user(client, event.chat_id, user.id, delta)
        if not ok:
            return await edit_auto(event, "❌ خطا در سکوت کردن")

        db.add_muted_user(event.chat_id, user.id)
        mention = f"[{safe_name(user)}](tg://user?id={user.id})"
        if val:
            msg = f"**کاربر {mention} به مدت {val} {unit} به دلیل {reason or 'نامشخص'} سکوت شد.**"
        else:
            msg = f"**کاربر {mention} سکوت شد.**"
        await edit_auto(event, msg)

    # ---------- حذف سکوت گپ ----------
    @client.on(events.NewMessage)
    @multi_lang([".حذف سکوت گپ", ".unmute group"])
    async def unmute_handler(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید. دستور اعمال نشد.")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "باید روی کاربر ریپلای کنی یا آیدی/یوزرنیم وارد کنی")

        muted_list = db.get_muted_users(event.chat_id)
        if user.id not in muted_list:
            return await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) از قبل سکوت نبوده است.**")

        ok = await unmute_user(client, event.chat_id, user.id)
        if ok:
            db.remove_muted_user(event.chat_id, user.id)
            await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) از سکوت خارج شد.**")
        else:
            await edit_auto(event, "❌ خطا در حذف سکوت")

    # ---------- بن (با تمام فیکس‌ها) ----------
    @client.on(events.NewMessage)
    @multi_lang([".بن", ".bun"])
    async def ban_handler(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید. دستور اعمال نشد.")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "باید روی کاربر ریپلای کنی یا آیدی/یوزرنیم وارد کنی")

        banned_list = db.get_banned_users(event.chat_id)
        if user.id in banned_list:
            return await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) قبلاً بن شده بود.**")

        delta, val, unit, reason = parse_time_and_reason(event.ml_args or "")
        ok = await ban_user(client, event.chat_id, user.id, delta)
        if not ok:
            return await edit_auto(event, "❌ خطا در بن کردن")

        db.add_banned_user(event.chat_id, user.id)
        mention = f"[{safe_name(user)}](tg://user?id={user.id})"
        if val:
            msg = f"**کاربر {mention} برای {val} {unit} بن شد.**"
            if reason:
                msg += f"\nدلیل: {reason}"
        else:
            msg = f"**کاربر {mention} بن شد.**"
        await edit_auto(event, msg)

    # ---------- حذف بن ----------
    @client.on(events.NewMessage)
    @multi_lang([".حذف بن", ".unban"])
    async def unban_handler(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید. دستور اعمال نشد.")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "باید روی کاربر ریپلای کنی یا آیدی/یوزرنیم وارد کنی")

        banned_list = db.get_banned_users(event.chat_id)
        if user.id not in banned_list:
            return await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) از قبل بن نبوده است.**")

        ok = await unban_user(client, event.chat_id, user.id)
        if ok:
            db.remove_banned_user(event.chat_id, user.id)
            await edit_auto(event, f"**کاربر {safe_name(user)} ({user.id}) از بن خارج شد.**")
        else:
            await edit_auto(event, "❌ خطا در حذف بن")

    # ---------- لیست سکوت گپ ----------
    @client.on(events.NewMessage)
    @multi_lang([".لیست سکوت گپ", ".muted list gap"])
    async def list_muted_gap(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید.")

        muted = db.get_muted_users(event.chat_id)
        if not muted:
            return await edit_auto(event, "**هیچ کاربری در این گروه سکوت نشده است.**")

        text = "**🔇 لیست کاربران سکوت‌شده در گروه:**\n\n"
        for uid in muted:
            try:
                u = await client.get_entity(uid)
                text += f"• {safe_name(u)} (`{uid}`)\n"
            except:
                text += f"• `{uid}`\n"
        await edit_auto(event, text)

    # ---------- لیست بن ----------
    @client.on(events.NewMessage)
    @multi_lang([".لیست بن", ".ban list"])
    async def list_banned(event):
        if not owner_only(event, owner_id):
            return
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید.")

        banned = db.get_banned_users(event.chat_id)
        if not banned:
            return await edit_auto(event, "**هیچ کاربری در این گروه بن نشده است.**")

        text = "**🚫 لیست کاربران بن‌شده در گروه:**\n\n"
        for uid in banned:
            try:
                u = await client.get_entity(uid)
                text += f"• {safe_name(u)} (`{uid}`)\n"
            except:
                text += f"• `{uid}`\n"
        await edit_auto(event, text)

    # ---------- پین و حذف پین (کوتاه) ----------
    @client.on(events.NewMessage)
    @multi_lang([".پین", ".pin"])
    async def pin_handler(event):
        if not owner_only(event, owner_id):
            return
        rep = await event.get_reply_message()
        if not rep:
            return
        await pin_msg(client, event.chat_id, rep.id)
        await edit_auto(event, "**پیام پین شد.**")

    @client.on(events.NewMessage)
    @multi_lang([".حذف پین", ".unpin"])
    async def unpin_handler(event):
        if not owner_only(event, owner_id):
            return
        rep = await event.get_reply_message()
        if not rep:
            return
        await unpin_msg(client, event.chat_id, rep.id)
        await edit_auto(event, "**پیام آنپین شد.**")

    # ---------- نوع چت ----------
    @client.on(events.NewMessage(pattern=r"^\.type$"))
    async def chat_type_cmd(event):
        chat_type = await get_chat_type(event)
        types_text = {
            "supergroup": "🧩 این چت سوپرگروه است",
            "group": "👥 این چت گروه معمولی است",
            "channel": "📢 این چت کانال است",
            "pv": "💬 این چت خصوصی است",
        }
        await edit_auto(event, types_text.get(chat_type, "❓ نوع چت مشخص نشد"))

    # ---------- خوشامدگویی روشن/خاموش + تنظیم + وضعیت ----------
    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی روشن", ".welcome on"])
    async def welcome_on(event):
        if not owner_only(event, owner_id):
            return
        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], True)
        await edit_auto(event, "**سیستم خوش‌آمدگویی فعال شد ✅**")

    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی خاموش", ".welcome off"])
    async def welcome_off(event):
        if not owner_only(event, owner_id):
            return
        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], False)
        await edit_auto(event, "**سیستم خوش‌آمدگویی غیرفعال شد ❌**")

    @client.on(events.NewMessage)
    @multi_lang([".تنظیم خوشامدگویی", ".set welcome"])
    async def set_welcome(event):
        if not owner_only(event, owner_id):
            return
        text = event.ml_args or ""
        if not text:
            return await edit_auto(event, "بعد از دستور، متن خوش‌آمد را بنویس")
        set_group_welcome(event.chat_id, text, True)
        await edit_auto(event, "**متن خوش‌آمد ذخیره و فعال شد ✅**")

    @client.on(events.NewMessage)
    @multi_lang([".وضعیت خوشامدگویی", ".welcome status"])
    async def welcome_status(event):
        if not owner_only(event, owner_id):
            return
        settings = get_group_welcome(event.chat_id)
        status = "فعال ✅" if settings["status"] else "غیرفعال ❌"
        text = settings["text"] or "متن پیش‌فرض استفاده می‌شود"
        await edit_auto(event, f"**وضعیت:** {status}\n\n**متن فعلی:**\n{text}")

print("✅ self_welcome_fixed.py کاملاً بازسازی شد با تمام درخواست‌ها")
