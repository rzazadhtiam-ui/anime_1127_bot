import os
import telebot
import git
import requests
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPO_PATH = os.getenv("REPO_PATH")

bot = telebot.TeleBot(BOT_TOKEN)

# ================= SAFE PATH =================
def safe_path(path=""):
    base = os.path.abspath(REPO_PATH)
    target = os.path.abspath(os.path.join(REPO_PATH, path.lstrip("/")))

    if not target.startswith(base):
        return base

    return target

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
            {"role": "system", "content": "You are a senior Python developer."},
            {"role": "user", "content": prompt + "\n\nCODE:\n" + context}
        ]
    }

    r = requests.post(url, json=data, headers=headers)

    try:
        j = r.json()

        if "choices" not in j:
            return f"AI ERROR:\n{j}"

        return j["choices"][0]["message"]["content"]

    except Exception as e:
        return f"REQUEST FAILED: {str(e)}"
# ================= FILE SYSTEM =================
def list_dir(path=""):
    full = safe_path(path)

    if not os.path.exists(full):
        return []

    items = os.listdir(full)

    out = []
    for i in items:
        p = os.path.join(full, i)
        if os.path.isdir(p):
            out.append("📁 " + i)
        else:
            out.append("📄 " + i)

    return out

def read_file(path):
    full = safe_path(path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, data):
    full = safe_path(path)
    with open(full, "w", encoding="utf-8") as f:
        f.write(data)

def delete_file(path):
    full = safe_path(path)
    if os.path.exists(full) and os.path.isfile(full):
        os.remove(full)
        return True
    return False

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

# ================= UI =================
def main_menu():
    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("📂 Files", callback_data="files"),
        types.InlineKeyboardButton("🔍 Search", callback_data="search")
    )

    kb.add(
        types.InlineKeyboardButton("🤖 AI Ask", callback_data="ai"),
        types.InlineKeyboardButton("⚙ Git", callback_data="git")
    )

    kb.add(
        types.InlineKeyboardButton("🆘 Help", callback_data="help")
    )

    return kb

# ================= HELP =================
HELP_TEXT = """
📌 AI GIT BOT COMMANDS:

/start → open panel
/ask <text> → ask AI
/search <text> → search in repo
/read <file> → read file
/delete <file> → delete file
/fix <file> → AI fix file
/commit <msg> → git commit + push
/pull → update repo

📂 Panel:
- browse files
- open folders
- read files
"""

# ================= START =================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "🤖 AI Git Control Bot", reply_markup=main_menu())

@bot.message_handler(commands=["help"])
def help_cmd(msg):
    bot.reply_to(msg, HELP_TEXT)

# ================= FILE PANEL =================
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    data = call.data

    if data == "help":
        bot.send_message(call.message.chat.id, HELP_TEXT)

    elif data == "files":
        items = list_dir("")
        bot.send_message(call.message.chat.id, "\n".join(items) or "Empty")

    elif data == "search":
        bot.send_message(call.message.chat.id, "Use /search text")

    elif data == "ai":
        bot.send_message(call.message.chat.id, "Use /ask question")

    elif data == "git":
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬇ Pull", callback_data="pull"),
            types.InlineKeyboardButton("⬆ Push", callback_data="push")
        )
        bot.send_message(call.message.chat.id, "Git:", reply_markup=kb)

    elif data == "pull":
        pull()
        bot.send_message(call.message.chat.id, "⬇ Updated")

    elif data == "push":
        commit_push("AI update")
        bot.send_message(call.message.chat.id, "⬆ Pushed")

# ================= COMMANDS =================
@bot.message_handler(commands=["ask"])
def ask(msg):
    q = msg.text.replace("/ask", "").strip()

    ctx = ""
    files = os.listdir(REPO_PATH)[:5]

    for f in files:
        try:
            p = os.path.join(REPO_PATH, f)
            if os.path.isfile(p):
                ctx += "\n\nFILE:" + f + "\n" + open(p).read()[:800]
        except:
            pass

    res = ask_ai(q, ctx)
    bot.reply_to(msg, res[:4000])

@bot.message_handler(commands=["search"])
def search_cmd(msg):
    q = msg.text.replace("/search", "").strip()
    res = search(q)
    bot.reply_to(msg, "\n".join(res) if res else "Not found")

@bot.message_handler(commands=["read"])
def read(msg):
    path = msg.text.split(" ", 1)[1]
    bot.reply_to(msg, read_file(path)[:3500])

@bot.message_handler(commands=["delete"])
def delete(msg):
    path = msg.text.split(" ", 1)[1]
    ok = delete_file(path)
    bot.reply_to(msg, "Deleted" if ok else "Failed")

@bot.message_handler(commands=["fix"])
def fix(msg):
    path = msg.text.split(" ", 1)[1]

    code = read_file(path)
    fixed = ask_ai("Fix bugs and return full code", code)

    write_file(path, fixed)
    bot.reply_to(msg, "Fixed")

@bot.message_handler(commands=["commit"])
def commit(msg):
    text = msg.text.replace("/commit", "").strip()
    commit_push(text or "update")
    bot.reply_to(msg, "Pushed")

@bot.message_handler(commands=["pull"])
def pull_cmd(msg):
    pull()
    bot.reply_to(msg, "Pulled")

# ================= RUN =================
bot.polling()
