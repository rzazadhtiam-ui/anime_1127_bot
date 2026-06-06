import os
import re
import base64
import requests
from telethon import events

# =========================
# CONFIG
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# ================================================================
# 🧠 AI CORE
# ================================================================

def ai_request(prompt: str):
    url = "https://api.groq.com/openai/v1/chat/completions"

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a senior software engineer and AI system analyst."
                },
                {"role": "user", "content": prompt}
            ]
        }
    )

    try:
        return res.json()["choices"][0]["message"]["content"]
    except:
        return str(res.json())


# ================================================================
# 📁 LOCAL PROJECT ENGINE
# ================================================================

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
    return list(set(re.findall(r"^(?:import|from)\s+([\w\.]+)", code, re.M)))


def analyze_project(base="Self"):
    files = scan_files(base)
    imports = set()

    for f in files:
        imports.update(extract_imports(read_file(f)))

    return {
        "files": len(files),
        "imports": list(imports)
    }


# ================================================================
# 🧬 GITHUB ENGINE
# ================================================================

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


# ================================================================
# 🧠 INTENT DETECTOR (NO COMMANDS)
# ================================================================

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


# ================================================================
# 🤖 AUTOPILOT ENGINE (MAIN BRAIN)
# ================================================================

def register_autopilot(client):

    @client.on(events.NewMessage)
    async def handler(event):

        text = (event.raw_text or "").strip()

        intent = detect_intent(text)

        # ---------------- ANALYZE PROJECT ----------------
        if intent == "analyze":
            data = analyze_project("Self")
            await event.reply(f"📦 Project Analysis:\n{data}")
            return

        # ---------------- SCAN FILES ----------------
        if intent == "scan":
            files = scan_files("Self")
            await event.reply("\n".join(files[:30]))
            return

        # ---------------- GITHUB MODE ----------------
        if intent == "github":
            repos = github_list()
            names = "\n".join([r["name"] for r in repos[:20]])
            await event.reply(names)
            return

        # ---------------- AI FIX MODE ----------------
        if intent == "fix":
            context = analyze_project("Self")
            result = ai_request(
                f"Find bugs and improve this project:\n{context}\n\nUser request:\n{text}"
            )
            await event.reply(result)
            return

        # ---------------- DEFAULT AI ----------------
        result = ai_request(text)
        await event.reply(result)
