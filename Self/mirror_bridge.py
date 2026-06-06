import asyncio
from telethon import events

# =========================
# STATE
# =========================

mirror_users = set()
mirror_targets = {}

mirror_enabled = True
OWNER_ID = 6433381392

panel_sessions = {}  # owner -> target
last_msg_cache = {}  # برای click بهتر


# =========================
# CORE
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
# MIRROR ENGINE
# =========================

def register_mirror(client):

    # =========================
    # PANEL COMMAND
    # =========================
    @client.on(events.NewMessage(pattern=r"^\.پنل (\d+)$"))
    async def panel_cmd(event):

        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        target_id = int(event.pattern_match.group(1))

        panel_sessions[event.sender_id] = target_id

        target_client = mirror_targets.get(event.sender_id)
        if not target_client:
            return await event.edit("Target client not set")

        # فقط کلمه "پنل"
        await target_client.send_message(target_id, "پنل")

        await event.edit("📟 Panel sent")

    # =========================
    # CALLBACK MIRROR
    # =========================
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
            data = event.data.decode()

            msg = await event.get_message()
            if not msg:
                return

            last_msg_cache[user_id] = msg

            # 🔥 اجرای کلیک واقعی روی همان پیام
            try:
                await msg.click(data=data)
            except:
                # fallback
                await target_client.send_message(
                    event.chat_id,
                    f"CLICK:{data}"
                )

            # حذف پیام کنترل خودت
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

    @client.on(events.NewMessage(pattern=r"^\.افزودن کاربر (\d+)$"))
    async def add_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        add_user(int(event.pattern_match.group(1)))
        await event.edit("User added")

    @client.on(events.NewMessage(pattern=r"^\.حذف کاربر (\d+)$"))
    async def remove_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        remove_user(int(event.pattern_match.group(1)))
        await event.edit("User removed")

    @client.on(events.NewMessage(pattern=r"^\.تعیین هدف (\d+)$"))
    async def target_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        set_target(event.sender_id, client)
        await event.edit("Target set")

    @client.on(events.NewMessage(pattern=r"^\.میرور روشن$"))
    async def on_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        enable_mirror(True)
        await event.edit("Mirror ON")

    @client.on(events.NewMessage(pattern=r"^\.میرور خاموش$"))
    async def off_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        enable_mirror(False)
        await event.edit("Mirror OFF")


# =========================
# OPTIONAL LOOP (FOR EXTENSIONS)
# =========================

async def bridge_worker():
    while True:
        await asyncio.sleep(0.2)
