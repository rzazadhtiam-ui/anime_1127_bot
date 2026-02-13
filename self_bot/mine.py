import telebot
from update1 import PanelManager
from flask import Flask
import threading
import os

TOKEN = "8550709057:AAFzGO1-sCzxIHqJ0raZkB1yg9AqeO1PrJU"

bot = telebot.TeleBot(TOKEN)
panel = PanelManager(bot)

# -------- Flask Server --------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive ✅"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# -------- Telegram Bot --------
def run_bot():
    print("Bot Running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


# -------- Threads --------
threading.Thread(target=run_web).start()
threading.Thread(target=run_bot).start()
