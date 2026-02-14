import telebot
from update1 import PanelManager
from update1_1 import setup_self_bot
from flask import Flask
import threading
import os
import time
import requests

TOKEN = "8550709057:AAFzGO1-sCzxIHqJ0raZkB1yg9AqeO1PrJU"
RENDER_URL = "https://anime-1127-bot-1-edmd.onrender.com"  # لینک سایت رندر

bot = telebot.TeleBot(TOKEN)
panel = PanelManager(bot)
setup_self_bot(bot, TOKEN)

# -------- Flask Server --------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive ✅"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# -------- Self Ping --------
def self_ping():
    while True:
        try:
            requests.get(RENDER_URL)
            print("Self Ping Success ✅")
        except Exception as e:
            print("Self Ping Error:", e)

        time.sleep(300)  # هر 5 دقیقه


# -------- Telegram Bot --------
def run_bot():
    print("Bot Running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


# -------- Threads --------
threading.Thread(target=run_web).start()
threading.Thread(target=run_bot).start()
threading.Thread(target=self_ping).start()
