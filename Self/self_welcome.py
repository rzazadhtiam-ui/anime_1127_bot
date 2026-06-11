# ================================================================
# self_welcome.py - سیستم مدیریت گروه - نسخه درست شده
# ================================================================

import asyncio
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantAdmin, ChannelParticipantCreator
from self_storage import Storage
from multi_lang import multi_lang, edit_auto, reply_auto
from telethon.tl.types import ChannelParticipantsKicked
db = Storage()

# ================================================================
# CONSTANTS
# ================================================================

TIME_UNITS = {
    "دقیقه": 60, 
    "ساعت": 3600, 
    "روز": 86400,
    "هفته": 604800, 
    "ماه": 2592000, 
    "سال": 31536000,
}

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def safe_name(user):
    """نام کاربر را با احتیاط بگیر"""
    if not user:
        return "کاربر"
    return user.first_name or "کاربر"


async def resolve_target(event):
    """کاربر هدف را برای دستورات تعیین کن (ریپلای یا آیدی)"""
    # اگر ریپلای بود
    rep = await event.get_reply_message()
    if rep and getattr(rep, "sender_id", None):
        try:
            return await event.client.get_entity(rep.sender_id)
        except:
            pass

    # اگر آیدی یا یوزرنیم در دستور بود
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
    """بررسی کن کاربر ادمین گروه است یا نه"""
    try:
        participant = await client(GetParticipantRequest(chat_id, user_id))
        p = getattr(participant, "participant", None)
        return isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except:
        return False


def owner_only(event, owner_id):
    """فقط صاحب اکانت"""
    return owner_id and event.sender_id == owner_id


def parse_time_and_reason(args):
    """زمان و دلیل را از آرگومان‌ها پارس کن"""
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


# ================================================================
# TELEGRAM ACTIONS
# ================================================================

async def mute_user(client, chat_id, user_id, delta):
    """کاربر را سکوت کن"""
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
    """سکوت کاربر را برطرف کن"""
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        
        # تمام محدودیت‌ها را برطرف کن
        rights = ChatBannedRights(
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            send_polls=False,
            embed_links=False,
            pin_messages=False,
            invite_users=False,
            change_info=False,
        )
        await client(EditBannedRequest(chat, user, rights))
        return True
    except:
        return False


async def ban_user(client, chat_id, user_id, delta):
    """کاربر را بن کن"""
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
    """بن کاربر را برطرف کن"""
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        
        rights = ChatBannedRights(view_messages=False)
        await client(EditBannedRequest(chat, user, rights))
        return True
    except:
        return False


from telethon.tl.functions.channels import EditBannedRequest

# ================================================================
# WELCOME SYSTEM (Database-based)
# ================================================================

def get_group_welcome(chat_id):
    """تنظیمات خوش‌آمد را برای گروه بگیر"""
    return {
        "status": bool(db.get_group_key(chat_id, "welcome_enabled")),
        "text": db.get_group_key(chat_id, "welcome_message") or ""
    }


def set_group_welcome(chat_id, text, status):
    """تنظیمات خوش‌آمد را ذخیره کن"""
    db.set_group_key(chat_id, "welcome_message", text or "")
    db.set_group_key(chat_id, "welcome_enabled", bool(status))


# ================================================================
# REGISTER HANDLERS
# ================================================================

def register_group_handlers(client, owner_id):
    """تمام handler‌های گروه را ثبت کن"""

    # ======================== سکوت گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".سکوت گپ", ".mute group"])
    async def mute_handler(event):
        """کاربر را سکوت کن"""
        if not owner_only(event, owner_id):
            return
        
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "❌ باید روی کاربر ریپلای کنی یا آیدی وارد کنی")

        delta, val, unit, reason = parse_time_and_reason(event.ml_args or "")
        ok = await mute_user(client, event.chat_id, user.id, delta)
        
        if not ok:
            return await edit_auto(event, "❌ خطا در سکوت کردن کاربر")

        mention = f"[{safe_name(user)}](tg://user?id={user.id})"
        
        if val:
            msg = f"✅ کاربر {mention} برای **{val} {unit}** سکوت شد"
            if reason:
                msg += f"\n📝 دلیل: {reason}"
        else:
            msg = f"✅ کاربر {mention} سکوت شد"
        
        await edit_auto(event, msg)

    # ======================== حذف سکوت گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".حذف سکوت گپ", ".unmute group"])
    async def unmute_handler(event):
        """سکوت کاربر را برطرف کن"""
        if not owner_only(event, owner_id):
            return
        
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "❌ باید روی کاربر ریپلای کنی یا آیدی وارد کنی")

        ok = await unmute_user(client, event.chat_id, user.id)
        
        if ok:
            mention = f"[{safe_name(user)}](tg://user?id={user.id})"
            await edit_auto(event, f"✅ کاربر {mention} از سکوت خارج شد")
        else:
            await edit_auto(event, "❌ خطا در حذف سکوت")

    # ======================== لیست سکوت گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".لیست سکوت گپ"])
    async def muted_list_handler(event):

        if not owner_only(event, owner_id):
            return

        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        text = "**🔇 لیست کاربران سکوت شده:**\n\n"
        found = False

        async for user in client.iter_participants(
        event.chat_id,
        filter=ChannelParticipantsRestricted
    ):
            perms = await client.get_permissions(event.chat_id, user.id)

            if perms and perms.send_messages is False:
                found = True

                username = f"`@{user.username}`" if user.username else "`ندارد`"
                name = safe_name(user)

                text += f"👤 {name} | {username}\n"

        if not found:
            text = "**🔇 هیچ کاربری سکوت نشده است**"

        await edit_auto(event, text)

    # ======================== بن گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".بن گپ", ".ban group"])
    async def ban_handler(event):
        """کاربر را بن کن"""
        if not owner_only(event, owner_id):
            return
        
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "❌ باید روی کاربر ریپلای کنی یا آیدی وارد کنی")

        delta, val, unit, reason = parse_time_and_reason(event.ml_args or "")
        ok = await ban_user(client, event.chat_id, user.id, delta)
        
        if not ok:
            return await edit_auto(event, "❌ خطا در بن کردن کاربر")

        mention = f"[{safe_name(user)}](tg://user?id={user.id})"
        
        if val:
            msg = f"✅ کاربر {mention} برای **{val} {unit}** بن شد"
            if reason:
                msg += f"\n📝 دلیل: {reason}"
        else:
            msg = f"✅ کاربر {mention} بن شد"
        
        await edit_auto(event, msg)

    # ======================== حذف بن گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".حذف بن گپ", ".unban group"])
    async def unban_handler(event):
        """بن کاربر را برطرف کن"""
        if not owner_only(event, owner_id):
            return
        
        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        user = await resolve_target(event)
        if not user:
            return await edit_auto(event, "❌ باید روی کاربر ریپلای کنی یا آیدی وارد کنی")

        ok = await unban_user(client, event.chat_id, user.id)
        
        if ok:
            mention = f"[{safe_name(user)}](tg://user?id={user.id})"
            await edit_auto(event, f"✅ کاربر {mention} از بن خارج شد")
        else:
            await edit_auto(event, "❌ خطا در حذف بن")

    # ======================== لیست بن گپ ========================
    @client.on(events.NewMessage)
    @multi_lang([".لیست بن"])
    async def banned_list_handler(event):

        if not owner_only(event, owner_id):
            return

        if not await is_group_admin(client, event.chat_id, event.sender_id):
            return await edit_auto(event, "❌ شما ادمین این گروه نیستید")

        text = "**📛 لیست کاربران بن شده:**\n\n"
        found = False
    
        async for user in client.iter_participants(
        event.chat_id,
        filter=ChannelParticipantsKicked
    ):
            found = True

            username = f"`@{user.username}`" if user.username else "`ندارد`"
            name = safe_name(user)

        text += f"👤 {name} | {username}\n"

        if not found:
            text = "**📛 هیچ کاربری بن نشده است**"

        await edit_auto(event, text)

    # ======================== خوش‌آمد روشن ========================
    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی روشن", ".welcome on"])
    async def welcome_on(event):
        """خوش‌آمدگویی را فعال کن"""
        if not owner_only(event, owner_id):
            return
        
        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], True)
        await edit_auto(event, "✅ سیستم خوش‌آمدگویی فعال شد")

    # ======================== خوش‌آمد خاموش ========================
    @client.on(events.NewMessage)
    @multi_lang([".خوشامدگویی خاموش", ".welcome off"])
    async def welcome_off(event):
        """خوش‌آمدگویی را غیرفعال کن"""
        if not owner_only(event, owner_id):
            return
        
        settings = get_group_welcome(event.chat_id)
        set_group_welcome(event.chat_id, settings["text"], False)
        await edit_auto(event, "❌ سیستم خوش‌آمدگویی غیرفعال شد")

    # ======================== تنظیم خوش‌آمد ========================
    @client.on(events.NewMessage)
    @multi_lang([".تنظیم خوشامدگویی", ".set welcome"])
    async def set_welcome(event):
        """متن خوش‌آمدگویی را تنظیم کن"""
        if not owner_only(event, owner_id):
            return
        
        text = event.ml_args or ""
        if not text:
            return await edit_auto(event, "❌ متن را بعد از دستور وارد کن")
        
        set_group_welcome(event.chat_id, text, True)
        await edit_auto(event, "✅ متن خوش‌آمدگویی ذخیره شد")

    # ======================== وضعیت خوش‌آمد ========================
    @client.on(events.NewMessage)
    @multi_lang([".وضعیت خوشامدگویی", ".welcome status"])
    async def welcome_status(event):
        """وضعیت خوش‌آمدگویی را نمایش بده"""
        if not owner_only(event, owner_id):
            return
        
        settings = get_group_welcome(event.chat_id)
        status = "✅ فعال" if settings["status"] else "❌ غیرفعال"
        text_content = settings["text"] or "متنی تنظیم نشده"
        
        await edit_auto(event, 
            f"📋 **وضعیت خوش‌آمدگویی**\n\n"
            f"وضعیت: {status}\n\n"
            f"📝 متن:\n{text_content}"
        )

    print("✅ سیستم مدیریت گروه لود شد")


__all__ = ["register_group_handlers"]
