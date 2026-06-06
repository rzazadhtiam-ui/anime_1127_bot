import asyncio
from telethon import events

# =========================
# STATE (RAM ONLY)
# =========================
mirror_users = set()
mirror_targets = {}
mirror_enabled = True

OWNER_ID = 6433381392


# =========================
# CORE FUNCTIONS (ENGLISH ONLY)
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
            chat_id = event.chat_id
            msg_id = event.message_id
            data = event.data.decode() if event.data else None

            msg = await client.get_messages(chat_id, ids=msg_id)
            if not msg:
                return

            try:
                await msg.click(data=data)
            except:
                await target_client.send_message(
                    chat_id,
                    f"Mirror Trigger: {data}"
                )

        except Exception as e:
            print("Mirror error:", e)


# =========================
# COMMANDS (PERSIAN ONLY)
# =========================
def register_commands(client):

    @client.on(events.NewMessage(pattern=r"^\.افزودن کاربر (\d+)$"))
    async def add_cmd(event):
        if event.sender_id != OWNER_ID:
            return event.edit("هه دست رسی نداری ")

        user_id = int(event.pattern_match.group(1))
        add_user(user_id)

        await event.edit(f"✔ کاربر اضافه شد به لیست میرور:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.حذف کاربر (\d+)$"))
    async def remove_cmd(event):
        if event.sender_id != OWNER_ID:
            return event.edit("دست رسی نداری بد بخت")

        user_id = int(event.pattern_match.group(1))
        remove_user(user_id)

        await event.edit(f"✖ کاربر حذف شد:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.تعیین هدف (\d+)$"))
    async def target_cmd(event):
        if event.sender_id != OWNER_ID:
            return event.edit("تو مه دست رسی نداری انقد زور نزن")

        user_id = int(event.pattern_match.group(1))
        set_target(user_id, client)

        await event.edit(f"🎯 هدف تنظیم شد برای:\n{user_id}")


    @client.on(events.NewMessage(pattern=r"^\.میرور روشن$"))
    async def on_cmd(event):
        if event.sender_id != OWNER_ID:
            return event.edit("شما دست رسی نداری ")

        enable_mirror(True)
        await event.edit("🟢 میرور روشن شد")


    @client.on(events.NewMessage(pattern=r"^\.میرور خاموش$"))
    async def off_cmd(event):
        if event.sender_id != OWNER_ID:
            return event.edit("شما دست رسی نداری")

        enable_mirror(False)
        await event.edit("🔴 میرور خاموش شد")
