from telethon import events
from deep_translator import GoogleTranslator
from functools import wraps

BASE_LANG = "en"

# ===============================
# زبان‌های پشتیبانی شده
# ===============================
SUPPORTED_LANGS = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic",
    "hy": "Armenian", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian",
    "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan",
    "ceb": "Cebuano", "ny": "Chichewa", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "co": "Corsican", "hr": "Croatian",
    "cs": "Czech", "da": "Danish", "nl": "Dutch", "en": "English",
    "eo": "Esperanto", "et": "Estonian", "tl": "Filipino", "fi": "Finnish",
    "fr": "French", "fy": "Frisian", "gl": "Galician", "ka": "Georgian",
    "de": "German", "el": "Greek", "gu": "Gujarati", "ht": "Haitian Creole",
    "ha": "Hausa", "haw": "Hawaiian", "iw": "Hebrew", "hi": "Hindi",
    "hmn": "Hmong", "hu": "Hungarian", "is": "Icelandic", "ig": "Igbo",
    "id": "Indonesian", "ga": "Irish", "it": "Italian", "ja": "Japanese",
    "jw": "Javanese", "kn": "Kannada", "kk": "Kazakh", "km": "Khmer",
    "ko": "Korean", "ku": "Kurdish (Kurmanji)", "ky": "Kyrgyz", "lo": "Lao",
    "la": "Latin", "lv": "Latvian", "lt": "Lithuanian", "lb": "Luxembourgish",
    "mk": "Macedonian", "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam",
    "mt": "Maltese", "mi": "Maori", "mr": "Marathi", "mn": "Mongolian",
    "my": "Myanmar (Burmese)", "ne": "Nepali", "no": "Norwegian", "ps": "Pashto",
    "fa": "Persian", "pl": "Polish", "pt": "Portuguese", "pa": "Punjabi",
    "ro": "Romanian", "ru": "Russian", "sm": "Samoan", "gd": "Scots Gaelic",
    "sr": "Serbian", "st": "Sesotho", "sn": "Shona", "sd": "Sindhi",
    "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali",
    "es": "Spanish", "su": "Sundanese", "sw": "Swahili", "sv": "Swedish",
    "tg": "Tajik", "ta": "Tamil", "te": "Telugu", "th": "Thai", "tr": "Turkish",
    "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese",
    "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", "zu": "Zulu",
    "ja": "Japanese"
}

_translate_cache = {}
user_langs = {}            # زبان کاربر
user_auto_translate = {}   # ترجمه خودکار روشن/خاموش
user_auto_lang = {}        # زبان ترجمه خودکار

# ===============================
# متدهای کمکی
# ===============================
def get_lang(user_id):
    return user_langs.get(user_id, BASE_LANG)

def set_lang(user_id, lang):
    lang = lang.lower()
    if lang not in SUPPORTED_LANGS:
        return False
    user_langs[user_id] = lang
    return True

def get_lang_list_text():
    text = "🌐 لطفا زبان خود را انتخاب کنید / Please choose your language:\n\n"
    for code, name in SUPPORTED_LANGS.items():
        text += f"{code} → {name}\n"
    return text

async def translate(text, target):
    key = f"{text}:{target}"
    if key in _translate_cache:
        return _translate_cache[key]
    try:
        translated = GoogleTranslator(source="auto", target=target).translate(text)
        _translate_cache[key] = translated
        return translated
    except:
        return text

async def reply_auto(event, text):
    lang = get_lang(event.sender_id)
    if lang == BASE_LANG:
        return await event.reply(text)
    translated = await translate(text, lang)
    return await event.reply(translated)

# ===============================
# دکوراتور چندزبانه
# ===============================
def multi_lang(patterns):
    if isinstance(patterns, str):
        patterns = [patterns]
    def decorator(func):
        @wraps(func)
        async def wrapper(event):
            if not event.out:
                return
            text = (event.raw_text or "").strip().lower()
            user_lang = get_lang(event.sender_id)
            for pattern in patterns:
                if text.startswith(pattern.lower()):
                    event.ml_text = text
                    event.ml_args = text[len(pattern):].strip()
                    return await func(event)
        return wrapper
    return decorator

# ===============================
# ثبت دستورات
# ===============================
def register_language_commands(client):

    # درخواست انتخاب زبان هنگام فعال شدن ربات
    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and "ربات ⦁ Self Nix برای شما فعال شد" in (e.raw_text or "")))
    async def ask_language_on_activation(event):
        if event.sender_id not in user_langs:
            await event.reply(get_lang_list_text())

    # تغییر زبان دستی
    @client.on(events.NewMessage(pattern=r"\.(?:زبان|language) (.+)"))
    async def change_lang(event):
        lang = event.pattern_match.group(1).lower()
        if not set_lang(event.sender_id, lang):
            return await reply_auto(event, "❌ این زبان پشتیبانی نمی‌شود / Unsupported language")
        await reply_auto(event, f"✅ زبان به {SUPPORTED_LANGS[lang]} تغییر کرد / Language set to {SUPPORTED_LANGS[lang]}")

    # نمایش لیست زبان‌ها
    @client.on(events.NewMessage(pattern=r"\.(?:زبان|language)$"))
    async def show_lang(event):
        await event.reply(get_lang_list_text())

    # ===============================
    # ترجمه دستی
    # ===============================
    @client.on(events.NewMessage(pattern=r"\.(?:ترجمه|translate) (\w+) (.+)"))
    async def translate_command(event):
        lang = event.pattern_match.group(1).lower()
        text = event.pattern_match.group(2)
        try:
            translated = await translate(text, lang)
            await event.reply(translated)
        except Exception as e:
            await event.reply(f"⚠️ خطا در ترجمه: {e}")

    # ===============================
    # ترجمه خودکار
    # ===============================
    