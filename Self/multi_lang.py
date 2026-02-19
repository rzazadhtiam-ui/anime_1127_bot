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
# Auto Reply
# ===============================
# ===============================
# Multi Language Decorator
# ===============================
def multi_lang(patterns):

    if isinstance(patterns, str):
        patterns = [patterns]

    def decorator(func):

        @wraps(func)
        async def wrapper(event):

            if not event.out:
                return

            raw_text = (event.raw_text or "").strip()
            user_lang = get_lang(event.chat_id)

            # ==========================
            # ترجمه ورودی به انگلیسی برای اجرا
            # ==========================
            if user_lang != "en":
                normalized = await translate(raw_text, "fa")
            else:
                normalized = raw_text

            text = normalized.lower()

            for pattern in patterns:

                if text.startswith(pattern.lower()):
                    event.ml_text = text
                    event.ml_args = text[len(pattern):].strip()
                    # ذخیره زبان کاربر برای استفاده بعدی در پاسخ
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
