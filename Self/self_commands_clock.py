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
from pymongo import MongoClient
from multi_lang import multi_lang, reply_auto, edit_auto


mongo = MongoClient(
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

db = mongo["selfbot_default"]
clock_col = db["clock_users"]
# ==========================================
# دیتابیس و فایل ذخیره‌سازی
# ==========================================
import pytz

# ساخت دیکشنری پویا از همه timezoneها
city_index = {}

for tz in pytz.all_timezones:
    if "/" in tz:
        city_part = tz.split("/")[-1].replace("_", " ")
        city_index[city_part.lower()] = tz

async def start_active_clocks(client):
    users = clock_col.find({
        "$or": [
            {"clock.bio_enabled": True},
            {"clock.name_enabled": True}
        ]
    })
    for user in users:  # بدون async
        uid = user["_id"]
        if uid not in active_clock_tasks:
            active_clock_tasks[uid] = asyncio.create_task(live_clock_user(client, uid))
# ==========================================
# هر کاربر یک تسک مخصوص ساعت زنده دارد
# ==========================================
active_clock_tasks = {}

# ==========================================
# گرفتن پروفایل ساعت کاربر (ساخت در صورت نبود)
# ==========================================
def get_clock(user_id):

    doc = clock_col.find_one({"_id": user_id})

    if not doc:
        doc = {
            "_id": user_id,
            "clock": {
                "timezone": "Asia/Tehran",
                "bio_enabled": False,
                "name_enabled": False,
                "font_id": None,
                "prev_state": {},
                "original_profile": {},
                "original_saved": False
            }
        }
        clock_col.insert_one(doc)

    return doc["clock"]

def save_clock(user_id, clock):

    clock_col.update_one(
        {"_id": user_id},
        {"$set": {"clock": clock}},
        upsert=True
    )

def set_clock(user_id, key, value):

    clock = get_clock(user_id)
    clock[key] = value
    save_clock(user_id, clock)

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
    save_clock(user_id, clock)

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
    4: ["🄀","🄁","🄂","🄃","🄄","🄅","🄆","🄇","🄈","🄉"],

    # بولد ریاضی
    5: ["𝟎","𝟏","𝟐","𝟑","𝟒","𝟓","𝟔","𝟕","𝟖","𝟗"],

    # دابل استراک
    6: ["𝟘","𝟙","𝟚","𝟛","𝟜","𝟝","𝟞","𝟟","𝟠","𝟡"],

    # سوپراسکریپت
    7: ["⁰","¹","²","³","⁴","⁵","⁶","⁷","⁸","⁹"],

    # ساب‌اسکریپت
    8: ["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"],

    # دایره مشکی
    9: ["⓪","❶","❷","❸","❹","❺","❻","❼","❽","❾"],

    # مربع
    10: ["🟦0","🟦1","🟦2","🟦3","🟦4","🟦5","🟦6","🟦7","🟦8","🟦9"],

    # استایل خاص
    11: ["𝟶","𝟷","𝟸","𝟹","𝟺","𝟻","𝟼","𝟽","𝟾","𝟿"],

    # استایل کلاسیک
    12: ["０","１","２","３","４","５","６","７","８","９"],

    # استایل باریک
    13: ["𝟢","𝟣","𝟤","𝟥","𝟦","𝟧","𝟨","𝟩","𝟪","𝟫"],

    # استایل تزئینی
    14: ["➀","➁","➂","➃","➄","➅","➆","➇","➈","➉"],

    # استایل فانتزی گرد
    15: ["🄌","➊","➋","➌","➍","➎","➏","➐","➑","➒"]
}
# ================================
# نگاشت پارامترها فارسی -> داخلی
# ================================
fa_alias = {
    "تهران": "tehran",
    "لندن": "london",
    "پاریس": "paris",
    "برلین": "berlin",
    "رم": "rome",
    "مادرید": "madrid",
    "آمستردام": "amsterdam",
    "بروکسل": "brussels",
    "وین": "vienna",
    "پراگ": "prague",
    "ورشو": "warsaw",
    "کی‌یف": "kyiv",
    "مسکو": "moscow",
    "استانبول": "istanbul",
    "آنکارا": "ankara",
    "دبی": "dubai",
    "ابوظبی": "abu dhabi",
    "دوحه": "doha",
    "ریاض": "riyadh",
    "بغداد": "baghdad",
    "کویت": "kuwait",
    "باکو": "baku",
    "تاشکند": "tashkent",
    "دهلی": "kolkata",
    "بمبئی": "kolkata",
    "پکن": "shanghai",
    "شانگهای": "shanghai",
    "توکیو": "tokyo",
    "سئول": "seoul",
    "بانکوک": "bangkok",
    "سنگاپور": "singapore",
    "کوالالامپور": "kuala lumpur",
    "جاکارتا": "jakarta",
    "سیدنی": "sydney",
    "ملبورن": "melbourne",
    "ونکوور": "vancouver",
    "تورنتو": "toronto",
    "نیویورک": "new york",
    "واشنگتن": "new york",
    "شیکاگو": "chicago",
    "لس‌آنجلس": "los angeles",
    "لس آنجلس": "los angeles",
    "سان‌فرانسیسکو": "los angeles",
    "مکزیکوسیتی": "mexico city",
    "بوینس‌آیرس": "buenos aires",
    "سائوپائولو": "sao paulo",
    "قاهره": "cairo",
    "ژوهانسبورگ": "johannesburg",
    "نایروبی": "nairobi",
}

def resolve_city(user_input):
    q = user_input.strip().lower()

    # اگر فارسی بود تبدیل به انگلیسی کن
    if q in fa_alias:
        q = fa_alias[q]

    return city_index.get(q)

# ==========================================
# ثبت دستورهای مدیریت ساعت
# ==========================================
def register_clock(client):

    asyncio.create_task(start_active_clocks(client))

    # =========================
    # نمایش ساعت فعلی
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت", ".clock"])
    async def clock_show(event):
        sender = await event.get_sender()
        me = await client.get_me()

        if sender.id != me.id:
            return

        query = getattr(event, "ml_args", "").strip()
        is_fa = event.raw_text.startswith(".ساعت")

        if not query:
            tz = "Asia/Tehran"
        else:
            tz = resolve_city(query)
            if not tz:
                return await edit_auto(
                    event,
                    "**❌ شهر پیدا نشد.**" if is_fa else "**❌ City not found.**"
                )

        now = datetime.now(pytz.timezone(tz))
        city_name = tz.split("/")[-1].replace("_", " ")

        if is_fa:
            await edit_auto(event, f"**🕒 ساعت {city_name}: {now.strftime('%H:%M')}**")
        else:
            await edit_auto(event, f"**🕒 Time in {city_name}: {now.strftime('%H:%M')}**")

# =========================
# ثبت دستورات ساعت جهانی و کلی
# =========================

    # =========================
    # 🌐 ساعت جهانی (UTC)
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت جهانی", ".clock utc"])
    async def clock_utc(event):
        sender = await event.get_sender()
        me = await client.get_me()

        # فقط خود اکانت
        if sender.id != me.id:
            return

        now = datetime.utcnow()
        await edit_auto(event, f"**🌐 UTC: {now.strftime('%H:%M')}**")

    # =========================
    # 🕒 ساعت کلی (همه شهرها)
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت کلی", ".clock all"])
    async def clock_all(event):
        sender = await event.get_sender()
        me = await client.get_me()

        # فقط خود اکانت
        if sender.id != me.id:
            return

        text = "**🕒 لیست ساعت شهرها:\n\n**"

        for city, tz in city_timezones.items():
            try:
                now = datetime.now(pytz.timezone(tz))
                text += f"**{city}: {now.strftime('%H:%M')}\n**"
            except Exception:
                text += f"**{city}: خطا ❌\n**"

        await edit_auto(event, text)

    # =========================
    # فعال‌سازی بیو
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت بیو", ".clock bio"])
    async def clock_bio(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        await save_original_profile(client, user_id)
        set_clock(user_id, "bio_enabled", True)

        if user_id not in active_clock_tasks:
            active_clock_tasks[user_id] = asyncio.create_task(
                live_clock_user(client, user_id)
            )

        await edit_auto(event, "**✅ ساعت روی بیو فعال شد.**")

    # =========================
    # فعال‌سازی نام
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت اسم", ".clock name"])
    async def clock_name(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        await save_original_profile(client, user_id)
        set_clock(user_id, "name_enabled", True)

        if user_id not in active_clock_tasks:
            active_clock_tasks[user_id] = asyncio.create_task(
                live_clock_user(client, user_id)
            )

        await edit_auto(event, "**✅ ساعت روی اسم فعال شد.**")

    # =========================
    # تنظیم فونت
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت فونت", ".clock font"])
    async def clock_font(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        query = getattr(event, "ml_args", "").strip()
        parts = query.split()

        if not parts:
            return await edit_auto(event, "**❌ فرمت درست: `.ساعت فونت <شماره>`**")

        try:
            fid = int(parts[0])
        except ValueError:
            return await edit_auto(event, "**❌ شماره فونت باید عدد باشد.**")

        if fid not in FONT_TABLE:
            return await edit_auto(event, "**❌ این فونت وجود ندارد.**")

        set_clock(user_id, "font_id", fid)

        await edit_auto(event, f"**✅ فونت {fid} فعال شد.**")

    # =========================
    # نمایش فونت‌ها
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".لیست فونت", ".font list"])
    async def clock_show_fonts(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        msg = "**📜 لیست فونت‌ها:\n**"
        for fid, digits in FONT_TABLE.items():
            msg += f"{fid}: {''.join(digits)}\n"

        await edit_auto(event, msg)

    # =========================
    # خاموش کردن ساعت
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت خاموش", ".clock off"])
    async def clock_off(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        clock = get_clock(user_id)

        if user_id in active_clock_tasks:
            active_clock_tasks[user_id].cancel()
            del active_clock_tasks[user_id]

        original = clock.get("original_profile", {})

        await client(UpdateProfileRequest(
            about=original.get("about", "")
        ))

        await client(UpdateProfileRequest(
            first_name=original.get("first_name", ""),
            last_name=original.get("last_name", "")
        ))

        clock["bio_enabled"] = False
        clock["name_enabled"] = False
        clock["font_id"] = None
        clock["original_saved"] = False
        clock["original_profile"] = {}
        save_clock(user_id, clock)

        await edit_auto(event, "**🛑 ساعت خاموش شد و پروفایل بازیابی شد.**")

    # =========================
    # تنظیم منطقه
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".ساعت منطقه", ".clock region"])
    async def clock_region(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return

        user_id = sender.id
        query = getattr(event, "ml_args", "").strip()

        if not query:
            return await edit_auto(event, "**❌ استفاده صحیح: `.ساعت منطقه <شهر>`**")

        if query not in city_timezones:
            return await edit_auto(event, "**❌ چنین شهری ثبت نشده.*؟")

        set_clock(user_id, "timezone", city_timezones[query])

        await edit_auto(event, f"**🌍 منطقه روی {query} تنظیم شد.**")
