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
You are an autonomous coding agent.

You have access to a project.

FILES:
{files}

User request:
{text}

Return ONLY one of these actions:

1. READ_FILE:<path>
2. SHOW_LINES:<path>
3. GET_LINE:<path>:<number>
4. FIX_FILE:<path>
5. ANALYZE_PROJECT
6. ANSWER:<text>

Choose best action automatically.
""")

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
                {"role": "system", "content": "You are a coding agent."},
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

def detect_intent(text: str):
    t = text.lower()

    if "کتابخونه" in t or "وابستگی" in t or "نیاز" in t:  
        return "analyze"  

    if "فایل" in t or "پوشه" in t or "کد" in t:  
        return "scan"  

    if "گیت" in t or "ریپو" in t:  
        return "github"  
    
    if "اصلاح" in t or "فیکس" in t or "باگ" in t:  
        return "fix"  

    return "ai"

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

        files = scan_files("Self")

        decision = ai_router(text, "\n".join(files))

        decision = decision.strip()
    # ---------------- ANALYZE PROJECT ----------------  
        if decision.startswith("READ_FILE:"):
            path = decision.split(":", 1)[1].strip()

            content = read_file(path)

            await event.reply(content[:3500])
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
