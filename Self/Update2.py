# =========================================================
# ◢◤ ⟦ ◈ SELF NIX SYSTEM ◈ ⟧ ◢◤
# Tiam Official Self System
# Version: 1.1.2
# =========================================================

import asyncio
import random
from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
from functools import wraps
from multi_lang import multi_lang, reply_auto, edit_auto

# =========================================================
# CONFIG
# =========================================================

SELF_NIX_ENABLED = True

MANDATORY_TAG = True

DEFAULT_PROFILE_STYLE = 1

AUTO_SIGNATURE_LINES = 6
AUTO_SIGNATURE_LENGTH = 50

# =========================================================
# PROFILE STYLES
# =========================================================

PROFILE_STYLES = {

    1: {
        "name": "◈NIX◈ | {name}",
        "bio": "◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤"
    },

    2: {
        "name": "◢ ₮ ł ₳ ₼ | NIX ◤ {name}",
        "bio": "⟦ ◈ ⟧ 𝑆𝑒𝑙𝑓 𝑁𝑖𝑥 𝑃𝑜𝑤𝑒𝑟𝑒𝑑"
    },

    3: {
        "name": "тɪαм | ◈ {name}",
        "bio": "◢ ᴛɪᴀᴍ'ꜱ ᴏꜰꜰɪᴄɪᴀʟ ꜱᴇʟꜰ ◤"
    },

    4: {
        "name": "[ ₮ ł ₳ ₼ ] | {name}",
        "bio": "◢◤ Nix Group ◢◤"
    },

    5: {
        "name": "⟦ ◈ SELF_NIX ◈ ⟧ {name}",
        "bio": "▰▰▰▰▰▱▱▱ 70%"
    }

}

# =========================================================
# RUNTIME
# =========================================================

user_styles = {}

# =========================================================
# UTILS
# =========================================================

def generate_bar(percent):

    full = int(percent / 10)

    empty = 10 - full

    return "▰" * full + "▱" * empty

def get_style(chat_id):

    return user_styles.get(
        chat_id,
        DEFAULT_PROFILE_STYLE
    )

def set_style(chat_id, style):

    user_styles[chat_id] = style

def build_signature():

    percent = random.randint(70, 99)

    bar = generate_bar(percent)

    return f"""

______

⟦ ◈ ⟧ 𝑆𝑒𝑙𝑓 𝑁𝑖𝑥 𝑃𝑜𝑤𝑒𝑟𝑒𝑑

{bar} {percent}%

◢ ᴛɪᴀᴍ'ꜱ ᴏꜰꜰɪᴄɪᴀʟ ꜱᴇʟꜰ ◤
"""

def should_add_signature(text):

    if not text:
        return False

    lines = text.count("\n") + 1

    length = len(text)

    if lines >= AUTO_SIGNATURE_LINES:
        return True

    if length >= AUTO_SIGNATURE_LENGTH:
        return True

    return False

async def auto_edit(event, text, edit_auto):

    if should_add_signature(text):

        text += build_signature()

    return await edit_auto(event, text)

async def auto_reply(event, text, reply_auto):

    if should_add_signature(text):

        text += build_signature()

    return await reply_auto(event, text)

# =========================================================
# PROFILE APPLY
# =========================================================

async def apply_profile(client, style_id):

    me = await client.get_me()

    current_name = me.first_name or "User"

    style = PROFILE_STYLES.get(style_id)

    if not style:
        return False

    new_name = style["name"].format(
        name=current_name
    )

    new_bio = style["bio"]

    # جلوگیری از حذف اسم اصلی سلف
    if MANDATORY_TAG:

        if "NIX" not in new_name.upper():

            new_name = f"◈NIX◈ | {current_name}"

    try:

        await client(UpdateProfileRequest(
            first_name=new_name,
            about=new_bio
        ))

        return True

    except Exception as e:

        print("PROFILE ERROR:", e)

        return False

# =========================================================
# STATUS BUILDER
# =========================================================

def build_status():

    speed = round(
        random.uniform(0.08, 0.20),
        2
    )

    percent = random.randint(75, 99)

    bar = generate_bar(percent)

    return f"""
◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤

◈ Message: Pong!
◈ Speed: {speed}s
◈ Status: Online ✨

{bar} {percent}%

◢◤ Nix Group ◢◤
""".strip()

# =========================================================
# STYLE LIST
# =========================================================

def build_style_text():

    return """
◢◤ ⟦ ◈ SELF NIX STYLE ◈ ⟧ ◢◤

◈ استایل های موجود:

1 → ◈NIX◈ | Name
2 → ◢ ₮ ł ₳ ₼ | NIX ◤
3 → тɪαм | ◈
4 → [ ₮ ł ₳ ₼ ]
5 → ⟦ ◈ SELF_NIX ◈ ⟧

نماد ها:
◢ SELF NIX ◤
⟦ ◈ SELF_NIX ◈ ⟧
◢ ₮ ł ₳ ₼ | NIX ◤

شکل ها:
тɪαм
T I A M
[ ₮ ł ₳ ₼ ]
◢ ◤
⟦ ◈ ⟧
▰▰▰▱▱

◈ مثال:
.profile 2
""".strip()

# =========================================================
# MAIN REGISTER
# =========================================================

def register_self_nix_system(
    client,
):

    # =====================================================
    # AUTO NAME CHECK
    # =====================================================

    @client.on(events.NewMessage(outgoing=True))
    async def auto_name_protect(event):

        if not SELF_NIX_ENABLED:
            return

        try:

            me = await client.get_me()

            current_name = me.first_name or ""

            if "NIX" not in current_name.upper():

                style_id = get_style(event.chat_id)

                style = PROFILE_STYLES.get(style_id)

                new_name = style["name"].format(
                    name=current_name
                )

                await client(UpdateProfileRequest(
                    first_name=new_name
                ))

        except:
            pass

    # =====================================================
    # STATUS
    # =====================================================

    @multi_lang([".ping", ".پینگ"])
    async def ping_handler(event):

        txt = build_status()

        await edit_auto(
            event,
            txt,
            edit_auto
        )

    # =====================================================
    # PROFILE LIST
    # =====================================================

    @multi_lang([".profile", ".پروفایل"])
    async def profile_handler(event):

        args = event.ml_args.strip()

        # نمایش لیست
        if not args:

            return await auto_edit(
                event,
                build_style_text(),
                edit_auto
            )

        # انتخاب استایل
        try:

            style_id = int(args)

        except:

            return await auto_edit(
                event,
                "❌ شماره استایل نامعتبر است",
                edit_auto
            )

        if style_id not in PROFILE_STYLES:

            return await auto_edit(
                event,
                "❌ استایل پیدا نشد",
                edit_auto
            )

        set_style(
            event.chat_id,
            style_id
        )

        ok = await apply_profile(
            client,
            style_id
        )

        if not ok:

            return await auto_edit(
                event,
                "❌ خطا در اعمال پروفایل",
                edit_auto
            )

        percent = random.randint(80, 99)

        bar = generate_bar(percent)

        txt = f"""
◢◤ ⟦ ◈ PROFILE UPDATED ◈ ⟧ ◢◤

◈ Style: {style_id}
◈ Status: Synced ✨

{bar} {percent}%

◢ ᴛɪᴀᴍ'ꜱ ᴏꜰꜰɪᴄɪᴀʟ ꜱᴇʟꜰ ◤
"""

        await edit_auto(
            event,
            txt.strip(),
            edit_auto
        )

    # =====================================================
    # NAME
    # =====================================================

    @multi_lang([".name", ".اسم"])
    async def name_handler(event):

        args = event.ml_args

        if not args:

            return await auto_edit(
                event,
                "❌ اسم وارد نشده",
                edit_auto
            )

        new_name = args

        if MANDATORY_TAG:

            if "NIX" not in new_name.upper():

                new_name = f"◈NIX◈ | {new_name}"

        try:

            await client(UpdateProfileRequest(
                first_name=new_name
            ))

            txt = f"""
◢◤ ⟦ ◈ NAME UPDATED ◈ ⟧ ◢◤

◈ Name:
{new_name}

◈ Status: Protected ✨
"""

            await edit_auto(
                event,
                txt.strip(),
                edit_auto
            )

        except:

            await edit_auto(
                event,
                "❌ خطا در تغییر اسم",
                edit_auto
            )

    # =====================================================
    # BIO
    # =====================================================

    @multi_lang([".bio", ".بیو"])
    async def bio_handler(event):

        args = event.ml_args

        if not args:

            return await auto_edit(
                event,
                "❌ بیو وارد نشده",
                edit_auto
            )

        bio = args

        if "SELF NIX" not in bio.upper():

            bio += "\n\n◢◤ ⟦ ◈ SELF NIX ◈ ⟧ ◢◤"

        try:

            await client(UpdateProfileRequest(
                about=bio
            ))

            await edit_auto(
                event,
                """
◢◤ ⟦ ◈ BIO UPDATED ◈ ⟧ ◢◤

◈ New Bio Applied ✨
◈ Self Nix Protected
""",
                edit_auto
            )

        except:

            await auto_edit(
                event,
                "❌ خطا در تغییر بیو",
                edit_auto
            )

    # =====================================================
    # SIGN TEST
    # =====================================================

    @multi_lang([".sign", ".امضا"])
    async def sign_handler(event):

        txt = """
این یک تست برای سیستم امضای خودکار Self Nix است

این متن عمداً طولانی نوشته شده
تا امضای حرفه‌ای خودکار فعال شود

◢◤ SELF NIX ACTIVE ◢◤
"""

        await edit_auto(
            event,
            txt.strip(),
            edit_auto
        )

    # =====================================================
    # EXAMPLE
    # =====================================================

    @multi_lang([".example", ".نمونه"])
    async def sample_handler(event):

        args = event.ml_args

        text = event.ml_text

        txt = f"""
◢◤ ⟦ ◈ SELF NIX EXAMPLE ◈ ⟧ ◢◤

◈ متن:
{text}

◈ آرگومان:
{args}

◈ Status: Active ✨
"""

        await edit_auto(
            event,
            txt.strip(),
            reply_auto
        )

    print("◢◤ SELF NIX SYSTEM LOADED ◢◤")
