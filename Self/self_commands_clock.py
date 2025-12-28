# =======================
# self_commands_clock.py
# ساعت زنده دقیق + هماهنگ با دیتابیس جدید
# =======================

import asyncio
from datetime import datetime
import pytz
from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
from self_config import self_config, city_timezones
from self_storage import Storage
import json

# ==========================================
# دیتابیس و فایل ذخیره‌سازی
# ==========================================
db = Storage()
DATA_FILE = "self_storage_data.json"

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# هر کاربر یک تسک مخصوص ساعت زنده دارد
# ==========================================
active_clock_tasks = {}

# ==========================================
# گرفتن پروفایل ساعت کاربر (ساخت در صورت نبود)
# ==========================================
def get_clock(user_id):
    data = db.data.setdefault("users", {}).setdefault(str(user_id), {})
    clock = data.setdefault("clock", {})
    clock.setdefault("enabled", False)
    clock.setdefault("timezone", "Asia/Tehran")
    clock.setdefault("bio_enabled", False)
    clock.setdefault("name_enabled", False)
    clock.setdefault("font_id", None)
    clock.setdefault("prev_state", {})  # وضعیت قبل از خاموش
    clock.setdefault("original_profile", {})  # ذخیره بیو و نام اصلی
    clock.setdefault("original_saved", False)
    return clock

def set_clock(user_id, key, value):
    get_clock(user_id)[key] = value
    save_data(db.data)

# ==========================================
# ذخیره بیو و اسم اصلی
# ==========================================
from telethon.tl.functions.users import GetFullUserRequest

async def save_original_profile(client, user_id):
    clock = get_clock(user_id)
    if clock.get("original_saved"):
        return

    me = await client.get_me()
    try:
        full = await client(GetFullUserRequest(me.id))
        about = full.about if hasattr(full, "about") else ""
    except:
        about = ""

    clock["original_profile"] = {
        "about": about,
        "first_name": me.first_name or "",
        "last_name": me.last_name or ""
    }
    clock["original_saved"] = True
    save_data(db.data)

# ==========================================
# ساعت زنده
# ==========================================
async def live_clock_user(client, user_id):
    last_minute = -1
    try:
        while True:
            clock = get_clock(user_id)

            # لوپ فقط وقتی فعال است که bio یا name فعال باشد
            if not (clock.get("bio_enabled") or clock.get("name_enabled")):
                break

            tz_name = clock.get("timezone", "Asia/Tehran")
            now = datetime.now(pytz.timezone(tz_name))

            if now.minute != last_minute:
                last_minute = now.minute

                # آپدیت بیو
                if clock.get("bio_enabled"):
                    await client(UpdateProfileRequest(about=now.strftime("%H:%M")))

                # آپدیت نام
                if clock.get("name_enabled"):
                    me = await client.get_me()
                    await client(UpdateProfileRequest(
                        first_name=me.first_name,
                        last_name=now.strftime("%H:%M")
                    ))

                # فونت
                font_id = clock.get("font_id")
                if font_id and font_id in FONT_TABLE:
                    digits = FONT_TABLE[font_id]
                    h_str = "".join(digits[int(d)] for d in f"{now.hour:02}")
                    m_str = "".join(digits[int(d)] for d in f"{now.minute:02}")
                    print(f"[CLOCK FONT {font_id}] {h_str}:{m_str}")

            await asyncio.sleep(60 - now.second)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Clock ERR] {e}")
    finally:
        if user_id in active_clock_tasks:
            del active_clock_tasks[user_id]

# ==========================================
# فونت‌ها
# ==========================================
FONT_TABLE = {
    1: ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"],
    2: ["𝟬","𝟭","𝟮","𝟯","𝟰","𝟱","𝟲","𝟳","𝟴","𝟵"],
    3: ["⓿","①","②","③","④","⑤","⑥","⑦","⑧","⑨"],
    4: ["🄀","🄁","🄂","🄃","🄄","🄅","🄆","🄇","🄈","🄉"]
}

# ==========================================
# ثبت دستورهای مدیریت ساعت
# ==========================================
def register_clock(client):

    async def start_active_clocks():
        for user_id_str, udata in db.data.get("users", {}).items():
            clock = udata.get("clock", {})
            if clock.get("bio_enabled") or clock.get("name_enabled"):
                uid = int(user_id_str)
                if uid not in active_clock_tasks:
                    active_clock_tasks[uid] = asyncio.create_task(
                        live_clock_user(client, uid)
                    )

    asyncio.create_task(start_active_clocks())

    @client.on(events.NewMessage(pattern=r"\.ساعت(.*)"))
    async def handle_clock(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        arg = event.pattern_match.group(1).strip()
        clock = get_clock(user_id)

        # بدون پارامتر
        if arg == "":
            tz = clock.get("timezone", "Asia/Tehran")
            now = datetime.now(pytz.timezone(tz))
            return await event.edit(f"🕒 ساعت {tz}: {now.strftime('%H:%M')}")

        # ساعت شهر
        if arg in city_timezones:
            tz = city_timezones[arg]
            now = datetime.now(pytz.timezone(tz))
            return await event.edit(f"🕒 ساعت {arg}: {now.strftime('%H:%M')}")

        # ساعت کلی
        if arg == "کلی":
            text = ""
            for city, tz in city_timezones.items():
                try:
                    now = datetime.now(pytz.timezone(tz))
                    text += f"🕒 {city}: {now.strftime('%H:%M')}\n"
                except:
                    text += f"❌ {city}: خطا\n"
            return await event.edit(text)

        # ساعت جهانی
        if arg == "جهانی":
            now = datetime.utcnow()
            return await event.edit(f"🌐 UTC: {now.strftime('%H:%M')}")

        # فعال‌سازی بیو
        if arg == "بیو":
            await save_original_profile(client, user_id)
            set_clock(user_id, "bio_enabled", True)
            if user_id not in active_clock_tasks:
                active_clock_tasks[user_id] = asyncio.create_task(
                    live_clock_user(client, user_id)
                )
            return await event.edit("✅ ساعت روی بیو فعال شد.")

        # فعال‌سازی نام
        if arg == "اسم":
            await save_original_profile(client, user_id)
            set_clock(user_id, "name_enabled", True)
            if user_id not in active_clock_tasks:
                active_clock_tasks[user_id] = asyncio.create_task(
                    live_clock_user(client, user_id)
                )
            return await event.edit("✅ ساعت روی اسم فعال شد.")

        # فونت
        if arg.startswith("فنت"):
            parts = arg.split()
            if len(parts) < 2:
                return await event.edit("❌ فرمت درست: `.ساعت فنت <شماره>`")
            fid = int(parts[1])
            if fid not in FONT_TABLE:
                return await event.edit("❌ این فونت وجود ندارد.")
            set_clock(user_id, "font_id", fid)
            if user_id not in active_clock_tasks and (clock.get("bio_enabled") or clock.get("name_enabled")):
                active_clock_tasks[user_id] = asyncio.create_task(
                    live_clock_user(client, user_id)
                )
            return await event.edit(f"✅ فونت {fid} فعال شد.")

        # نمایش فونت‌ها
        if arg == "نمایش":
            msg = "📜 لیست فونت‌ها:\n"
            for fid, digits in FONT_TABLE.items():
                msg += f"{fid}: {''.join(digits)}\n"
            return await event.edit(msg)

        # خاموش کردن ساعت
        if arg == "خاموش":
            if user_id in active_clock_tasks:
                active_clock_tasks[user_id].cancel()
                del active_clock_tasks[user_id]

            original = clock.get("original_profile", {})
            await client(UpdateProfileRequest(about=original.get("about","")))
            await client(UpdateProfileRequest(first_name=original.get("first_name",""),
                                              last_name=original.get("last_name","")))

            clock["bio_enabled"] = False
            clock["name_enabled"] = False
            clock["font_id"] = None
            clock["original_saved"] = False
            clock["original_profile"] = {}
            clock["prev_state"] = {}
            save_data(db.data)
            return await event.edit("🛑 ساعت خاموش شد و پروفایل به حالت قبل برگشت.")

        # روشن کردن ساعت (وضعیت قبل)
        if arg == "روشن":
            prev = clock.get("prev_state", {})
            set_clock(user_id, "bio_enabled", prev.get("bio_enabled", False))
            set_clock(user_id, "name_enabled", prev.get("name_enabled", False))
            set_clock(user_id, "font_id", prev.get("font_id"))
            set_clock(user_id, "timezone", prev.get("timezone", "Asia/Tehran"))

            if user_id not in active_clock_tasks and (clock.get("bio_enabled") or clock.get("name_enabled")):
                active_clock_tasks[user_id] = asyncio.create_task(
                    live_clock_user(client, user_id)
                )
            return await event.edit("✅ ساعت دوباره فعال شد و وضعیت قبلی بازیابی شد.")

        # تنظیم منطقه
        if arg.startswith("منطقه"):
            parts = arg.split()
            if len(parts) < 2:
                return await event.edit("❌ استفاده صحیح: `.ساعت منطقه <شهر>`")
            city = parts[1]
            if city not in city_timezones:
                return await event.edit("❌ چنین شهری ثبت نشده.")
            set_clock(user_id, "timezone", city_timezones[city])
            return await event.edit(f"🌍 منطقه روی {city} تنظیم شد.")

        return await event.edit("❌ دستور اشتباه است.")