import asyncio
from telethon import events
from deep_translator import GoogleTranslator
from functools import wraps

BASE_LANG = "fa"

# ===============================
# Supported Languages
# ===============================
SUPPORTED_LANGS = {
    "en": "English",
    "fa": "Persian",
    "tr": "Turkish",
    "ru": "Russian",
    "ar": "Arabic",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese"
}

_translate_cache = {}
user_langs = {}

# ===============================
# Language Utils
# ===============================
def get_lang(chat_id):
    return user_langs.get(chat_id, BASE_LANG)

def set_lang(chat_id, lang):
    lang = lang.lower()

    if lang not in SUPPORTED_LANGS:
        return False

    user_langs[chat_id] = lang
    return True

def get_lang_list_text():
    txt = "🌐 Choose Language:\n\n"
    for code, name in SUPPORTED_LANGS.items():
        txt += f"{code} → {name}\n"
    return txt

# ===============================
# Translation Core
# ===============================
async def translate(text, target):

    if not text:
        return text

    key = f"{text}:{target}"

    if key in _translate_cache:
        return _translate_cache[key]

    try:
        result = await asyncio.to_thread(
            lambda: GoogleTranslator(source="auto", target=target).translate(text)
        )

        _translate_cache[key] = result
        return result

    except:
        return text

# ===============================
# 
# ===============================
# 🛑 قوانین Ignore مرکزی برای جلوگیری از تداخل دستورات مشابه
IGNORE_RULES = {
    # بخش ساعت (فارسی و انگلیسی)
    ".ساعت": [
        ".ساعت خاموش",
        ".ساعت اسم",
        ".ساعت بیو",
        ".ساعت کلی",
        ".ساعت جهانی",
        ".ساعت منطقه",
        ".ساعا فونت",
    ],
    ".clock": [
        ".clock utc",
        ".clock all",
        ".clock bio",
        ".clock name",
        ".clock font",
        ".clock off",
        ".clock region",
    ],

    ".بازی": [ 
        ".بازی روشن",
        ".بازی خاموش",
    ],

    ".سکوت": [ 
        ".سکوت گپ", 
    ],

    ".حذف سکوت": [
        ".حذف سکوت گپ",
    ],

    ".حذف":[
        ".حذف سکوت",
        ".حذف سکوت گپ",
        ".حذف پین", 
        ".حذف بن",
        ".حذف همه",
    ],
}

def _norm_cmd(s: str) -> str:
    """نرمال‌سازی متن برای مقایسه دقیق و بدون مشکل فاصله اضافی"""
    return " ".join((s or "").strip().lower().split())

def _get_auto_ignore_for_patterns(patterns):
    """پیدا کردن خودکار قوانین ignore بر اساس الگوی ورودی"""
    auto_ignores = []
    for p in patterns:
        key = _norm_cmd(p)
        if key in IGNORE_RULES:
            auto_ignores.extend(IGNORE_RULES[key])
    return list(dict.fromkeys(auto_ignores))

def _should_ignore(raw_text: str, ignores) -> bool:
    """بررسی اینکه آیا پیام فعلی باید نادیده گرفته شود یا خیر"""
    t = _norm_cmd(raw_text)
    for ign in ignores:
        ign_n = _norm_cmd(ign)
        if t.startswith(ign_n):
            return True
    return False

# ===============================
# Multi Language Decorator
# ===============================
def multi_lang(patterns, ignore=None, use_auto_ignore=True):
    if isinstance(patterns, str):
        patterns = [patterns]

    if ignore and isinstance(ignore, str):
        ignore = [ignore]

    # ignore مرکزی + ignore دستی
    auto_ignores = _get_auto_ignore_for_patterns(patterns) if use_auto_ignore else []
    manual_ignores = ignore or []
    final_ignores = list(dict.fromkeys(auto_ignores + manual_ignores))

    def decorator(func):
        @wraps(func)
        async def wrapper(event):
            if not event.out:
                return

            raw_text = (event.raw_text or "").strip()
            if not raw_text:
                return

            user_lang = get_lang(event.chat_id)

            # ------------------------------
            # اگر پیام جزو ignore ها بود، این handler اجرا نشود
            # ------------------------------
            if final_ignores and _should_ignore(raw_text, final_ignores):
                return

            # ------------------------------
            # ترجمه ورودی برای match کردن
            # ------------------------------
            if user_lang != "en":
                normalized = await translate(raw_text, "fa")
            else:
                normalized = raw_text

            text = normalized.lower()

            for pattern in patterns:
                if text.startswith(pattern.lower()):
                    event.ml_text = text
                    event.ml_args = text[len(pattern):].strip()
                    event.user_lang = user_lang
                    return await func(event)

        return wrapper

    return decorator

# ===============================
# Auto Reply (ترجمه پاسخ به زبان کاربر)
# ===============================
async def reply_auto(event, text):

    lang = getattr(event, "user_lang", get_lang(event.chat_id))

    if lang == BASE_LANG:
        return await event.reply(text)

    # خروجی فارسی ربات به زبان کاربر ترجمه میشه
    translated = await translate(text, lang)
    return await event.reply(translated)

# ===============================
# Auto Edit (ترجمه پاسخ به زبان کاربر)
# ===============================
async def edit_auto(event, text):

    lang = getattr(event, "user_lang", get_lang(event.chat_id))

    if lang == BASE_LANG:
        return await event.edit(text)

    # خروجی فارسی ربات به زبان کاربر ترجمه میشه
    translated = await translate(text, lang)
    return await event.edit(translated)
# ===============================
# Register Commands
# ===============================
def register_language_commands(client):

    # ask language on activation
    @client.on(events.NewMessage(
        incoming=True,
        func=lambda e: e.is_private and "Self Nix" in (e.raw_text or "")
    ))
    async def ask_language(event):

        if event.chat_id not in user_langs:
            await event.reply(get_lang_list_text())

    # change language
    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:زبان|language)\s+(\w+)"
    ))
    async def change_lang(event):

        lang = event.pattern_match.group(1).lower()

        if not set_lang(event.chat_id, lang):
            return await reply_auto(event, "Unsupported language")

        await reply_auto(
            event,
            f"Language changed to {SUPPORTED_LANGS[lang]}"
        )

    # show language list
    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:زبان|language)$"
    ))
    async def show_lang(event):

        await event.reply(get_lang_list_text())

    # manual translate
    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:ترجمه|translate)\s+(\w+)\s+(.+)"
    ))
    async def translate_command(event):

        lang = event.pattern_match.group(1).lower()
        text = event.pattern_match.group(2)

        if lang not in SUPPORTED_LANGS:
            return await event.reply("Invalid language")

        result = await translate(text, lang)
        await event.reply(result)
