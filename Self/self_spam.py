# ================================================================
# self_spam_mongo.py — نسخه کامل با MongoDB و اسپم همیشه اجرا
# ================================================================

import asyncio
import random
from typing import Dict

from telethon import TelegramClient, events, functions
from pymongo import MongoClient

# ================================================================
# MONGO SETUP
# ================================================================

MONGO_URI = "mongodb://jinx:titi_jinx@ac-yjpvg6o-shard-00-00.35gzto0.mongodb.net:27017,ac-yjpvg6o-shard-00-01.35gzto0.mongodb.net:27017,ac-yjpvg6o-shard-00-02.35gzto0.mongodb.net:27017/?replicaSet=atlas-fzmhnh-shard-0&ssl=true&authSource=admin"
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["self_spam_db"]
collection = db["owners"]

# ================================================================
# RUNTIME REGISTERS (per owner / per chat)
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
    if collection.find_one({"_id": owner_id}) is None:
        collection.insert_one({"_id": owner_id, "muted": {}, "blocked": {}})
    if owner_id not in active_spams:
        active_spams[owner_id] = {}
    if owner_id not in spam_events:
        spam_events[owner_id] = {}

# ================================================================
# USER HELPERS
# ================================================================

async def get_name(client, uid):
    try:
        ent = await client.get_entity(uid)
        name = f"{ent.first_name or ''} {ent.last_name or ''}".strip()
        return name if name else str(uid)
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
    if target.startswith("@"):
        try:
            ent = await client.get_entity(target)
            return ent.id, await get_name(client, ent.id)
        except:
            return None, None

    if target.isdigit():
        uid = int(target)
        return uid, await get_name(client, uid)

    return None, None

# ================================================================
# SPAM ENGINE
# ================================================================

async def send_spam(client, event, owner_id, spam_type, count, msg_text=None, reply_mode=False,
                    min_delay_override=None, max_delay_override=None, max_errors=7):
    rep = await event.get_reply_message() if event.is_reply else event.message
    chat_id = rep.chat_id
    reply_to = rep.id if (reply_mode and event.is_reply) else None
    txt = (msg_text or rep.message or "سلام").strip()

    sp = spam_type.lower()
    if sp == "سریع":
        dmin, dmax = 0.03, 0.06
    elif sp == "آرام":
        dmin, dmax = 1.2, 2.0
    elif sp == "هایپر":
        dmin, dmax = 0.008, 0.015
    else:
        dmin, dmax = 1.6, 3.0

    if min_delay_override is not None:
        dmin = float(min_delay_override)
    if max_delay_override is not None:
        dmax = float(max_delay_override)
    if dmax < dmin:
        dmax = dmin

    consec = 0
    task_id = id(asyncio.current_task())
    stop_event = spam_events[owner_id][chat_id][task_id]

    for i in range(count):
        if stop_event.is_set():
            break
        try:
            await client.send_message(chat_id, txt, reply_to=reply_to)
            consec = 0
        except:
            consec += 1
            if consec >= max_errors:
                break
        if i != count - 1:
            await asyncio.sleep(random.uniform(dmin, dmax))


async def start_spam(client, event, owner_id, tp, cnt, txt=None, reply_mode=False,
                     min_delay_override=None, max_delay_override=None):
    rep = await event.get_reply_message() if event.is_reply else event.message
    chat_id = rep.chat_id

    if chat_id not in active_spams[owner_id]:
        active_spams[owner_id][chat_id] = {}
        spam_events[owner_id][chat_id] = {}

    stop_event = asyncio.Event()
    task = asyncio.create_task(send_spam(client, event, owner_id, tp, cnt, txt, reply_mode,
                                         min_delay_override, max_delay_override))
    tid = id(task)
    active_spams[owner_id][chat_id][tid] = task
    spam_events[owner_id][chat_id][tid] = stop_event
    return task

async def stop_chat_spams(owner_id, chat_id):
    if owner_id not in active_spams or chat_id not in active_spams[owner_id]:
        return
    for tid, task in list(active_spams[owner_id][chat_id].items()):
        ev = spam_events[owner_id][chat_id].get(tid)
        if ev: ev.set()
        try: task.cancel()
        except: pass
    active_spams[owner_id][chat_id].clear()
    spam_events[owner_id][chat_id].clear()

# ================================================================
# MUTE / BLOCK — MONGO
# ================================================================

def mute_user(owner_id, uid, name):
    collection.update_one({"_id": owner_id}, {"$set": {f"muted.{uid}": name}}, upsert=True)

def unmute_user(owner_id, uid):
    collection.update_one({"_id": owner_id}, {"$unset": {f"muted.{uid}": ""}})

async def block_user(client, owner_id, uid, name):
    try:
        ent = await client.get_input_entity(uid)
        await client(functions.contacts.BlockRequest(id=ent))
        collection.update_one({"_id": owner_id}, {"$set": {f"blocked.{uid}": name}}, upsert=True)
        return True
    except:
        return False

async def unblock_user(client, owner_id, uid):
    try:
        ent = await client.get_input_entity(uid)
        await client(functions.contacts.UnblockRequest(id=ent))
        collection.update_one({"_id": owner_id}, {"$unset": {f"blocked.{uid}": ""}})
        return True
    except:
        return False

def list_muted(owner_id):
    doc = collection.find_one({"_id": owner_id})
    return doc.get("muted", {}) if doc else {}

def list_blocked(owner_id):
    doc = collection.find_one({"_id": owner_id})
    return doc.get("blocked", {}) if doc else {}

# ================================================================
# MAIN HANDLERS
# ================================================================

def register_handlers(client, owner_check_fn=None):
    me_id = None
    async def get_me_id():
        nonlocal me_id
        if me_id is None:
            me = await client.get_me()
            me_id = me.id
        return me_id

    @client.on(events.NewMessage(incoming=True))
    async def auto_delete(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid = event.sender_id
        me = await get_me_id()
        if str(uid) in list_muted(owner_id):
            try: 
                if uid != me: await event.delete()
            except:
                try:
                    if uid != me: await client.delete_messages(event.chat_id, [event.id])
                except: pass

    @client.on(events.NewMessage(pattern=r"\.اسپم\s+(\w+)\s+(\d+)\s*(.*)"))
    async def spam_cmd(event):
        if owner_check_fn and not owner_check_fn(event.sender_id): return
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        tp = event.pattern_match.group(1)
        cnt = int(event.pattern_match.group(2))
        txt = event.pattern_match.group(3).strip()
        if not txt and event.is_reply: txt = (await event.get_reply_message()).message or ""
        if not txt: txt = "سلام"
        await start_spam(event.client, event, owner_id, tp, cnt, txt)
        await event.edit(f"⚡ اسپم {tp} در حال انجام است (تعداد: {cnt})")

    @client.on(events.NewMessage(pattern=r"\.توقف اسپم$"))
    async def stop_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        await stop_chat_spams(owner_id, event.chat_id)
        await event.edit("اسپم متوقف شد.")

    # MUTE / UNMUTE
    @client.on(events.NewMessage(pattern=r"\.سکوت$"))
    async def mute_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid, name = await resolve_target(client, event)
        if not uid:
            uid = await get_me_id()
            name = await get_name(client, uid)
        mute_user(owner_id, uid, name)
        await event.edit(f"کاربر {name} ({uid}) سکوت شد.")

    @client.on(events.NewMessage(pattern=r"\.حذف سکوت$"))
    async def unmute_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid, name = await resolve_target(client, event)
        if not uid:
            uid = await get_me_id()
            name = await get_name(client, uid)
        unmute_user(owner_id, uid)
        await event.edit(f"{name} ({uid}) از سکوت خارج شد.")

    # BLOCK / UNBLOCK
    @client.on(events.NewMessage(pattern=r"\.بلاک"))
    async def block_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid, name = await resolve_target(client, event)
        if not uid: return await event.edit("کاربر پیدا نشد.")
        ok = await block_user(event.client, owner_id, uid, name)
        if ok: await event.edit(f"{name} ({uid}) بلاک شد.")
        else: await event.edit("❌ خطا در بلاک کردن.")

    @client.on(events.NewMessage(pattern=r"\.انبلاک"))
    async def unblock_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        uid, name = await resolve_target(client, event)
        if not uid: return await event.edit("کاربر پیدا نشد.")
        ok = await unblock_user(event.client, owner_id, uid)
        if ok: await event.edit(f"{name} ({uid}) از بلاک خارج شد.")
        else: await event.edit("❌ خطا در آن‌بلاک کردن.")

    # LIST
    @client.on(events.NewMessage(pattern=r"\.لیست سکوت$"))
    async def list_mute_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        m = list_muted(owner_id)
        if not m: return await event.edit("هیچ کاربری در سکوت نیست.")
        txt = "👤 لیست سکوت :\n\n" + "\n".join(f"{n} : {u}" for u, n in m.items())
        await event.edit(txt)

    @client.on(events.NewMessage(pattern=r"\.لیست بلاک$"))
    async def list_block_cmd(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        b = list_blocked(owner_id)
        if not b: return await event.edit("هیچ کاربری بلاک نیست.")
        txt = "⛔ لیست بلاک:\n\n" + "\n".join(f"{n} : {u}" for u, n in b.items())
        await event.edit(txt)

    # CLEAR ALL
    @client.on(events.NewMessage(pattern=r"\.پاکسازی سکوت$"))
    async def clear_all_mute(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        for uid in list(list_muted(owner_id).keys()):
            unmute_user(owner_id, int(uid))
        await event.edit("تمام کاربران از سکوت خارج شدند ✔️")

    @client.on(events.NewMessage(pattern=r"\.پاکسازی بلاک$"))
    async def clear_all_block(event):
        owner_id = await get_owner_id(client)
        ensure_owner(owner_id)
        success_count = 0
        for uid in list(list_blocked(owner_id).keys()):
            ok = await unblock_user(event.client, owner_id, int(uid))
            if ok: success_count += 1
        await event.edit(f"{success_count} کاربر از بلاک خارج شدند ✔️")
