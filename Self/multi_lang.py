import asyncio
from telethon import events
from deep_translator import GoogleTranslator
from functools import wraps

BASE_LANG = "fa"

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

# ==========================================
# Language
# ==========================================

def get_lang_from_user(user):
    lang = getattr(user, "language_code", None)
    return lang if lang in SUPPORTED_LANGS else BASE_LANG

def set_lang(chat_id, lang):
    lang = str(lang).lower()

    if lang not in SUPPORTED_LANGS:
        return False

    user_langs[chat_id] = lang
    return True

def get_lang_list_text():
    txt = "🌐 Languages\n\n"

    for code, name in SUPPORTED_LANGS.items():
        txt += f"{code} → {name}\n"

    return txt

def get_lang(user):
    return get_lang_from_user(user)

# ==========================================
# Translator
# ==========================================

async def translate(text, target):

    if not text:
        return ""

    try:

        key = f"{text}:{target}"

        if key in _translate_cache:
            return _translate_cache[key]

        result = await asyncio.to_thread(
            lambda: GoogleTranslator(
                source="auto",
                target=target
            ).translate(text)
        )

        if not result:
            return text

        _translate_cache[key] = result

        if len(_translate_cache) > 500:
            _translate_cache.clear()

        return result

    except:
        return text

# ==========================================
# Ignore Rules
# ==========================================

IGNORE_RULES = {

    ".ساعت": [
        ".ساعت خاموش",
        ".ساعت اسم",
        ".ساعت بیو",
        ".ساعت کلی",
        ".ساعت جهانی",
        ".ساعت منطقه",
        ".ساعت فونت"
    ],

    ".clock": [
        ".clock off",
        ".clock name",
        ".clock bio",
        ".clock all",
        ".clock utc",
        ".clock region",
        ".clock font"
    ]
}

def _norm(text):

    return " ".join(
        str(text).strip().lower().split()
    )

def _auto_ignore(patterns):

    result = []

    for p in patterns:

        p = _norm(p)

        if p in IGNORE_RULES:
            result.extend(IGNORE_RULES[p])

    return list(dict.fromkeys(result))

def _should_ignore(text, ignores):

    t = _norm(text)

    for ign in ignores:

        if t.startswith(_norm(ign)):
            return True

    return False

# ==========================================
# Multi Language Decorator
# ==========================================

def multi_lang(patterns, ignore=None, use_auto_ignore=True):

    if isinstance(patterns, str):
        patterns = [patterns]

    if isinstance(ignore, str):
        ignore = [ignore]

    auto = _auto_ignore(patterns) if use_auto_ignore else []

    ignores = list(
        dict.fromkeys(
            auto + (ignore or [])
        )
    )

    def decorator(func):

        @wraps(func)
        async def wrapper(event):

            try:

                if not getattr(event, "out", False):
                    return

                raw = getattr(event, "raw_text", None)

                if not isinstance(raw, str):
                    return

                raw = raw.strip()

                if not raw:
                    return

                if ignores and _should_ignore(raw, ignores):
                    return

                text = raw.lower()

                for pattern in patterns:

                    p = pattern.lower()

                    if text.startswith(p):

                        event.ml_text = text
                        event.ml_args = text[len(p):].strip()
                        event.user_lang = get_lang(event.chat_id)

                        return await func(event)

            except Exception as e:

                print(
                    f"[MULTI_LANG ERROR] "
                    f"{func.__name__}: {e}"
                )

        return wrapper

    return decorator

# ==========================================
# Auto Reply
# ==========================================

async def reply_auto(event, text, file=None, **kwargs):
    try:

        lang = getattr(
            event,
            "user_lang",
            get_lang_from_user(event.sender)
        )

        if lang == BASE_LANG:
            return await event.reply(text, file=file, **kwargs)

        translated = await translate(text, lang)

        return await event.reply(translated, file=file, **kwargs)

    except Exception as e:
        print(f"[REPLY_AUTO] {e}")
# ==========================================
# Auto Edit
# ==========================================

async def edit_auto(event, text, file=None, **kwargs):
    try:

        lang = getattr(
            event,
            "user_lang",
            get_lang_from_user(event.sender)
        )

        if lang == BASE_LANG:
            return await event.edit(text, file=file, **kwargs)

        translated = await translate(text, lang)

        return await event.edit(translated, file=file, **kwargs)

    except Exception as e:
        print(f"[EDIT_AUTO] {e}")

# ==========================================
# Register Commands
# ==========================================

def register_language_commands(client):

    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:زبان|language)$"
    ))
    async def show_lang(event):

        await event.edit(
            get_lang_list_text()
        )

    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:زبان|language)\s+(\w+)"
    ))
    async def set_language(event):

        lang = event.pattern_match.group(1).lower()

        if not set_lang(event.chat_id, lang):
            return await event.edit(
                "Invalid language"
            )

        await event.edit(
            f"Language changed to {SUPPORTED_LANGS[lang]}"
        )

    @client.on(events.NewMessage(
        outgoing=True,
        pattern=r"\.(?:ترجمه|translate)\s+(\w+)\s+(.+)"
    ))
    async def translate_cmd(event):

        lang = event.pattern_match.group(1).lower()

        text = event.pattern_match.group(2)

        if lang not in SUPPORTED_LANGS:
            return await event.edit(
                "Invalid language"
            )

        result = await translate(
            text,
            lang
        )

        await event.edit(result)
