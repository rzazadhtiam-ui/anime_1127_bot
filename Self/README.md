# Telegram Session Builder (Tiam Version)

این پروژه یک **سایت ساخت سشن تلگرام با پنل ادمین و لینک‌های یک‌بارمصرف** است که با Flask و Telethon ساخته شده و سشن‌ها را در MongoDB ذخیره می‌کند.

---

## پیش‌نیازها

1. **Python 3.11+**
2. MongoDB فعال (Atlas یا سرور دیگر)
3. اتصال اینترنت برای نصب کتابخانه‌ها و اتصال به تلگرام

---

## نصب کتابخانه‌ها

تمام کتابخانه‌های لازم در `requirements.txt` قرار دارند.  
برای نصب، دستور زیر را اجرا کنید:

```bash
pip install -r requirements.txt
```

کتابخانه‌های اصلی پروژه:

- Flask – وب‌سرور
- Telethon – مدیریت سشن‌های تلگرام
- pymongo – ذخیره‌سازی در MongoDB
- dnspython – مورد نیاز MongoDB Atlas

کتابخانه‌های استاندارد پایتون نیز استفاده می‌شوند و نیازی به نصب جداگانه ندارند:

- os, threading, asyncio, secrets, time, datetime

---

## تنظیم MongoDB

در فایل `main.py` یا کد پروژه، اتصال MongoDB مشخص شده است:

```python
mongo_uri = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017/"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)
```

- `sessions` collection برای ذخیره سشن‌ها  
- `links` collection برای لینک‌های یک‌بارمصرف

---

## اجرای سرور

```bash
python main.py
```

- سایت روی پورت `8000` اجرا می‌شود
- مسیر اصلی: `/`  
- پنل ادمین: `/admin`  
  - یوزرنیم/پسورد پیش‌فرض: `admin / 123456`  
  - قابل تغییر در `self_config`

---

## قابلیت‌ها

1. ساخت سشن تلگرام با OTP و 2FA
2. ذخیره سشن‌ها در MongoDB
3. پنل ادمین برای ایجاد لینک‌های محدود
4. لینک‌های یک‌بارمصرف یا چندبار مصرف با ظرفیت مشخص
5. Keep-alive خودکار: هر ۴ دقیقه سایت خودش را صدا می‌زند
6. بررسی لینک قبل از نمایش صفحه اصلی

---

## توجه

- اگر لینک نامعتبر یا ظرفیت استفاده تمام شده باشد، صفحه اصلی پیام خطا نمایش می‌دهد.  
- برای استفاده در Render، اطمینان حاصل کنید که پورت `8000` باز است یا از متغیر محیطی PORT استفاده شود.
