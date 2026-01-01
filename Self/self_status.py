import asyncio
from telethon import events, functions
from telethon.tl.types import (
    SendMessageTypingAction,
    SendMessageRecordAudioAction,
    SendMessageRecordVideoAction,
    SendMessageGamePlayAction
)


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
        self.chat_list.add(chat_id)

    def register_handlers(self):

        # ثبت چت‌هایی که در آن‌ها پیام می‌دهی
        @self.client.on(events.NewMessage(outgoing=True))
        async def track_chats(event):
            await self.add_chat(event.chat_id)

        # سین خودکار (فقط پیوی و گروه – بدون کانال)
        @self.client.on(events.NewMessage(incoming=True))
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
                await self.client.send_read_acknowledge(
                    event.chat_id,
                    max_id=event.id
                )
            except Exception as e:
                print(f"[AUTO READ ERROR] {e}")

        # دستورات کنترلی
        @self.client.on(events.NewMessage(outgoing=True))
        async def command_handler(event):
            if event.sender_id != self.me_id:
                return

            text = event.raw_text.strip()

            if text == ".آنلاین":
                self.online = True
                await self.client(functions.account.UpdateStatusRequest(offline=False))
                await event.respond("اکانت آنلاین شد.")

            elif text == ".آفلاین":
                self.online = False
                await self.client(functions.account.UpdateStatusRequest(offline=True))
                await event.respond("اکانت آفلاین شد.")

            elif text == ".سین روشن":
                self.auto_read = True
                await event.respond("سین خودکار روشن شد.")

            elif text == ".سین خاموش":
                self.auto_read = False
                await event.respond("سین خودکار خاموش شد.")

            elif text == ".تایپ روشن":
                self.status_flags["typing"][event.chat_id] = True
                await event.respond("تایپ روشن شد.")

            elif text == ".تایپ خاموش":
                self.status_flags["typing"][event.chat_id] = False
                await event.respond("تایپ خاموش شد.")

            elif text == ".ویس روشن":
                self.status_flags["recording_voice"][event.chat_id] = True
                await event.respond("ویس روشن شد.")

            elif text == ".ویس خاموش":
                self.status_flags["recording_voice"][event.chat_id] = False
                await event.respond("ویس خاموش شد.")

            elif text == ".فیلم روشن":
                self.status_flags["recording_video"][event.chat_id] = True
                await event.respond("فیلم روشن شد.")

            elif text == ".فیلم خاموش":
                self.status_flags["recording_video"][event.chat_id] = False
                await event.respond("فیلم خاموش شد.")

            elif text == ".بازی روشن":
                self.status_flags["playing_game"][event.chat_id] = True
                await event.respond("بازی روشن شد.")

            elif text == ".بازی خاموش":
                self.status_flags["playing_game"][event.chat_id] = False
                await event.respond("بازی خاموش شد.")

            elif text == ".تایپ همگانی فعال":
                for c in self.chat_list:
                    self.status_flags["typing"][c] = True
                await event.respond("تایپ همگانی فعال شد.")

            elif text == ".تایپ همگانی غیرفعال":
                for c in self.chat_list:
                    self.status_flags["typing"][c] = False
                await event.respond("تایپ همگانی غیرفعال شد.")

    async def status_loop(self):
        while True:
            for chat_id in list(self.chat_list):
                try:
                    if self.status_flags["typing"].get(chat_id):
                        async with self.client.action(chat_id, SendMessageTypingAction()):
                            await asyncio.sleep(25)

                    if self.status_flags["recording_voice"].get(chat_id):
                        async with self.client.action(chat_id, SendMessageRecordAudioAction()):
                            await asyncio.sleep(25)

                    if self.status_flags["recording_video"].get(chat_id):
                        async with self.client.action(chat_id, SendMessageRecordVideoAction()):
                            await asyncio.sleep(25)

                    if self.status_flags["playing_game"].get(chat_id):
                        async with self.client.action(chat_id, SendMessageGamePlayAction()):
                            await asyncio.sleep(25)

                except Exception as e:
                    print(f"[STATUS LOOP ERROR] {e}")

            await asyncio.sleep(0.1)

    async def keep_online(self):
        while True:
            if self.online:
                try:
                    await self.client(functions.account.UpdateStatusRequest(offline=False))
                except Exception as e:
                    print(f"[KEEP ONLINE ERROR] {e}")
            await asyncio.sleep(60)

    async def start(self):
        await self.init_owner()
        self.register_handlers()
        asyncio.create_task(self.status_loop())
        asyncio.create_task(self.keep_online())