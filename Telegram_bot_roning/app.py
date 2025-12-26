import os
import ast
import uuid
import shutil
import subprocess
import tempfile
from flask import Flask, request, jsonify, render_template_string

# =======================
# CONFIG
# =======================
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.abspath("user_apps")
os.makedirs(BASE_DIR, exist_ok=True)

# وبهوک مشترک
GLOBAL_WEBHOOK_PATH = "/webhook"

# =======================
# FLASK
# =======================
app = Flask(__name__)

# =======================
# HTML
# =======================
HTML = """
<!doctype html>
<html lang="fa">
<head>
<meta charset="utf-8">
<title>Python Bot Platform</title>
<style>
body{background:#0b0b0b;color:#fff;font-family:tahoma}
textarea{width:100%;height:260px;background:#000;color:#00ff9c;padding:15px}
button{padding:10px 25px;margin:10px;font-size:16px}
pre{background:#000;border:1px solid #333;padding:15px;min-height:150px}
</style>
</head>
<body>

<h2>🚀 پلتفرم اجرای کد پایتون</h2>

<textarea id="code" placeholder="کد پایتون خود را وارد کنید"></textarea><br>

<button onclick="run('test')">اجرای تستی</button>
<button onclick="run('activate')">فعال‌سازی کد</button>

<h3>📤 خروجی</h3>
<pre id="out">---</pre>

<script>
function run(mode){
  fetch("/run/"+mode,{
    method:"POST",
    body:document.getElementById("code").value
  })
  .then(r=>r.text())
  .then(t=>document.getElementById("out").textContent=t)
}
</script>

</body>
</html>
"""

# =======================
# SECURITY CHECK
# =======================
DANGEROUS_NODES = (
    ast.Import,
    ast.ImportFrom,
)

DANGEROUS_WORDS = [
    "os.", "sys.", "subprocess", "shutil",
    "open(", "__import__", "eval(", "exec("
]

def is_code_safe(code: str) -> bool:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, DANGEROUS_NODES):
                return False
        for word in DANGEROUS_WORDS:
            if word in code:
                return False
        return True
    except:
        return False

# =======================
# EXECUTION ENGINE
# =======================
def run_python(code: str, persistent=False):
    workdir = tempfile.mkdtemp() if not persistent else os.path.join(BASE_DIR, str(uuid.uuid4()))
    os.makedirs(workdir, exist_ok=True)

    main_file = os.path.join(workdir, "main.py")

    # preload
preload = """
# --- وب و API ---
import flask
import fastapi
import requests
import httpx
import urllib3

# --- تلگرام و پیام‌رسان ---
import telebot
import telegram
import aiogram
import telethon
import pyrogram

# --- دیتابیس و ذخیره‌سازی ---
import sqlite3
import pymongo
import psycopg2
import redis
import sqlalchemy

# --- امنیت و رمزنگاری ---
import bcrypt
import passlib
import itsdangerous
import jwt
import cryptography

# --- پردازش و فرمت‌ها ---
import json
import yaml
import xmltodict
import lxml
from bs4 import BeautifulSoup

# --- ابزارها و کمکی‌ها ---
import math
import random
import datetime
import time
import os
import sys
import functools
import itertools
import collections

# --- تاریخ و زمان ---
import datetime
import pytz
import dateutil
import pendulum

# --- ریاضی و تحلیل داده ---
import statistics
import decimal
import fractions
import numpy
import scipy
import sympy
import pandas

# --- تصویر و پردازش ---
from PIL import Image
import imageio
import cv2
import qrcode

# --- متن و NLP ---
import re
import nltk
import spacy
import textblob

# --- ماشین لرنینگ محدود (CPU) ---
import sklearn
import xgboost
import lightgbm
"""

    with open(main_file, "w", encoding="utf-8") as f:
        f.write(preload + "\n" + code)

    try:
        result = subprocess.run(
            ["python3", main_file],
            input="123\n",
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "⏱ اجرای کد بیش از حد طول کشید"
    finally:
        if not persistent:
            shutil.rmtree(workdir, ignore_errors=True)

    return output.strip()

# =======================
# ROUTES
# =======================
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/run/test", methods=["POST"])
def run_test():
    code = request.data.decode()

    if not is_code_safe(code):
        return "❌ کاربر گرامی ما قادر به فعال کردن کد شما نمی‌باشیم"

    out = run_python(code, persistent=False)
    return out or "بدون خروجی"

@app.route("/run/activate", methods=["POST"])
def run_activate():
    code = request.data.decode()

    if not is_code_safe(code):
        return "❌ کاربر گرامی ما قادر به فعال کردن کد شما نمی‌باشیم"

    out = run_python(code, persistent=True)
    return "✅ کاربر گرامی کد شما با موفقیت فعال شد 😁\n\n" + (out or "بدون خروجی")

# =======================
# WEBHOOK (shared)
# =======================
@app.route(GLOBAL_WEBHOOK_PATH, methods=["POST"])
def webhook():
    return jsonify({"status": "ok"})

# =======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
