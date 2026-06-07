import asyncio
from telethon import events

OWNER_ID = 6433381392

mirror_enabled = True
mirror_users = set()

# session B (target userbot)
mirror_clients = {}

# pending actions
pending_panels = {}  # user_id -> (client, message)

# =========================
# CORE
# =========================
def add_user(user_id: int):
    mirror_users.add(user_id)

def set_client(user_id: int, client):
    mirror_clients[user_id] = client

def enable(state: bool):
    global mirror_enabled
    mirror_enabled = state


# =========================
# STEP 1: A COMMAND -> SEND PANEL VIA B
# =========================
def register_controller(client):

    @client.on(events.NewMessage(pattern=r"^\.پل (\d+)$"))
    async def send_panel(event):

        if event.sender_id != OWNER_ID:
            return

        target_id = int(event.pattern_match.group(1))

        target_client = mirror_clients.get(target_id)
        if not target_client:
            return await event.reply("Session not found")

        # B sends panel to owner PV
        msg = await target_client.send_message(OWNER_ID, "پنل")

        # save state for later click
        pending_panels[OWNER_ID] = (target_client, msg)

        await event.reply("Panel opened")


    # =========================
    # STEP 2: CLICK COMMAND FROM A
    # =========================
    @client.on(events.NewMessage(pattern=r"^\.کلیک (\d+)$"))
    async def click_btn(event):

        if event.sender_id != OWNER_ID:
            return

        if OWNER_ID not in pending_panels:
            return await event.reply("No active panel")

        client_b, msg = pending_panels[OWNER_ID]

        try:
            await msg.click(int(event.pattern_match.group(1)))
            await event.reply("Clicked")
        except Exception as e:
            await event.reply(f"Failed: {e}")


# =========================
# STEP 3: AUTO PANEL DETECTION (OPTIONAL)
# =========================
def register_auto(client):

    @client.on(events.NewMessage(incoming=True))
    async def detect_panel(event):

        if event.sender_id not in mirror_users:
            return

        if event.text == "پنل":
            pending_panels[event.sender_id] = (client, event.message)
