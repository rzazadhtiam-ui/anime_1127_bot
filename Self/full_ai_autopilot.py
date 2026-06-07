import os
import re
import base64
import requests
from telethon import events

#=========================

#CONFIG

#=========================

GROQ_API_KEY = "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"
GITHUB_TOKEN = "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"

#================================================================

#🧠 AI CORE

#================================================================

def ai_router(text, files):
    return ai_request(f"""
تو یک AI Agent هستی.

فایل های پروژه:

{files}

فقط یکی از خروجی های زیر را برگردان:

READ_FILE:<path>
SHOW_LINES:<path>
GET_LINE:<path>:<number>
ANALYZE_PROJECT
ANSWER:<text>

هیچ توضیح اضافه ننویس.

درخواست کاربر:
{text}
""").strip()

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
    "content": """
تو Self Nix AI هستی؛ یک دستیار حرفه‌ای برنامه‌نویسی، تحلیلگر کد و مدیر پروژه.

قوانین:

- همیشه به زبان فارسی پاسخ بده.
- لحن طبیعی، روان، دوستانه و فنی داشته باش.
- از ترجمه ماشینی، عبارت‌های عجیب و واژه‌های غیرطبیعی استفاده نکن.
- پاسخ‌ها را واضح، دقیق و کاربردی بنویس.
- اگر کاربر سلام یا گفت‌وگوی عادی داشت، طبیعی پاسخ بده.
- اگر سؤال برنامه‌نویسی پرسید، پاسخ فنی و عملی ارائه کن.
- اگر اطلاعات کافی نداری، حدس نزن و سؤال بپرس.
- اگر مطمئن نیستی، این موضوع را اعلام کن.

قوانین فایل و پروژه:

- فقط از فایل‌ها و پوشه‌هایی که واقعاً در پروژه وجود دارند استفاده کن.
- هرگز نام فایل، تابع، کلاس یا ماژول خیالی نساز.
- اگر فایل موردنظر پیدا نشد، صریحاً بگو «فایل پیدا نشد».
- اگر کاربر درخواست خواندن فایل کرد، ابتدا فایل را بررسی کن و سپس پاسخ بده.
- اگر کاربر درخواست تعداد خطوط فایل را داد، تعداد خطوط را اعلام کن.
- اگر کاربر درخواست مشاهده یک خط خاص را داد، فقط همان خط را نمایش بده.
- اگر کاربر درخواست تحلیل فایل را داد، ساختار، مشکلات، باگ‌های احتمالی و پیشنهادهای بهبود را توضیح بده.
- اگر کاربر درخواست تحلیل پروژه را داد، فایل‌های مهم، وابستگی‌ها، معماری و مشکلات احتمالی را بررسی کن.
- اگر کاربر درخواست رفع باگ داد، علت باگ، محل احتمالی و راه‌حل را توضیح بده.
- اگر کاربر درخواست بهبود کد داد، تغییرات کمینه، منطقی و امن پیشنهاد کن.
- هرگز بدون درخواست کاربر فایل‌ها را تغییر نده.
- هرگز اطلاعات ساختگی تولید نکن.

تخصص‌ها:

- Python
- Telethon
- Telegram UserBot
- Telegram Bot
- MongoDB
- AsyncIO
- APIs
- GitHub
- Software Architecture
- Debugging

هدف اصلی:

کمک به توسعه، تحلیل، اشکال‌زدایی و مدیریت پروژه Self Nix با بیشترین دقت ممکن و ارائه پاسخ‌های فارسی، فنی و قابل اجرا.
"""
},
                {"role": "user", "content": prompt}
            ]
        }
    )

    return res.json()["choices"][0]["message"]["content"]

#================================================================

#📁 LOCAL PROJECT ENGINE

#================================================================
def scan_files(base="Self"):
    result = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".py"):
                result.append(os.path.join(root, f))
    return result


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def extract_imports(code):
    return list(set(
        re.findall(r"^(?:import|from)\s+([\w\.]+)", code, re.M)
    ))


def get_lines(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()
    except:
        return []


def analyze_project(base="Self"):
    files = scan_files(base)
    imports = set()

    for f in files:
        content = read_file(f)
        imports.update(extract_imports(content))

    return {
        "files": len(files),
        "imports": list(imports)
    }

#================================================================

#🧬 GITHUB ENGINE

#================================================================

def gh_headers():
    return {
"Authorization": f"Bearer {GITHUB_TOKEN}",
"Accept": "application/vnd.github+json"
}

def github_list():
    return requests.get(
"https://api.github.com/user/repos",
    headers=gh_headers()
    ).json()

def github_create(name):
    return requests.post(
"https://api.github.com/user/repos",
    headers=gh_headers(),
    json={"name": name, "private": True}
    ).json()

def github_read(owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    return requests.get(url, headers=gh_headers()).json()

def github_write(owner, repo, path, content):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    encoded = base64.b64encode(content.encode()).decode()

    return requests.put(  
    url,  
    headers=gh_headers(),  
    json={  
        "message": "auto update by AI agent",  
        "content": encoded  
    }  
).json()

#================================================================

#🧠 INTENT DETECTOR (NO COMMANDS)

#================================================================

def find_file(name, base="Self"):
    for root, _, files in os.walk(base):
        for f in files:
            if name.lower() in f.lower():
                return os.path.join(root, f)
    return None
#================================================================

#🤖 AUTOPILOT ENGINE (MAIN BRAIN)

#================================================================

from telethon import events

ADMIN_ID = 6433381392

def register_autopilot(client):

    @client.on(events.NewMessage(outgoing=True))
    async def handler(event):

        me = await client.get_me()

        if event.chat_id != me.id:
            return

        text = event.raw_text.strip()
        
        if not text.startswith(".tjm "):
            return

        text = text[5:].strip()

        files = scan_files("Self")

        decision = ai_router(text, "\n".join(files))

        decision = decision.strip()
    # ---------------- ANALYZE PROJECT ----------------  
        if decision.startswith("READ_FILE:"):
            path = decision.split(":", 1)[1].strip()

        if not os.path.exists(path):
            path = find_file(path)

        if not path:
            await event.reply("فایل پیدا نشد")
            return


        if decision.startswith("SHOW_LINES:"):
            path = decision.split(":", 1)[1].strip()

            lines = get_lines(path)

            await event.reply(str(len(lines)))
            return


        if decision.startswith("GET_LINE:"):
            _, path, num = decision.split(":")
            num = int(num)

            lines = get_lines(path)

            if num <= len(lines):
                await event.reply(lines[num - 1])
            else:
                await event.reply("خط وجود ندارد")

            return


        if decision.startswith("ANALYZE_PROJECT"):
            data = analyze_project("Self")
            await event.reply(str(data))
            return


        if decision.startswith("ANSWER:"):
            await event.reply(decision.replace("ANSWER:", "", 1))
            return
