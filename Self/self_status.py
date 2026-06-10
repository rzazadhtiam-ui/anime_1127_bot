import asyncio
from telethon import events, functions
from telethon.tl.types import (
    SendMessageTypingAction,
    SendMessageRecordAudioAction,
    SendMessageRecordVideoAction,
    SendMessageGamePlayAction
)
from multi_lang import multi_lang, reply_auto, edit_auto

# فرض بر این است که این دو قبلاً در پروژه‌ات وجود دارند
# from multi_lang import multi_lang
# from edit_auto import edit_auto

class SelfStatusBot:

    def __init__(self, client):
        self.client = client
        self.me_id = None

        self.status_flags = {
            "typing": {},
            "recording_voice": {},
            "recording_video": {},
            "playing_game": {}
        }

        self.online = False
        self.auto_read = False
        self.chat_list = set()

    async def init_owner(self):
        me = await self.client.get_me()
        self.me_id = me.id

    async def add_chat(self, chat_id):
        if chat_id:
            self.chat_list.add(chat_id)

    def register_handlers(self):

        client = self.client

        # ------------------------
        # Track Chats
        # ------------------------
        @client.on(events.NewMessage(outgoing=True))
        async def track_chats(event):
            if event.chat_id:
                await self.add_chat(event.chat_id)

        # ------------------------
        # Auto Read
        # ------------------------
        @client.on(events.NewMessage(incoming=True))
        async def auto_read_handler(event):

            if not self.auto_read:
                return

            if event.sender_id == self.me_id:
                return

            if event.is_channel:
                return

            if event.message.action:
                return

            try:
                await client.send_read_acknowledge(
                    event.chat_id,
                    max_id=event.id
                )
            except Exception as e:
                print(f"[AUTO READ ERROR] {e}")

        # ==============================
        # Online / Offline
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".انلاین", ".Online"])
        async def online_handler(event):
            if not event.out:
                return

            self.online = True
            await client(functions.account.UpdateStatusRequest(offline=False))
            await edit_auto(event,"اکانت آنلاین شد.")

        @client.on(events.NewMessage)
        @multi_lang([".افلاین", ".Ofline"])
        async def offline_handler(event):
            if not event.out:
                return

            self.online = False
            await client(functions.account.UpdateStatusRequest(offline=True))
            await edit_auto(event,"اکانت آفلاین شد.")

        # ==============================
        # Auto Read Commands
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".سین روشن", ".autoread on"])
        async def autoread_on(event):
            if not event.out:
                return

            self.auto_read = True
            await edit_auto(event,"سین خودکار روشن شد.")

        @client.on(events.NewMessage)
        @multi_lang([".سین خاموش", ".autoread off"])
        async def autoread_off(event):
            if not event.out:
                return

            self.auto_read = False
            await edit_auto(event,"سین خودکار خاموش شد.")

        # ==============================
        # Typing
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".تایپ روشن", ".typing on"])
        async def typing_on(event):
            if not event.out:
                return

            self.status_flags["typing"][event.chat_id] = True
            await edit_auto(event,"تایپ روشن شد.")

        @client.on(events.NewMessage)
        @multi_lang([".تایپ خاموش", ".typing off"])
        async def typing_off(event):
            if not event.out:
                return

            self.status_flags["typing"][event.chat_id] = False
            await edit_auto(event,"تایپ خاموش شد.")

        # ==============================
        # Voice Recording
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".وس روشن", ".voice on"])
        async def voice_on(event):
            if not event.out:
                return

            self.status_flags["recording_voice"][event.chat_id] = True
            await edit_auto(event,"ویس روشن شد.")

        @client.on(events.NewMessage)
        @multi_lang([".ویس خاموش", ".voice off"])
        async def voice_off(event):
            if not event.out:
                return

            self.status_flags["recording_voice"][event.chat_id] = False
            await edit_auto(event,"ویس خاموش شد.")

        # ==============================
        # Video Recording
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".فیلم خاموش", ".video off"])
        async def video_on(event):
            if not event.out:
                return

            self.status_flags["recording_video"][event.chat_id] = True
            await edit_auto(event,"فیلم روشن شد.")

        @client.on(events.NewMessage)
        @multi_lang([".فیلم خاموش", ".video off"])
        async def video_off(event):
            if not event.out:
                return

            self.status_flags["recording_video"][event.chat_id] = False
            await edit_auto(event,"فیلم خاموش شد.")

        # ==============================
        # Game
        # ==============================

        @client.on(events.NewMessage)
        @multi_lang([".بازی روشن", ".game on"])
        async def game_on(event):
            if not event.out:
                return

            self.status_flags["playing_game"][event.chat_id] = True
            await edit_auto(event,"بازی روشن شد.")

        @client.on(events.NewMessage)
        @multi_lang([".بازی خاموش", ".game off"])
        async def game_off(event):
            if not event.out:
                return

            self.status_flags["playing_game"][event.chat_id] = False
            await edit_auto(event,"بازی خاموش شد.")

    # =========================================
    # Optimized Status Loop
    # =========================================

    async def status_loop(self):

        actions_map = {
            "typing": SendMessageTypingAction(),
            "recording_voice": SendMessageRecordAudioAction(),
            "recording_video": SendMessageRecordVideoAction(),
            "playing_game": SendMessageGamePlayAction()
        }

        while True:

            for chat_id in list(self.chat_list):

                for key, action in actions_map.items():

                    if self.status_flags[key].get(chat_id):

                        try:
                            async with self.client.action(chat_id, action):
                                await asyncio.sleep(4)
                        except Exception as e:
                            print(f"[STATUS LOOP ERROR] {e}")

            await asyncio.sleep(1)

    # =========================================
    # Keep Online
    # =========================================

    async def keep_online(self):
        while True:
            if self.online:
                try:
                    await self.client(
                        functions.account.UpdateStatusRequest(offline=False)
                    )
                except Exception as e:
                    print(f"[KEEP ONLINE ERROR] {e}")

            await asyncio.sleep(60)

    # =========================================
    # Start
    # =========================================

    async def start(self):
        await self.init_owner()
        self.register_handlers()
        asyncio.create_task(self.status_loop())
        asyncio.create_task(self.keep_online())
