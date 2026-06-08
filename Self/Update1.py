from telethon import events
import asyncio
from multi_lang import multi_lang, reply_auto

INLINE_BOT = "anime_1127_bot"
pm_locked = False


def register_update1(client):

    # =========================
    # سرچ اینلاین
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".سرچ ", ".search"])
    async def anime_search(event):

        query = event.ml_args

        try:
            results = await client.inline_query(INLINE_BOT, query)

            if not results:
                return await reply_auto(event, "**❌ نتیجه‌ای پیدا نشد**")

            await reply_auto(event, f"**🔍 {len(results)} نتیجه پیدا شد**")

            for res in results[:3]:
                await res.click(event.chat_id)
                await asyncio.sleep(1)

        except Exception as e:
            await reply_auto(event, f"**⚠️ خطا در سرچ: {e}**")

    # =========================
    # قفل پیوی
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".پیوی قفل", ".Pm lock", ".Pv lock"])
    async def lock_pm(event):

        global pm_locked
        pm_locked = True

        await reply_auto(event, "**🔒 پیوی شما قفل شد**")

    # =========================
    # باز کردن پیوی
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".پیوی باز", ".Pm unlock"])
    async def unlock_pm(event):

        global pm_locked
        pm_locked = False

        await reply_auto(event, "**🔓 پیوی شما باز شد**")

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
    @client.on(events.NewMessage)
    @multi_lang([".آهنگ ", ".Music "])
    async def music_search(event):

        query = event.ml_args

        try:
            results = await client.inline_query("Anoser_bot", query)

            if not results:
                return await reply_auto(event, "**❌ آهنگی پیدا نشد**")

            await reply_auto(event, "**🎵 آهنگ پیدا شد**")
            await results[0].click(event.chat_id)

        except Exception as e:
            await reply_auto(event, f"**⚠️ خطا در جستجوی آهنگ: {e}**")

    # =========================
    # دستور بازی
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".بازی ", ".Game "])
    async def game_search(event):

        query = event.ml_args.strip().lower()

        try:
            results = await client.inline_query("bodobazibot", query)

            if not results:
                return await reply_auto(event, "**❌ بازی پیدا نشد**")

            matched_game = None

            for res in results:
                if res.title and res.title.strip().lower() == query:
                    matched_game = res
                    break

            if not matched_game:
                return await reply_auto(event, "**❌ بازی با این نام دقیق پیدا نشد**")

            await matched_game.click(event.chat_id)

        except Exception as e:
            await reply_auto(event, f"**⚠️ خطا در جستجوی بازی: {e}**")

    # =========================
    # لیست بازی ها
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".لیست بازی", ".Game list"])
    async def game_list(event):

        try:
            results = await client.inline_query("bodobazibot", "")

            if not results:
                return await reply_auto(event, "**❌ هیچ بازی‌ای پیدا نشد**")

            games = []

            for res in results:
                name = res.title or res.description
                if name:
                    games.append(name)

            if not games:
                return await reply_auto(event, "**❌ نام بازی‌ها پیدا نشد**")

            text = "**🎮 لیست بازی‌ها:\n\n**"

            for i, game in enumerate(games, 1):
                text += f"بازی {i}: `{game}`\n"

            await reply_auto(event, text)

        except Exception as e:
            await reply_auto(event, f"**⚠️ خطا در گرفتن لیست بازی: {e}**")

    # =========================
    # دستور راهنما اینلاین
    # =========================
    @client.on(events.NewMessage)
    @multi_lang([".راهنما", ".Guide", ".پنل", ".panel", "پنل", "panel", "راهنما", "Guide"])
    async def help_inline(event):

        try:
            results = await client.inline_query("self_nix_bot", "self-nix-panel-tjm")

            if not results:
                return await reply_auto(event, "**❌ نتیجه‌ای پیدا نشد**")

            await results[0].click(event.chat_id)
            await event.delete()

        except Exception as e:
            await reply_auto(event, f"**❌ خطا:\n{e}**")
1
