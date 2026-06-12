import os
import telebot
import git
import requests
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPO_PATH = os.getenv("REPO_PATH")

bot = telebot.TeleBot(BOT_TOKEN)

USER_MODEL = {}   # user_id -> model
CHAT_MODE = {}    # user_id -> AI chat memory
MODELS_CACHE = []
# ================= MODELS =================
SYSTEM_PROMPT = """
You are a senior Python engineer and Telegram bot debugger.

Rules:
- پاسخ‌ها کوتاه، دقیق و فنی باشند
- فارسی روان و طبیعی
- اگر باگ هست دقیق تحلیل کن
- حدس نزن، اگر اطلاعات کافی نیست سوال بپرس
- فقط راه‌حل بده، نه حرف اضافه
"""

def get_models():
    url = "https://api.groq.com/openai/v1/models"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    r = requests.get(url, headers=headers)
    j = r.json()

    if "data" not in j:
        return ["❌ cannot load models", str(j)]

    return [m["id"] for m in j["data"]]

def refresh_models():
    global MODELS_CACHE

    try:
        MODELS_CACHE = get_models()
    except:
        MODELS_CACHE = ["llama-3.1-8b-instant"]

# ================= AI =================
def ask_ai(prompt, context="", model="llama-3.1-8b-instant"):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt + "\n\nCODE CONTEXT:\n" + context}
        ],
        "temperature": 0.2
    }

    r = requests.post(url, json=data, headers=headers)
    j = r.json()

    if "choices" not in j:
        return f"AI ERROR: {j}"

    return j["choices"][0]["message"]["content"]





# ================= FILE SEARCH (SMART) =================
def smart_search(keyword):
    results = []

    for root, _, files in os.walk(REPO_PATH):
        for f in files:
            path = os.path.join(root, f)

            try:
                text = open(path, "r", encoding="utf-8").read()

                if keyword.lower() in text.lower():
                    results.append(path.replace(REPO_PATH + "/", ""))

            except:
                pass

    return results[:30]

# ================= SCAN SYSTEM =================
def scan_pattern(pattern):
    hits = []

    for root, _, files in os.walk(REPO_PATH):
        for f in files:
            path = os.path.join(root, f)

            try:
                text = open(path, "r", encoding="utf-8").read()

                if pattern in text:
                    hits.append(path.replace(REPO_PATH + "/", ""))

            except:
                pass

    return hits[:20]

# ================= FILE OPS =================
def read_file(p):
    return open(os.path.join(REPO_PATH, p), "r", encoding="utf-8").read()

def write_file(p, data):
    open(os.path.join(REPO_PATH, p), "w", encoding="utf-8").write(data)

# ================= GIT =================
def git_push(msg):
    repo = git.Repo(REPO_PATH)
    repo.git.add(all=True)
    repo.index.commit(msg)
    repo.remote().push()

def git_pull():
    repo = git.Repo(REPO_PATH)
    repo.remote().pull()

# ================= MODEL PANEL =================
def model_panel():
    kb = types.InlineKeyboardMarkup()

    if not MODELS_CACHE:
        refresh_models()

    for m in MODELS_CACHE:
        kb.add(types.InlineKeyboardButton(f"🤖 {m}", callback_data=f"model|{m}"))

    kb.add(types.InlineKeyboardButton("🔄 refresh", callback_data="refresh_models"))

    return kb

# ================= MAIN MENU =================
def menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("📂 Files", callback_data="files"),
        types.InlineKeyboardButton("🔍 Search", callback_data="search")
    )

    kb.add(
        types.InlineKeyboardButton("🤖 Models", callback_data="models"),
        types.InlineKeyboardButton("⚙ Git", callback_data="git")
    )

    kb.add(
        types.InlineKeyboardButton("🧠 Scan Code", callback_data="scan")
    )

    return kb

# ================= HELP =================
HELP = """
🤖 ربات AI IDE

📌 قابلیت‌ها:
- چت مستقیم (بدون دستور)
- جستجوی فایل
- اسکن کد پروژه
- ویرایش با AI
- مدیریت Git
- انتخاب مدل هوش مصنوعی

📂 دستورها:
/help → راهنما
/search <text> → جستجو
/scan <text> → پیدا کردن در کل پروژه
/read <file> → نمایش فایل
/fix <file> → اصلاح با AI
/commit → ارسال به GitHub

💡 فقط پیام بده → AI جواب می‌دهد
"""

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "🚀 AI IDE Bot Ready", reply_markup=menu())

@bot.message_handler(commands=["help"])
def help_cmd(m):
    bot.reply_to(m, HELP)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id

    if c.data == "models":
        bot.send_message(c.message.chat.id, "مدل‌ها:", reply_markup=model_panel())

    elif c.data.startswith("model|"):
        model = c.data.split("|")[1]
        USER_MODEL[uid] = model
        bot.send_message(c.message.chat.id, f"✅ مدل فعال شد: {model}")

    elif c.data == "search":
        bot.send_message(c.message.chat.id, "🔍 از /search استفاده کن")

    elif c.data == "scan":
        bot.send_message(c.message.chat.id, "🧠 مثال: /scan ساعت")

    elif c.data == "files":
        files = os.listdir(REPO_PATH)[:30]
        bot.send_message(c.message.chat.id, "\n".join(files))

    elif c.data == "git":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬇ Pull", callback_data="pull"),
            types.InlineKeyboardButton("⬆ Push", callback_data="push")
        )
        bot.send_message(c.message.chat.id, "Git:", reply_markup=kb)

    elif c.data == "pull":
        git_pull()
        bot.send_message(c.message.chat.id, "⬇ Updated")

    elif c.data == "push":
        git_push("AI update")
        bot.send_message(c.message.chat.id, "⬆ Pushed")
    elif c.data == "refresh_models":
        refresh_models()
        bot.send_message(c.message.chat.id, "✅ models updated", reply_markup=model_panel())

# ================= NATURAL CHAT (NO COMMAND) =================
@bot.message_handler(func=lambda m: True)
def chat(m):
    uid = m.from_user.id
    model = USER_MODEL.get(uid, MODELS_CACHE[0] if MODELS_CACHE else "llama-3.1-8b-instant")

    text = m.text

    # اگر دستور نبود → AI chat
    if text.startswith("/"):
        return

    ctx = ""

    # context از چند فایل
    try:
        files = os.listdir(REPO_PATH)[:3]
        for f in files:
            p = os.path.join(REPO_PATH, f)
            if os.path.isfile(p):
                ctx += "\n\nFILE:" + f + "\n" + open(p).read()[:600]
    except:
        pass

    res = ask_ai(text, ctx, model=model)
    bot.reply_to(m, res[:4000])

# ================= RUN =================
bot.polling()
