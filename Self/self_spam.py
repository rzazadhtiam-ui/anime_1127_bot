# ================================================================
# self_spam.py — نسخه نهایی پایدار (per-owner + per-chat + SQLite)
# ================================================================

import asyncio
import json
import os
import random
from typing import Dict

from telethon import events, functions
from self_storage import Storage

# ================================================================
# FILES / STORAGE
# ================================================================

MEMORY_FILE = "self_spam_memory.json"
storage = Storage()

# ================================================================
# LOAD MEMORY (CACHE ONLY)
# ================================================================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(MEMORY, f, indent=2, ensure_ascii=False)
    except:
        pass

MEMORY: Dict[str, Dict] = load_memory()

# ================================================================
# RUNTIME REGISTERS
# ================================================================

active_spams: Dict[str, Dict[int, Dict[int, asyncio.Task]]] = {}
spam_events: Dict[str, Dict[int, Dict[int, asyncio.Event]]] = {}

# ================================================================
# OWNER UTILS
# ================================================================

async def get_owner_id(client) -> str:
    me = await client.get_me()
    return str(me.id)

def ensure_owner(owner_id: str):
    MEMORY.setdefault(owner_id, {"muted": {}, "blocked": {}})
    active_spams.setdefault(owner_id, {})
    spam_events.setdefault(owner_id, {})
    save_memory()

# ================================================================
# USER HELPERS
# ================================================================

async def get_name(client, uid):
    try:
        ent = await client.get_entity(uid)
        return f"{ent.first_name or ''} {ent.last_name or ''}".strip() or str(uid)
    except:
        return str(uid)

async def resolve_target(client, event):
    if event.is_reply:
        msg = await event.get_reply_message()
        return msg.sender_id, await get_name(client, msg.sender_id)

    parts = event.raw_text.split(" ", 1)
    if len(parts) < 2:
        return None, None

    target = parts[1].strip()
    try:
        ent = await client.get_entity(target)
        return ent.id, await get_name(client, ent.id)
    except:
        return None, None

# ================================================================
# SPAM ENGINE
# ================================================================

async def send_spam(
    client, event, owner_id, spam_type, count, text,
    min_delay=None, max_delay=None
):
    chat_id = event.chat_id

    dmin, dmax = 1.5, 3.0
    if spam_type == "سریع":
        dmin, dmax = 0.03, 0.06
    elif spam_type == "آرام":
        dmin, dmax = 1.2, 2.0
    elif spam_type == "هایپر":
        dmin, dmax = 0.008, 0.015

    if min_delay: dmin = float(min_delay)
    if max_delay: dmax = float(max_delay)
    if dmax < dmin: dmax = dmin

    task_id = id(asyncio.current_task())
    stop_event = spam_events[owner_id][chat_id][task_id]

    for _ in range(count):
        if stop_event.is_set():
            break
        try:
            await client.send_message(chat_id, text)
        except:
            break
        await asyncio.sleep(random.uniform(dmin, dmax))

async def start_spam(client, event, owner_id, tp, cnt, txt):
    chat_id = event.chat_id

    active_spams[owner_id].setdefault(chat_id, {})
    spam_events[owner_id].setdefault(chat_id, {})

    stop_event = asyncio.Event()
    task = asyncio.create_task(send_spam(client, event, owner_id, tp, cnt, txt))
    tid = id(task)

    active_spams[owner_id][chat_id][tid] = task
    spam_events[owner_id][chat_id][tid] = stop_event

async def stop_chat_spams(owner_id, chat_id):
    for tid, task in list(active_spams.get(owner_id, {}).get(chat_id, {}).items()):
        spam_events[owner_id][chat_id][tid].set()
        task.cancel()
    active_spams.get(owner_id, {}).pop(chat_id, None)
    spam_events.get(owner_id, {}).pop(chat_id, None)

# ================================================================
# MUTE / BLOCK (SQLite + Cache)
# ================================================================

def mute_user(owner_id, uid, name):
    storage.set_user_key(uid, "silence", "is_silenced", True)
    storage.set_user_key(uid, "silence", "reason", f"سکوت شد ({name})")
    MEMORY[owner_id]["muted"][str(uid)] = name
    save_memory()

def unmute_user(owner_id, uid):
    storage.set_user_key(uid, "silence", "is_silenced", False)
    storage.set_user_key(uid, "silence", "reason", "")
    MEMORY[owner_id]["muted"].pop(str(uid), None)
    save_memory()

async def block_user(client, owner_id, uid, name):
    try:
        ent = await client.get_input_entity(uid)
        await client(functions.contacts.BlockRequest(ent))
        storage.set_user_key(uid, "block", "is_blocked", True)
        MEMORY[owner_id]["blocked"][str(uid)] = name
        save_memory()
        return True
    except:
        return False

async def unblock_user(client, owner_id, uid):
    try:
        ent = await client.get_input_entity(uid)
        await client(functions.contacts.UnblockRequest(ent))
        storage.set_user_key(uid, "block", "is_blocked", False)
        MEMORY[owner_id]["blocked"].pop(str(uid), None)
        save_memory()
        return True
    except:
        return False

# ================================================================
# MAIN HANDLERS
# ================================================================

def register_handlers(client, owner_check_fn=None):

    @client.on(events.NewMessage(incoming=True))
    async def auto_delete(event):
        if storage.get_user_key(event.sender_id, "silence", "is_silenced"):
            try:
                await event.delete()
            except:
                pass

    @client.on(events.NewMessage(pattern=r"\.اسپم\s+(\w+)\s+(\d+)\s*(.*)"))
    async def spam_cmd(event):
        if owner_check_fn and not owner_check_fn(event.sender_id):
            return
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)

        tp = event.pattern_match.group(1)
        cnt = int(event.pattern_match.group(2))
        txt = event.pattern_match.group(3) or "سلام"

        await start_spam(client, event, owner_id, tp, cnt, txt)
        await event.edit("⚡ اسپم شروع شد")

    @client.on(events.NewMessage(pattern=r"\.توقف اسپم$"))
    async def stop_cmd(event):
        owner_id = await get_owner_id(client)
        await stop_chat_spams(owner_id, event.chat_id)
        await event.edit("⛔ اسپم متوقف شد")

    @client.on(events.NewMessage(pattern=r"\.سکوت$"))
    async def mute_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid, name = await resolve_target(client, event)
        mute_user(owner_id, uid, name)
        await event.edit(f"{name} سکوت شد")

    @client.on(events.NewMessage(pattern=r"\.حذف سکوت$"))
    async def unmute_cmd(event):
        owner_id = await get_owner_id(client)
        uid, name = await resolve_target(client, event)
        unmute_user(owner_id, uid)
        await event.edit(f"{name} آزاد شد")

    @client.on(events.NewMessage(pattern=r"\.بلاک$"))
    async def block_cmd(event):
        owner_id = await get_owner_id(client)
        uid, name = await resolve_target(client, event)
        if await block_user(client, owner_id, uid, name):
            await event.edit("⛔ بلاک شد")

    @client.on(events.NewMessage(pattern=r"\.انبلاک$"))
    async def unblock_cmd(event):
        owner_id = await get_owner_id(client)
        uid, _ = await resolve_target(client, event)
        if await unblock_user(client, owner_id, uid):
            await event.edit("✅ آنبلاک شد")