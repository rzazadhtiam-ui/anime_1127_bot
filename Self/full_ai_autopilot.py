import os
import re
import base64
import requests
from telethon import events

# ================= CONFIG =================

GROQ_API_KEY = "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"
GITHUB_TOKEN = "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"

BASE_DIR = "Self"

ADMIN_ID = 6433381392

# ================= AI =================

def ai_request(prompt: str):
    url = "https://api.groq.com/openai/v1/chat/completions"

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Self Nix AI"
                },
                {"role": "user", "content": prompt}
            ]
        }
    )

    return res.json()["choices"][0]["message"]["content"]


def ai_router(text, files):
    return ai_request(f"""
تو یک AI Agent برای مدیریت پروژه هستی.

فایل ها:
{files}

فقط یکی از این خروجی ها:

READ_FILE:<path>
SHOW_LINES:<path>
GET_LINE:<path>:<num>
ANALYZE_PROJECT
LIST_FILES
PROJECT_TREE
SEARCH:<keyword>

CREATE_FILE:<path>
DELETE_FILE:<path>
WRITE_FILE:<path>
APPEND_FILE:<path>
RENAME_FILE:<old>:<new>
REPLACE_FILE:<path>

DEBUG_FILE:<path>
ANSWER:<text>

درخواست:
{text}
""").strip()

# ================= FILE ENGINE =================

def scan_files(base=BASE_DIR):
    out = []
    for r, _, f in os.walk(base):
        for i in f:
            if i.endswith(".py"):
                out.append(os.path.join(r, i))
    return out


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def append_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def delete_file(path):
    if os.path.exists(path):
        os.remove(path)


def list_files():
    return scan_files()


def search_files(keyword):
    res = []
    for f in scan_files():
        if keyword.lower() in f.lower():
            res.append(f)
    return res


def resolve_path(path, base=BASE_DIR):
    if os.path.exists(path):
        return path

    for r, _, files in os.walk(base):
        for f in files:
            full = os.path.join(r, f)
            if f.lower() == path.lower():
                return full
            if full.lower().endswith(path.lower()):
                return full
    return None


def get_lines(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()
    except:
        return []


def analyze_project():
    files = scan_files()
    return {
        "files": len(files),
    }

# ================= DEBUG =================

def debug_file(path):
    code = read_file(path)
    return ai_request(f"""
این فایل را دیباگ کن:

کد:
{code}
""")

# ================= CORE HANDLER =================

def register_autopilot(client):

    @client.on(events.NewMessage(outgoing=True))
    async def handler(event):

        me = await client.get_me()
        if event.chat_id != me.id:
            return

        text = event.raw_text.strip()

        if not text.startswith(".tjm"):
            return

        query = text[4:].strip()

        files = "\n".join(scan_files())

        decision = ai_router(query, files)

        # ========== GET LINE ==========
        if decision.startswith("GET_LINE:"):
            _, path, num = decision.split(":")
            path = resolve_path(path)

            if not path:
                await event.reply("فایل پیدا نشد")
                return

            try:
                num = int(num)
                lines = get_lines(path)
                await event.reply(lines[num - 1])
            except:
                await event.reply("خطا در خواندن خط")
            return

        # ========== READ ==========
        if decision.startswith("READ_FILE:"):
            path = resolve_path(decision.split(":")[1])
            await event.reply(read_file(path)[:4000])
            return

        # ========== LIST ==========
        if decision == "LIST_FILES":
            await event.reply("\n".join(list_files())[:4000])
            return

        # ========== SEARCH ==========
        if decision.startswith("SEARCH:"):
            key = decision.split(":", 1)[1]
            res = search_files(key)
            await event.reply("\n".join(res)[:4000])
            return

        # ========== CREATE FILE ==========
        if decision.startswith("CREATE_FILE:"):
            path = decision.split(":", 1)[1]
            write_file(path, "")
            await event.reply("ساخته شد")
            return

        # ========== DELETE ==========
        if decision.startswith("DELETE_FILE:"):
            path = resolve_path(decision.split(":", 1)[1])
            delete_file(path)
            await event.reply("حذف شد")
            return

        # ========== WRITE ==========
        if decision.startswith("WRITE_FILE:"):
            try:
                _, path, content = decision.split(":", 2)
                write_file(path, content)
                await event.reply("آپدیت شد")
            except:
                await event.reply("خطا در نوشتن")
            return

        # ========== DEBUG ==========
        if decision.startswith("DEBUG_FILE:"):
            path = resolve_path(decision.split(":")[1])
            result = debug_file(path)
            await event.reply(result[:4000])
            return

        # ========== ANSWER ==========
        if decision.startswith("ANSWER:"):
            await event.reply(decision[7:])
            return
