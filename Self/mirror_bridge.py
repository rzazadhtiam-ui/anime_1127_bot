import asyncio
from telethon import events

# =========================
# STATE (RAM)
# =========================

mirror_users = set()
mirror_targets = {}

mirror_enabled = True
OWNER_ID = 6433381392

# =========================
# NEW: BRIDGE LAYER (BOT ↔ SELF BOT)
# =========================

command_queue = []  # Bot API → Self bot

panel_sessions = {}  # user_id -> panel state
button_map = {}      # user_id -> {text: callback_data}


# =========================
# CORE FUNCTIONS
# =========================

def enable_mirror(state: bool):
    global mirror_enabled
    mirror_enabled = state


def add_user(user_id: int):
    mirror_users.add(user_id)


def remove_user(user_id: int):
    mirror_users.discard(user_id)


def set_target(user_id: int, client):
    mirror_targets[user_id] = client


# =========================
# BRIDGE FUNCTIONS
# =========================

def push_command(cmd: dict):
    command_queue.append(cmd)


def pop_command():
    if command_queue:
        return command_queue.pop(0)
    return None


# =========================
# MIRROR ENGINE (CALLBACK RELAY)
# =========================

def register_mirror(client):

    @client.on(events.CallbackQuery)
    async def callback_handler(event):

        if not mirror_enabled:
            return

        user_id = event.sender_id

        if user_id not in mirror_users:
            return

        target_client = mirror_targets.get(user_id)
        if not target_client:
            return

        try:
            data = event.data.decode() if event.data else None
            chat_id = event.chat_id

            # دریافت پیام اصلی
            msg = await event.get_message()
            if not msg:
                return

            # =========================
            # NEW: PANEL SYNC MODE
            # =========================

            panel = panel_sessions.get(user_id)

            if panel:
                # اگر دکمه در map باشد
                btn_map = button_map.get(user_id, {})

                callback_data = btn_map.get(data, data)

                # ارسال به سیستم هدف (Relay)
                push_command({
                    "type": "callback",
                    "target": user_id,
                    "chat_id": chat_id,
                    "data": callback_data
                })

            # اجرای محلی click
            try:
                await msg.click(data=data)
            except:
                push_command({
                    "type": "fallback",
                    "chat_id": chat_id,
                    "data": data
                })

            # حذف پیام کنترل
            try:
                await event.delete()
            except:
                pass

        except Exception as e:
            print("Mirror error:", e)


# =========================
# COMMANDS
# =========================

def register_commands(client):

    # =========================
    # PANEL INIT (NEW)
    # =========================
    @client.on(events.NewMessage(pattern=r"^\.پنل (\d+)$"))
    async def panel_cmd(event):

        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        target_id = int(event.pattern_match.group(1))

        panel_sessions[event.sender_id] = {
            "target": target_id,
            "active": True
        }

        await event.edit("📟 Panel activated & linked")

    # =========================
    # ADD BUTTON MAP
    # =========================
    @client.on(events.NewMessage(pattern=r"^\.دکمه (.+) (.+)$"))
    async def add_button(event):

        if event.sender_id != OWNER_ID:
            return

        text = event.pattern_match.group(1)
        callback = event.pattern_match.group(2)

        if event.sender_id not in button_map:
            button_map[event.sender_id] = {}

        button_map[event.sender_id][text] = callback

        await event.edit(f"✔ Button mapped:\n{text} → {callback}")

    # =========================
    # MIRROR CONTROL
    # =========================

    @client.on(events.NewMessage(pattern=r"^\.افزودن کاربر (\d+)$"))
    async def add_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        user_id = int(event.pattern_match.group(1))
        add_user(user_id)

        await event.edit(f"✔ User added:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.حذف کاربر (\d+)$"))
    async def remove_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        user_id = int(event.pattern_match.group(1))
        remove_user(user_id)

        await event.edit(f"✖ User removed:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.تعیین هدف (\d+)$"))
    async def target_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        user_id = int(event.pattern_match.group(1))
        set_target(user_id, client)

        await event.edit(f"🎯 Target set:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.میرور روشن$"))
    async def on_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        enable_mirror(True)
        await event.edit("🟢 Mirror ON")


    @client.on(events.NewMessage(pattern=r"^\.میرور خاموش$"))
    async def off_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        enable_mirror(False)
        await event.edit("🔴 Mirror OFF")


# =========================
# BRIDGE LOOP (IMPORTANT)
# =========================

async def bridge_worker():
    while True:
        cmd = pop_command()

        if cmd:
            print("BRIDGE:", cmd)

        await asyncio.sleep(0.2)
