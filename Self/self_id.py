# ============================================================
# profile_manager.py
# Telethon Self Profile Manager Module
# Author: Tiam
# اصلاح شده برای دانلود موقت عکس بدون ذخیره دائمی
# ============================================================

import asyncio
import os
import tempfile
from telethon import events, functions
from telethon.tl.types import UserProfilePhoto
from telethon.errors import (
    UsernameOccupiedError,
    UsernameInvalidError,
    AboutTooLongError,
    FloodWaitError
)

# ============================================================
# Helper functions
# ============================================================

def is_self(event):
    """بررسی می‌کند که پیام از صاحب اکانت باشد"""
    return event.sender_id == event.client._self_id


async def get_target_user(event):
    """دریافت کاربر هدف، اگر ریپلای باشد کاربر ریپلای، در غیر این صورت صاحب اکانت"""
    if event.is_reply:
        reply = await event.get_reply_message()
        return await event.client.get_entity(reply.sender_id)
    else:
        return await event.client.get_me()


# ============================================================
# Main register function
# ============================================================

def register(client):
    """ثبت تمامی دستورات ربات"""

    # ==============================
    # .ایدی
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.ایدی$'))
    async def user_info_handler(event):
        if not is_self(event):
            return

        user = await get_target_user(event)
        name = user.first_name or "ندارد"
        last_name = user.last_name or "ندارد"
        username = f"@{user.username}" if user.username else "ندارد"
        user_id = user.id

        # اگر عکس داشته باشه
        if user.photo:
            with tempfile.TemporaryDirectory() as tmpdir:
                photo_path = os.path.join(tmpdir, "pfp.jpg")
                await event.client.download_profile_photo(user, file=photo_path)
                text = (
                    f"اسم: {name}\n"
                    f"فامیل: {last_name}\n"
                    f"یوزرنیم: {username}\n"
                    f"ایدی عددی: {user_id}"
                )
                # ارسال پیام داخل بلوک تا فایل پاک نشه قبل از ارسال
                await event.edit(text, file=photo_path)
            return

        # اگر عکس نداشت فقط متن
        text = (
            f"اسم: {name}\n"
            f"فامیل: {last_name}\n"
            f"یوزرنیم: {username}\n"
            f"ایدی عددی: {user_id}"
        )
        await event.edit(text)

    # ==============================
    # .تنظیم اسم
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.تنظیم اسم (.+)'))
    async def set_first_name(event):
        if not is_self(event):
            return

        new_name = event.pattern_match.group(1).strip()
        me = await client.get_me()
        old_name = me.first_name or "ندارد"

        try:
            await client(functions.account.UpdateProfileRequest(first_name=new_name))
            await event.edit(
                f"⚠️ اسم عوض شد\n"
                f"اسم قبلی: {old_name}\n"
                f"اسم فعلی: {new_name}"
            )
        except Exception:
            await event.edit("⚠️ خطا در تغییر اسم")

    # ==============================
    # .تنظیم فامیل
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.تنظیم فامیل (.+)'))
    async def set_last_name(event):
        if not is_self(event):
            return

        new_last = event.pattern_match.group(1).strip()
        me = await client.get_me()
        old_last = me.last_name or "ندارد"

        try:
            await client(functions.account.UpdateProfileRequest(last_name=new_last))
            await event.edit(
                f"⚠️ فامیل عوض شد\n"
                f"فامیل قبلی: {old_last}\n"
                f"فامیل فعلی: {new_last}"
            )
        except Exception:
            await event.edit("⚠️ خطا در تغییر فامیل")

    # ==============================
    # .تنظیم بیو
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.تنظیم بیو (.+)'))
    async def set_bio(event):
        if not is_self(event):
            return

        new_bio = event.pattern_match.group(1).strip()
        me = await client.get_me()
        old_bio = me.about or "ندارد"

        try:
            await client(functions.account.UpdateProfileRequest(about=new_bio))
            await event.edit(
                f"⚠️ بیو عوض شد\n"
                f"بیو قبلی: {old_bio}\n"
                f"بیو فعلی: {new_bio}"
            )
        except AboutTooLongError:
            await event.edit("⚠️ بیو بیش از حد مجاز است")
        except Exception:
            await event.edit("⚠️ خطا در تغییر بیو")

    # ==============================
    # .تنظیم یوزرنیم
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.تنظیم یوزرنیم (.+)'))
    async def set_username(event):
        if not is_self(event):
            return

        new_username = event.pattern_match.group(1).strip().replace("@", "")
        me = await client.get_me()
        old_username = f"@{me.username}" if me.username else "ندارد"

        try:
            await client(functions.account.UpdateUsernameRequest(username=new_username))
            await event.edit(
                f"⚠️ یوزرنیم عوض شد\n"
                f"یوزرنیم قبلی: {old_username}\n"
                f"یوزرنیم فعلی: @{new_username}"
            )
        except UsernameOccupiedError:
            await event.edit("⚠️ یوزرنیم قبلا گرفته شده")
        except UsernameInvalidError:
            await event.edit("⚠️ یوزرنیم نامعتبر است")
        except Exception:
            await event.edit("⚠️ خطا در تغییر یوزرنیم")

    # ==============================
    # .تنظیم عکس (ریپلای)
    # ==============================
    @client.on(events.NewMessage(pattern=r'^\.تنظیم عکس$'))
    async def set_profile_photo(event):
        if not is_self(event):
            return

        if not event.is_reply:
            await event.edit("⚠️ باید روی عکس ریپلای شود")
            return

        reply = await event.get_reply_message()
        if not reply.photo:
            await event.edit("⚠️ پیام ریپلای‌شده عکس نیست")
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                photo_file = await reply.download_media(file=os.path.join(tmpdir, "tmp_photo.jpg"))
                # آپلود عکس
                await client(functions.photos.UploadProfilePhotoRequest(
                    file=await client.upload_file(photo_file)
                ))
                # ارسال پیام داخل بلوک تا فایل هنوز موجود باشه
                await event.edit(
                    "⚠️ عکس پروفایل عوض شد\n"
                    "عکس قبلی و عکس جدید ثبت شد"
                )
        except FloodWaitError:
            await event.edit("⚠️ محدودیت زمانی تلگرام")
        except Exception:
            await event.edit("⚠️ خطا در تغییر عکس پروفایل")

# ============================================================
# End of file
# ============================================================