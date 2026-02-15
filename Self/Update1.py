from telethon import events
import asyncio

INLINE_BOT = "anime_1127_bot"
pm_locked = False

def register_update1(client):

    # =========================
    # سرچ اینلاین
    # =========================
    @client.on(events.NewMessage(pattern=r"\.سرچ (.+)"))
    async def anime_search(event):
        if not event.out:
            return
        query = event.pattern_match.group(1)
        try:
            results = await client.inline_query(INLINE_BOT, query)
            if not results:
                await event.reply("❌ نتیجه‌ای پیدا نشد")
                return
            await event.reply(f"🔍 {len(results)} نتیجه پیدا شد")
            for res in results[:3]:
                await res.click(event.chat_id)
                await asyncio.sleep(1)
        except Exception as e:
            await event.reply(f"⚠️ خطا در سرچ: {e}")

    # =========================
    # قفل پیوی
    # =========================
    @client.on(events.NewMessage(pattern=r"\.پیوی قفل"))
    async def lock_pm(event):
        global pm_locked
        if not event.out:
            return
        pm_locked = True
        await event.reply("🔒 پیوی شما قفل شد")

    # =========================
    # باز کردن پیوی
    # =========================
    @client.on(events.NewMessage(pattern=r"\.پیوی باز"))
    async def unlock_pm(event):
        global pm_locked
        if not event.out:
            return
        pm_locked = False
        await event.reply("🔓 پیوی شما باز شد")

    # =========================
    # گارد پیوی
    # =========================
    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def pm_guard(event):
        if not pm_locked:
            return
        if event.out:
            return
        try:
            await event.delete()
        except:
            pass

    # =========================
    # دستور آهنگ
    # =========================
    @client.on(events.NewMessage(pattern=r"\.آهنگ (.+)"))
    async def music_search(event):
        if not event.out:
            return
        query = event.pattern_match.group(1)
        try:
            results = await client.inline_query("Anoser_bot", query)
            if not results:
                await event.reply("❌ آهنگی پیدا نشد")
                return
            await event.reply("🎵 آهنگ پیدا شد")
            await results[0].click(event.chat_id)
        except Exception as e:
            await event.reply(f"⚠️ خطا در جستجوی آهنگ: {e}")

    # =========================
    # دستور بازی
    # =========================
    @client.on(events.NewMessage(pattern=r"\.بازی (.+)"))
    async def game_search(event):
        if not event.out:
            return
        query = event.pattern_match.group(1).strip().lower()
        try:
            results = await client.inline_query("bodobazibot", query)
            if not results:
                await event.reply("❌ بازی پیدا نشد")
                return
            matched_game = None
            for res in results:
                if res.title and res.title.strip().lower() == query:
                    matched_game = res
                    break
            if not matched_game:
                await event.reply("❌ بازی با این نام دقیق پیدا نشد")
                return
            await matched_game.click(event.chat_id)
        except Exception as e:
            await event.reply(f"⚠️ خطا در جستجوی بازی: {e}")

    # =========================
    # لیست بازی ها
    # =========================
    @client.on(events.NewMessage(pattern=r"\.لیست بازی"))
    async def game_list(event):
        if not event.out:
            return
        try:
            results = await client.inline_query("bodobazibot", "")
            if not results:
                await event.reply("❌ هیچ بازی‌ای پیدا نشد")
                return
            games = []
            for res in results:
                name = res.title or res.description
                if name:
                    games.append(name)
            if not games:
                await event.reply("❌ نام بازی‌ها پیدا نشد")
                return
            text = "🎮 لیست بازی‌ها:\n\n"
            for i, game in enumerate(games, start=1):
                text += f"بازی {i}: {game}\n"
            await event.reply(text)
        except Exception as e:
            await event.reply(f"⚠️ خطا در گرفتن لیست بازی: {e}")

    # =========================
    # دستور راهنما اینلاین
    # =========================
    @client.on(events.NewMessage(pattern=r"\.راهنما"))
    async def help_inline(event):
        sender = await event.get_sender()
        me = await client.get_me()
        if sender.id != me.id:
            return
        try:
            results = await client.inline_query("self_nix_bot", "پنل سلف")
            if not results:
                return await event.edit("❌ نتیجه‌ای پیدا نشد")
            await results[0].click(event.chat_id)
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ خطا:\n{e}")