import os
import telebot
import git
import requests

# ================= ENV (Termux only, no files) =================
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
            {"role": "system", "content": "You are a senior Python developer working on Telegram bots."},
            {"role": "user", "content": prompt + "\n\nCODE:\n" + context}
        ]
    }

    r = requests.post(url, json=data, headers=headers)
    return r.json()["choices"][0]["message"]["content"]

# ================= FILE SYSTEM =================
def list_files():
    out = []
    for r, _, f in os.walk(REPO_PATH):
        for i in f:
            out.append(os.path.join(r, i))
    return out[:50]

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
                if i.endswith(".py"):
                    if text in open(p, "r", encoding="utf-8").read():
                        res.append(p)
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

# ================= BOT COMMANDS =================

@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "AI Git Bot is running.")

@bot.message_handler(commands=["files"])
def files(msg):
    bot.reply_to(msg, "\n".join(list_files()))

@bot.message_handler(commands=["search"])
def search_cmd(msg):
    q = msg.text.replace("/search", "").strip()
    bot.reply_to(msg, "\n".join(search(q)) or "Not found")

@bot.message_handler(commands=["read"])
def read(msg):
    path = msg.text.split(" ", 1)[1]
    bot.reply_to(msg, read_file(path)[:3500])

@bot.message_handler(commands=["ask"])
def ask(msg):
    q = msg.text.replace("/ask", "")

    files = list_files()[:5]
    context = ""

    for f in files:
        try:
            context += "\n\nFILE:" + f + "\n" + read_file(f)[:800]
        except:
            pass

    result = ask_ai(q, context)
    bot.reply_to(msg, result[:4000])

@bot.message_handler(commands=["fix"])
def fix(msg):
    path = msg.text.split(" ", 1)[1]

    code = read_file(path)
    fixed = ask_ai("Fix all bugs and return full corrected code", code)

    write_file(path, fixed)
    bot.reply_to(msg, "File fixed.")

@bot.message_handler(commands=["commit"])
def commit(msg):
    text = msg.text.replace("/commit", "").strip()
    commit_push(text or "AI update")
    bot.reply_to(msg, "Pushed to GitHub.")

@bot.message_handler(commands=["pull"])
def pull_cmd(msg):
    pull()
    bot.reply_to(msg, "Pulled latest code.")

# ================= RUN =================
bot.polling()
