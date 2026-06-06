import asyncio
from telethon import events

mirror_users = set()
mirror_targets = {}

mirror_enabled = True
OWNER_ID = 6433381392

panel_sessions = {}
last_message = {}   # NEW: ذخیره آخرین پیام پنل


def enable_mirror(state: bool):
    global mirror_enabled
    mirror_enabled = state


def add_user(user_id: int):
    mirror_users.add(user_id)


def remove_user(user_id: int):
    mirror_users.discard(user_id)


def set_target(user_id: int, client):
    mirror_targets[user_id] = client


def register_mirror(client):

    @client.on(events.NewMessage(pattern=r"^\.پنل (\d+)$"))
    async def panel_cmd(event):

        if event.sender_id != OWNER_ID:
            return await event.edit("No access")

        target_id = int(event.pattern_match.group(1))

        panel_sessions[event.sender_id] = target_id

        target_client = mirror_targets.get(event.sender_id)
        if not target_client:
            return await event.edit("Target client not set")

        # 🔥 فقط متن "پنل"
        await target_client.send_message(target_id, "پنل")

        await event.edit("Panel sent")


    # =========================
    # CLICK MIRROR (AUTO)
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

            # ذخیره آخرین پیام برای کلیک واقعی
            last_message[user_id] = msg

            # 🔥 کلیک واقعی روی همان پیام
            try:
                await msg.click(data=data)
            except:
                pass

            # حذف پیام کنترل
            try:
                await event.delete()
            except:
                pass

        except Exception as e:
            print("Mirror error:", e)
