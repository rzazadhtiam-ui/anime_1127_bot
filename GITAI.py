import os
import telebot
import git
import requests
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPO_PATH = os.getenv("REPO_PATH")

bot = telebot.TeleBot(BOT_TOKEN)

# ================= AI =================
def ask_ai(prompt, context=""):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a senior developer for Telegram bots."},
            {"role": "user", "content": prompt + "\n\nCODE:\n" + context}
        ]
    }

    r = requests.post(url, json=data, headers=headers)
    return r.json()["choices"][0]["message"]["content"]

# ================= FILE SYSTEM =================
def list_dir(path=""):
    full = os.path.join(REPO_PATH, path)
    items = os.listdir(full)

    folders = []
    files = []

    for i in items:
        if os.path.isdir(os.path.join(full, i)):
            folders.append("📁 " + i)
        else:
            files.append("📄 " + i)

    return folders + files

def read_file(path):
    full = os.path.join(REPO_PATH, path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, data):
    full = os.path.join(REPO_PATH, path)
    with open(full, "w", encoding="utf-8") as f:
        f.write(data)

def search(text):
    res = []
    for r, _, f in os.walk(REPO_PATH):
        for i in f:
            try:
                p = os.path.join(r, i)
                if text.lower() in open(p, "r", encoding="utf-8").read().lower():
                    res.append(p.replace(REPO_PATH + "/", ""))
            except:
                pass
    return res[:30]

# ================= GIT =================
def commit_push(msg):
    repo = git.Repo(REPO_PATH)
    repo.git.add(all=True)
    repo.index.commit(msg)
    repo.remote().push()

def pull():
    repo = git.Repo(REPO_PATH)
    repo.remote().pull()

# ================= UI HELPERS =================
def main_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("📂 Files", callback_data="files"),
        types.InlineKeyboardButton("🔍 Search", callback_data="search")
    )

    kb.add(
        types.InlineKeyboardButton("🤖 Ask AI", callback_data="ask"),
        types.InlineKeyboardButton("🔧 Git Tools", callback_data="git")
    )

    return kb

def files_menu(path=""):
    kb = types.InlineKeyboardMarkup()

    items = list_dir(path)

    for i in items[:20]:
        name = i[2:]
        if i.startswith("📁"):
            kb.add(types.InlineKeyboardButton(i, callback_data=f"cd|{path}/{name}"))
        else:
            kb.add(types.InlineKeyboardButton(i, callback_data=f"read|{path}/{name}"))

    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back"))

    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "🤖 AI Git Control Bot", reply_markup=main_menu())

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    data = call.data

    # MAIN FILES
    if data == "files":
        bot.edit_message_text(
            "📂 Repository Files:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=files_menu("")
        )

    # NAVIGATE
    elif data.startswith("cd|"):
        path = data.split("|")[1]
        bot.edit_message_text(
            f"📂 {path}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=files_menu(path)
        )

    # READ FILE
    elif data.startswith("read|"):
        path = data.split("|")[1]

        try:
            content = read_file(path)
            bot.send_message(call.message.chat.id, content[:3500])
        except:
            bot.send_message(call.message.chat.id, "❌ Cannot read file")

    # SEARCH
    elif data == "search":
        res = search(".py")
        bot.send_message(call.message.chat.id, "\n".join(res) or "Not found")

    # ASK AI
    elif data == "ask":
        bot.send_message(call.message.chat.id, "Use: /ask your question")

    # GIT MENU
    elif data == "git":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬇ Pull", callback_data="pull"),
            types.InlineKeyboardButton("⬆ Push", callback_data="push")
        )
        bot.send_message(call.message.chat.id, "Git tools:", reply_markup=kb)

    elif data == "pull":
        pull()
        bot.send_message(call.message.chat.id, "⬇ Pulled")

    elif data == "push":
        commit_push("AI update")
        bot.send_message(call.message.chat.id, "⬆ Pushed")

# ================= COMMANDS =================
@bot.message_handler(commands=["ask"])
def ask(msg):
    q = msg.text.replace("/ask", "").strip()

    files = os.listdir(REPO_PATH)[:5]
    ctx = ""

    for f in files:
        try:
            p = os.path.join(REPO_PATH, f)
            if os.path.isfile(p):
                ctx += f"\n\nFILE:{f}\n" + open(p).read()[:800]
        except:
            pass

    res = ask_ai(q, ctx)
    bot.reply_to(msg, res[:4000])

# ================= RUN =================
bot.polling()
