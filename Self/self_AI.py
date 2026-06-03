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

OPENAI_KEY = "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"


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

characters_col = db["characters"]
flow_col = db["character_flow"]

# =========================================================
# CHARACTER FLOW (STATE MACHINE)
# =========================================================

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
# CHARACTER SYSTEM
# =========================================================
def create_character(name: str, owner_id: int, data: dict):
    characters_col.insert_one({
        "name": name,
        "owner_id": owner_id,
        "status": "pending",
        "data": data,
        "created_at": time.time()
    })


def get_character(name: str):
    if not name:
        return None

    return characters_col.find_one({
        "name": name.replace(".", "").strip(),
        "status": "global"
    })


def get_character_owner(name: str):
    return characters_col.find_one({
        "name": name.replace(".", "").strip()
    })


def approve_character(name: str):
    characters_col.update_one(
        {"name": name},
        {"$set": {"status": "global"}}
    )


def reject_character(name: str):
    characters_col.update_one(
        {"name": name},
        {"$set": {"status": "rejected"}}
    )

# =========================================================
# ACTIVE CHARACTER PER CHAT (STORAGE IN DB OPTIONAL)
# =========================================================

active_col = db["active_characters"]

def set_active_character(chat_id: int, name: str):
    active_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"name": name}},
        upsert=True
    )


def get_active_character(chat_id: int):
    doc = active_col.find_one({"chat_id": chat_id})
    return doc["name"] if doc else None

# =========================================================
# USER MEMORY (OPTIONAL BUT USEFUL)
# =========================================================

memory_col = db["memory"]

def add_memory(chat_id: int, user_id: int, text: str):
    memory_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$push": {
                "messages": {
                    "$each": [text],
                    "$slice": -20
                }
            }
        },
        upsert=True
    )


def get_memory(chat_id: int, user_id: int):
    doc = memory_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if not doc:
        return ""
    return "\n".join(doc.get("messages", [])[-10:])


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


async def generate_character_ai(name: str):
    prompt = f"""
You are a strict JSON generator.

RULES:
- Fill ALL fields completely
- No empty values
- Output ONLY valid JSON (no explanation)

Create character for: {name}

Return:
{{
  "name": "{name}",
  "personality_fa": "full Persian description of personality",
  "tone_fa": "tone description",
  "speaking_style_fa": "speaking style",
  "rules_fa": ["rule1", "rule2", "rule3"],
  "system_prompt": "full system prompt for AI behavior"
}}
"""
    return await ask_ai(prompt)

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
                    "model": "llama-3.3-70b-versatile",
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
    char.get("data", {}).get("system_prompt")
    if char else None
)

    if not system_prompt:
    	system_prompt = DEFAULT_CHARACTER["system_prompt"]

    prompt = f"""
SYSTEM:
{system_prompt}

MEMORY:
{memory.get(chat, uid)}

USER:
{question}
"""

    out = await ask_ai(prompt)
    await reply_auto(event, out)

def safe_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None

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


    # ================= CREATE CHARACTER =================
    @client.on(events.NewMessage)
    @multi_lang([".char create", ".ساخت کاراکتر"])
    async def start_char(event):
        uid = event.sender_id

        set_flow(uid, "WAIT_NAME", {
    "chat_id": event.chat_id
})

        await edit_auto(event,
        "فرآیند ساخت کاراکتر فعال شد.\n"
        "نام کاراکتر را ارسال کنید."
    )
    # ================= EDIT CHARACTER =================
    @client.on(events.NewMessage)
    @multi_lang([".char edit", ".ادیت کاراکتر"])
    async def edit_char(event):
        parts = event.raw_text.split(maxsplit=3)
        if len(parts) < 4:
            return await edit_auto(event, "Usage: .char edit name prompt")

        name = parts[2]
        prompt = parts[3]
        chars.edit(event.sender_id, name, prompt)
        await edit_auto(event, "Character updated")

    # ================= SELECT CHARACTER =================
    @client.on(events.NewMessage)
    @multi_lang([".char use", ".کاراکتر"])
    async def use_char(event):
        name = event.raw_text.split(maxsplit=1)[1]

        set_active_character(event.chat_id, name)

        await reply_auto(event, f"Active character: {name}")

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




#════════════════════════
    flow_lock = set()  # جلوگیری از دوبار اجرا شدن همزمان per user


    # =====================================================
    # FLOW HANDLER
    # =====================================================
    @client.on(events.NewMessage)
    async def char_flow(event):

        uid = event.sender_id
        text = (event.raw_text or "").strip()

        flow = get_flow(uid)
        if not flow:
            return

        if flow.get("chat_id") and flow["chat_id"] != event.chat_id:
            return

        step = flow.get("step")
        temp = flow.get("temp", {}) or {}

        # =========================
        # STEP 1: NAME
        # =========================
        if step == "WAIT_NAME":

            if event.is_reply:
                return await reply_auto(event, "❌ فقط اسم را مستقیم ارسال کن")

            if text.startswith(".") or text.startswith("/"):
                return await reply_auto(event, "❌ فقط اسم کاراکتر را ارسال کن")

            name = text.strip()

            if len(name) < 2 or len(name) > 30:
                return await reply_auto(event, "❌ نام نامعتبر است")

            set_flow(uid, "GENERATING", {
                "name": name,
                "chat_id": event.chat_id
            })

            await reply_auto(event, "⏳ در حال ساخت شخصیت...")

            ai_result = await generate_character_ai(name)
            data = safe_json(ai_result)

            if not data:
                set_flow(uid, "WAIT_NAME", {"chat_id": event.chat_id})
                return await reply_auto(event, "❌ خطا در ساخت شخصیت، دوباره اسم را بفرست")

            data.setdefault("personality_fa", "نامشخص")
            data.setdefault("tone_fa", "نامشخص")
            data.setdefault("speaking_style_fa", "نامشخص")
            data.setdefault("rules_fa", ["بدون قانون"])

            set_flow(uid, "CONFIRM", {
                "name": name,
                "ai": data,
                "chat_id": event.chat_id
            })

            rules_text = "\n• ".join(data["rules_fa"])

            preview = f"""
📌 پیش‌نمایش شخصیت

👤 نام:
{name}

🧠 شخصیت:
{data['personality_fa']}

🎭 لحن:
{data['tone_fa']}

🗣 سبک صحبت:
{data['speaking_style_fa']}

📜 قوانین:
• {rules_text}

تایید می‌کنید؟
بله / خیر
"""

            return await reply_auto(event, preview)

        # =========================
        # STEP 2: CONFIRM
        # =========================
        if step == "CONFIRM":

            if text in ["بله", "yes", "ok", "آره"]:

                name = temp.get("name")
                ai = temp.get("ai")

                if not name or not ai:
                    clear_flow(uid)
                    return await reply_auto(event, "❌ خطا در داده‌ها")

                create_character(name=name, owner_id=uid, data=ai)

                clear_flow(uid)
                set_active_character(event.chat_id, name)

                return await reply_auto(event, f"✅ کاراکتر {name} ساخته شد.")

            if text in ["خیر", "نه", "no"]:

                set_flow(uid, "WAIT_CUSTOM_DESCRIPTION", {
                    "name": temp.get("name"),
                    "chat_id": event.chat_id
                })

                return await reply_auto(event, "✍️ توضیح شخصیت را بنویس (فارسی)")

        # =========================
        # STEP 3: CUSTOM DESCRIPTION
        # =========================
        if step == "WAIT_CUSTOM_DESCRIPTION":

            desc = text.strip()

            if len(desc) < 5:
                return await reply_auto(event, "❌ توضیح خیلی کوتاه است")

            prompt = f"""
Create Telegram AI character JSON:

{desc}

Return ONLY JSON:
{{
  "name": "{temp.get('name')}",
  "personality_fa": "",
  "tone_fa": "",
  "speaking_style_fa": "",
  "rules_fa": [],
  "system_prompt": ""
}}
"""

            ai_result = await ask_ai(prompt)
            data = extract_json(ai_result)

            if not data or not validate_character(data):
            	return await reply_auto(event, "AI خروجی ناقص داد، دوباره تلاش کنید")

            data.setdefault("rules_fa", ["بدون قانون"])

            set_flow(uid, "CONFIRM_CUSTOM", {
                "name": temp.get("name"),
                "ai": data,
                "chat_id": event.chat_id
            })

            rules_text = "\n• ".join(data["rules_fa"])

            preview = f"""
📌 پیش‌نمایش شخصیت

👤 نام:
{data.get('name')}

🧠 شخصیت:
{data.get('personality_fa')}

🎭 لحن:
{data.get('tone_fa')}

🗣 سبک صحبت:
{data.get('speaking_style_fa')}

📜 قوانین:
• {rules_text}

تایید می‌کنید؟
بله / خیر
"""

            return await reply_auto(event, preview)

        # =========================
        # STEP 4: CONFIRM CUSTOM
        # =========================
        if step == "CONFIRM_CUSTOM":

            if text in ["بله", "yes", "ok", "آره"]:

                name = temp.get("name")
                ai = temp.get("ai")

                create_character(name=name, owner_id=uid, data=ai)

                clear_flow(uid)
                set_active_character(event.chat_id, name)

                return await reply_auto(event, f"✅ کاراکتر {name} ساخته شد.")

            if text in ["خیر", "نه", "no"]:

                set_flow(uid, "WAIT_CUSTOM_DESCRIPTION", {
                    "name": temp.get("name"),
                    "chat_id": event.chat_id
                })

                return await reply_auto(event, "✍️ دوباره توضیح بده")

    # =====================================================
    # APPROVE (OWNER)
    # =====================================================
    @client.on(events.NewMessage)
    async def approve_character_cmd(event):

        if not await owner_only(event):
            return

        if not (event.raw_text or "").startswith(".approve"):
            return

        name = event.raw_text.split(maxsplit=1)[1]

        approve_character(name)

        await reply_auto(event, f"✔ Approved: {name}")

    # =====================================================
    # CHARACTER CHAT
    # =====================================================
    @client.on(events.NewMessage)
    async def character_chat(event):

        text = (event.raw_text or "").strip()

        char_name = get_active_character(event.chat_id)
        char = get_character(char_name)

        if not char:
            return

        aliases = [
            char.get("name"),
            char.get("persian_name"),
            char.get("english_name")
        ]

        matched = None
        for a in aliases:
            if a and text.lower().startswith(a.lower()):
                matched = a
                break

        if not matched:
            return

        question = text[len(matched):].strip()
        if not question:
            return

        await core_ai(event, question)

    
#════════════════════════
                 

    @client.on(events.NewMessage)
    async def approve_character_cmd(event):

        if not await owner_id(event):
            return

        if not event.raw_text.startswith(".approve"):
            return

        name = event.raw_text.split(maxsplit=1)[1]

        approve_character(name)

        await edit_auto(event, f"✔ Approved: {name}")
        
        
    @client.on(events.NewMessage)
    async def character_chat(event):

        text = (event.raw_text or "").strip()

        char_name = get_active_character(event.chat_id)
        char = get_character(char_name)

        if not char:
            return

        me = await event.client.get_me()

    # Saved Messages
        if event.chat_id == me.id:
            await core_ai(event, text)
            return

        aliases = [
        char.get("name"),
        char.get("persian_name"),
        char.get("english_name")
    ]

        matched = None
    
        for alias in aliases:
            if alias and alias.lower() in text.lower():
                matched = alias
                break
        
        if not matched:
            return

        question = text.replace(matched, "").strip()

        if not question:
            return

        await core_ai(event, question)
    
    

print("self-ai loaded")