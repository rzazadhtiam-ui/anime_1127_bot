import telebot
from tiam import PanelManager

TOKEN = "8550709057:AAFzGO1-sCzxIHqJ0raZkB1yg9AqeO1PrJU"
bot = telebot.TeleBot(TOKEN)

# ساخت پنل منیجر
panel = PanelManager(bot)

# حالا میتونی infinity_polling بزنی
print("Bot Running...")
bot.infinity_polling(timeout=30, long_polling_timeout=30)
