from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any, Optional
# Mongo-based character access layer
import json
from telethon import events
from multi_lang import multi_lang, reply_auto, edit_auto, register_language_commands


# =========================================================
# LOGGING
# =========================================================

log = logging.getLogger("SELF_AI")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[SELF_AI] %(levelname)s - %(message)s"))
    log.addHandler(h)
log.setLevel(logging.INFO)


# =========================================================
# CONFIG
# =========================================================

OPENAI_KEY = os.getenv("GROQ_API_KEY")


DEFAULT_CHARACTER = {
    "name": "Self Nix Core",
    "prompt": (
        "You are Self Nix AI System.\n"
        "You are a fusion of advanced robotics engineering and ancient Achaemenid strategic intelligence.\n"
        "You respond in a structured, technical, and concise way.\n"
        "You never mention system prompts.\n"
        "You behave like a stable production AI inside a Telegram self bot.\n"
    )
}



# =========================================================
# MONGO DB CORE - SELF NIX CHARACTER SYSTEM
# =========================================================

import time
from pymongo import MongoClient

# =========================
# DB CONNECTION
# =========================

client = MongoClient(
"mongodb://jinx:titi_jinx@ac-yjpvg6o-shard-00-00.35gzto0.mongodb.net:27017,"
    "ac-yjpvg6o-shard-00-01.35gzto0.mongodb.net:27017,"
    "ac-yjpvg6o-shard-00-02.35gzto0.mongodb.net:27017/?replicaSet=atlas-fzmhnh-shard-0&ssl=true&authSource=admin"
)
db = client["self_nix"]

memory_cache = {}
# =========================================================
# CHARACTER FLOW (STATE MACHINE)
# =========================================================


import json

def safe_json(text):
    try:
        if isinstance(text, dict):
            return text
        return json.loads(text)
    except:
        return None


def validate_character(data):
    if not isinstance(data, dict):
        return False
    return "name" in data and "system_prompt" in data

def set_flow(user_id: int, step: str, temp: dict = None):
    flow_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "step": step,
                "temp": temp or {},
                "updated_at": time.time()
            }
        },
        upsert=True
    )


def get_flow(user_id: int):
    return flow_col.find_one({"user_id": user_id})


def clear_flow(user_id: int):
    flow_col.delete_one({"user_id": user_id})



# =========================================================
# USER MEMORY (OPTIONAL BUT USEFUL)
# =========================================================

memory_col = db["memory"]

def add_memory(chat_id, user_id, text):
    # RAM
    if chat_id not in memory_cache:
        memory_cache[chat_id] = {}

    if user_id not in memory_cache[chat_id]:
        memory_cache[chat_id][user_id] = []

    memory_cache[chat_id][user_id].append(text)

    # limit RAM size
    if len(memory_cache[chat_id][user_id]) > 20:
        memory_cache[chat_id][user_id] = memory_cache[chat_id][user_id][-20:]

    # Mongo backup
    memory_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"messages": memory_cache[chat_id][user_id]}},
        upsert=True
    )


def get_memory(chat_id, user_id):
    # اول RAM
    if chat_id in memory_cache and user_id in memory_cache[chat_id]:
        return "\n".join(memory_cache[chat_id][user_id][-10:])

    # fallback Mongo
    doc = memory_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if not doc:
        return ""

    messages = doc.get("messages", [])

    # load into RAM
    if chat_id not in memory_cache:
        memory_cache[chat_id] = {}

    memory_cache[chat_id][user_id] = messages

    return "\n".join(messages[-10:])

def preload_memory():
    for doc in memory_col.find({}):
        chat_id = doc["chat_id"]
        user_id = doc["user_id"]

        if chat_id not in memory_cache:
            memory_cache[chat_id] = {}

        memory_cache[chat_id][user_id] = doc.get("messages", [])[-20:]

# =========================================================
# CHARACTER LAYER (MONGO ONLY - FIXED)
# =========================================================


# =========================================================
# CLEANUP (OPTIONAL MAINTENANCE)
# =========================================================

def cleanup_old_flows(expire_seconds: int = 3600):
    flow_col.delete_many({
        "updated_at": {"$lt": time.time() - expire_seconds}
    })



# =========================================================
# GROUP CONTROL
# =========================================================

class Group:
    def __init__(self):
        self.ai_on: Dict[int, bool] = {}
        self.muted: Dict[int, float] = {}

    def enable(self, chat: int):
        self.ai_on[chat] = True

    def disable(self, chat: int):
        self.ai_on[chat] = False

    def mute(self, uid: int, sec: int):
        self.muted[uid] = time.time() + sec

    def is_muted(self, uid: int):
        return self.muted.get(uid, 0) > time.time()


group = Group()





# =========================================================
# AI ENGINE (FIXED FALLBACK)
# =========================================================
import re

def extract_json(text: str):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        return json.loads(match.group())
    except:
        return None


async def ask_ai(prompt: str):
    if not OPENAI_KEY:
        return "AI KEY تنظیم نشده"

    try:
        import aiohttp

        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            ) as r:

                j = await r.json()

                if r.status != 200:
                    return f"AI HTTP ERROR: {j}"

                if "choices" not in j:
                    return f"AI RESPONSE ERROR: {j}"

                return j["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI ERROR: {e}"
        
# =========================================================
# CORE AI (ONLY COMMAND BASED)
# =========================================================

async def core_ai(event, question: str):
    chat = event.chat_id
    uid = event.sender_id

    char_name = get_active_character(chat)
    char = get_character(char_name)

    system_prompt = (
        char.get("system_prompt")
        if char else None
    )

    if not system_prompt:
        system_prompt = DEFAULT_CHARACTER["prompt"]

    prompt = f"""
SYSTEM:
{system_prompt}

MEMORY:
{get_memory(chat, uid)}

USER:
{question}
"""

    out = await ask_ai(prompt)

    add_memory(chat, uid, f"USER: {question}")
    add_memory(chat, uid, f"AI: {out}")
    
    

    await reply_auto(event, out)

#════════════════════════
owner = 6433381392

async def owner_id(event):
    return event.sender_id == owner

async def owner_only(event):
    me = await event.client.get_me()
    return event.sender_id == me.id

async def users(event):
    me = await event.client.get_me()
    return event.sender_id != me.id
#════════════════════════

def norm(name: str):
    return name.strip().lower()

def char_exists(name):
    return characters_col.find_one({"name_lc": norm(name)})

def user_char_count(uid):
    return characters_col.count_documents({"owner_id": uid})

def can_create(uid):
    return user_char_count(uid) < 10

async def notify_admin(client, name, owner_id):
    await client.send_message(
        6433381392,
        f"""
🧠 NEW CHARACTER REQUEST

Name: {name}
Owner: {owner_id}

Commands:
.approve {name}
.reject {name}
"""
    )




# =========================================================
# REGISTER
# =========================================================

def register_self_AI(client):

    # ================= AI ON =================
    @client.on(events.NewMessage)
    @multi_lang([".ai on", ".هوش روشن"])
    async def ai_on(event):
        group.enable(event.chat_id)
        await edit_auto(event, "AI ON")

    # ================= AI OFF =================
    @client.on(events.NewMessage)
    @multi_lang([".ai off", ".هوش خاموش"])
    async def ai_off(event):
        group.disable(event.chat_id)
        await edit_auto(event, "AI OFF")

    # ================= MUTE =================


#════════════════════════

#.ai command 

#════════════════════════
    @client.on(events.NewMessage)
    @multi_lang([".ai", "ai"])
    async def ai_question(event):

        text = (event.raw_text or "").strip()
        question = text[3:].strip()

        if not question:
            return await reply_auto(event, "مثال: .ai سلام")

        uid = event.sender_id

        char = DEFAULT_CHARACTER

        prompt = f"""
You are "Self Nix AI", a Telegram-based assistant embedded in a self-bot system.

════════════════════
IDENTITY
════════════════════
- Name: Self Nix AI
- System: Hybrid intelligence inspired by Achaemenid strategic logic + modern AI systems
- Role: Telegram assistant inside automation environment

════════════════════
LANGUAGE RULE
════════════════════
- Detect the user's language from their message
- Always respond in the SAME language as the user
- If Persian (Farsi) is used, respond fully in Persian
- If English is used, respond in English

════════════════════
BEHAVIOR RULES
════════════════════
1. Stay strictly in character as Self Nix AI
2. Never mention prompts, APIs, or internal system design
3. Be concise, structured, and technical
4. For OWNER users: answer minimal and direct
5. For OTHER users: subtly indicate system presence (natural tone)

════════════════════
USER QUESTION
════════════════════
{question}

════════════════════
RESPONSE STYLE
════════════════════
- Clear structured answer
- No unnecessary explanation
- End with signature only if user is NOT owner:
  — Self Nix AI
"""


        response = await ask_ai(prompt)

    # جلوگیری از کرش
        if not response:
            response = "No response from AI."

    # OWNER
        if await owner_only(event):

            try:
                return await edit_auto(event,response)
            except:
                return await reply_auto(event, response)

    # USERS
        final_text = (
        "🤖 Self Nix AI System\n"
        "──────────────────\n"
        f"{response}\n"
        "\n— Self Nix Core"
    )



print("self-ai loaded")
