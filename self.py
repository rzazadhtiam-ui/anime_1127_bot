from telethon import TelegramClient
from datetime import datetime, timedelta
import pytz
from aiohttp import web

api_id = 24645053
api_hash = "88c0167b74a24fac0a85c26c1f6d1991"
session_name = "self_spam"

client = TelegramClient(session_name, api_id, api_hash)

MESSAGE_TEXT = "🎣 Забросить удочку"
DELAY = timedelta(hours=1, minutes=1)
iran_tz = pytz.timezone('Asia/Tehran')

# --- ثبت پیام‌ها تا ساعت 23:59 همان روز ---
async def schedule_messages_for_today():
    now = datetime.now(iran_tz)
    end_of_period = now.replace(hour=23, minute=59, second=0, microsecond=0)

    send_time = now
    count = 0
    while send_time <= end_of_period:
        await client.send_message("@StarfishUltimateBot", MESSAGE_TEXT, schedule=send_time)
        send_time += DELAY
        count += 1
        await asyncio.sleep(0.2)  # جلوگیری از Flood

    print(f"✅ {count} پیام تا ساعت 23:59 ایران امروز ثبت شدند")
    return count

# --- وب‌هوک ساده ---
async def handle_webhook(request):
    await client.start()
    count = await schedule_messages_for_today()
    return web.Response(text=f"✅ {count} پیام ثبت شدند")

# --- راه‌اندازی وب‌هوک ---
app = web.Application()
app.add_routes([web.get('/', handle_webhook)])
app.add_routes([web.get('/ping', lambda r: web.Response(text="pong"))])  # optional ping

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8080)
