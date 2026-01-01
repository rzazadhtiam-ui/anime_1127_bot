
async def coin_loop():
    while True:
        await asyncio.sleep(60)
        for file in os.listdir(USER_DATA_DIR):
            if file.endswith(".json"):
                uid = int(file.replace(".json", ""))
                data = load_user_data(uid)
                data["coins"] = data.get("coins", 0) + 1
                save_user_data(uid, data)


# all_imports.py — وارد کردن تمام ماژول‌ها و ابزارها

# ---------- patch برای imghdr ----------
import sys
class imghdr_patch:
    @staticmethod
    def what(file, h=None):
        return None
sys.modules['imghdr'] = imghdr_patch
# --------------------------------------

# ---------- ماژول‌های استاندارد ----------
import os
import json
import asyncio
import tempfile
import random
from datetime import datetime, timedelta
import re
from typing import Optional, Callable, Any, Dict, List

# ---------- کتابخانه‌های خارجی ----------
import pytz
import requests
from telethon import TelegramClient, events, functions, Button, types
from telethon.errors import SessionPasswordNeededError, RPCError
from telethon.tl.types import InputPeerUser, ChatBannedRights, ChannelParticipantsAdmins
from telethon.tl.functions.channels import EditBannedRequest
from jdatetime import datetime as jdatetime

# ---------- فایل‌های داخلی پروژه ----------
from self_config import self_config, city_timezones
from self_commands_clock import *
from self_spam import *
from self_tools import self_tools
from self_welcome import *
from self_status import SelfStatusBot
from self_id import register


# ---------- تابع رجیستر ابزارها ----------
def register_tools(client):
    try:
        if 'register_clock' in globals():
            register_clock(client)

        if 'register_spam' in globals():
            register_spam(client)

        if 'register_welcome' in globals():
            register_welcome(client)

        if 'register_custom_tools' in globals():
            register_custom_tools(client)
            
        if 'register_jinx' in globals():
        	register_jinx(client, owner_id)        
        
        if 'modules_catcher_storage.py' in globals():
        	register_catcher_storage(client)

        print("✔️ ابزارها فعال شدند.")
    except Exception as e:
        print("❌ خطا در register_tools:", e)
