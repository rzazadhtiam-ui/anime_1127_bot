#!/usr/bin/env python3
"""
Self Nix Panel - نسخه ماژولار (فقط با ایمپورت در هسته ربات کار می‌کند)
- تمام دکمه‌های بازگشت = سبز (success)
- دکمه بستن پنل = قرمز (danger)
- بدون کال کردن setup_panel(bot) هیچ فعالیتی ندارد
"""

import asyncio
import threading
import uuid
from typing import Optional, Dict

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pymongo import MongoClient
import certifi

# ==================== تنظیمات ====================
OWNER_ID = 6433381392
MAIN_TEXT = "📖 ⦁ Self Nix پنل راهنما ربات :"
PANEL_TIMEOUT = 180

# ==================== دیتابیس ====================
mongo_uri = (
    "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@"
    "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017,"
    "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017"
    "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"
)

client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client["self_panel_db"]
buttons_col = db["buttons"]
buttons_col.create_index("name")

# ==================== متغیرهای جهانی ====================
bot: Optional[Bot] = None
router = Router()

history: Dict[int, list] = {}
_timers: Dict[int, threading.Timer] = {}

# ==================== States ====================
class AddButtonStates(StatesGroup):
    waiting_name = State()
    waiting_type = State()
    waiting_text = State()

class EditStates(StatesGroup):
    waiting_rename = State()
    waiting_edit_text = State()
    waiting_position = State()

# ==================== توابع کمکی ====================
def get_panel_text(name: str) -> str:
    btn = buttons_col.find_one({"name": name})
    if not btn:
        return "📭 پنل پیدا نشد"
    if btn.get("text"):
        return btn["text"]
    if btn.get("type") == "panel":
        return f"📂 {name}"
    if btn.get("type") == "text_panel":
        return btn.get("text", "")
    return "📭 بدون متن"


def _cancel_timer(uid: int):
    if uid in _timers:
        try:
            _timers.pop(uid).cancel()
        except:
            pass


def _close_panel(uid: int, *, inline_id: Optional[str] = None,
                 chat_id: Optional[int] = None, msg_id: Optional[int] = None,
                 reason: str = "manual"):
    _cancel_timer(uid)
    history.pop(uid, None)

    text = "⏱ <b>پنل به دلیل عدم فعالیت بسته شد</b>" if reason == "timeout" else "✅ <b>پنل با موفقیت بسته شد</b>"

    try:
        if inline_id and bot:
            asyncio.create_task(bot.edit_message_text(text, inline_message_id=inline_id, parse_mode="HTML"))
        elif chat_id and msg_id and bot:
            asyncio.create_task(bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML"))
    except Exception as e:
        print(f"[close_panel error] {e}")


def _reset_timer(uid: int, call: CallbackQuery):
    _cancel_timer(uid)
    inline_id = getattr(call, "inline_message_id", None)
    chat_id = call.message.chat.id if call.message else None
    msg_id = call.message.message_id if call.message else None

    def _expire():
        _close_panel(uid, inline_id=inline_id, chat_id=chat_id, msg_id=msg_id, reason="timeout")

    t = threading.Timer(PANEL_TIMEOUT, _expire)
    t.daemon = True
    t.start()
    _timers[uid] = t


def build_panel_markup(user_id: int, parent: str, show_back: bool = False) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    buttons = list(buttons_col.find({"parent": parent}).sort([("row", 1), ("col", 1)]))
    grid: Dict[int, Dict[int, InlineKeyboardButton]] = {}

    for btn in buttons:
        r = int(btn.get("row", 0))
        c = int(btn.get("col", 0))
        grid.setdefault(r, {})[c] = InlineKeyboardButton(
            text=btn["name"],
            callback_data=f"open_{user_id}_{btn['name']}_{parent}"
        )

    for r in sorted(grid.keys()):
        row = [grid[r][c] for c in sorted(grid[r].keys())]
        markup.inline_keyboard.append(row)

    # ==================== تمام دکمه‌های بازگشت = سبز ====================
    if show_back and parent != "root":
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=f"back_{user_id}_{parent}",
                style="success"
            )
        ])

    # ==================== دکمه بستن پنل = قرمز ====================
    if parent == "root":
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text="❌ بستن پنل",
                callback_data=f"close_{user_id}",
                style="danger"
            )
        ])

    return markup


def admin_panel_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for btn in buttons_col.find():
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{btn['name']} | {btn.get('type', 'none')}",
                callback_data=f"edit_menu||{btn['_id']}"
            )
        ])
    return markup

def register_panel(router: Router, bot: Bot):
# ==================== هندلرها ====================
    @router.message(F.text == "/add")
    async def add_button_start(message: Message, state: FSMContext):
        if message.from_user.id != OWNER_ID:
            return
        await message.answer("اسم دکمه جدید را بفرست:")
        await state.set_state(AddButtonStates.waiting_name)


    @router.message(AddButtonStates.waiting_name)
    async def add_button_name(message: Message, state: FSMContext):
        name = message.text.strip()
        if not name:
            await message.answer("نام معتبر نیست.")
            return

        new_id = str(uuid.uuid4())
        buttons_col.insert_one({
        "_id": new_id, "name": name, "type": "pending",
        "parent": "pending", "text": "", "row": 0, "col": 0
    })
        await state.update_data(name=name)
        await message.answer("نوع دکمه:\n1 = panel\n2 = text_panel")
        await state.set_state(AddButtonStates.waiting_type)


    @router.message(AddButtonStates.waiting_type)
    async def add_button_type(message: Message, state: FSMContext):
        ttype = message.text.strip()
        data = await state.get_data()
        name = data.get("name")

        if ttype == "2":
            panels = list(buttons_col.find({"type": "panel"}))
            if not panels:
                await message.answer("اول panel بساز.")
                await state.clear()
                return
            kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📁 {p['name']}", callback_data=f"set_textparent||{name}||{p['name']}")]
            for p in panels
        ])
            await message.answer(f"دکمه «{name}» زیر کدام پنل؟", reply_markup=kb)
            await state.clear()
            return

        panels = list(buttons_col.find({"type": "panel"}))
        kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 root", callback_data=f"set_parent||{name}||root")]
    ] + [
        [InlineKeyboardButton(text=p["name"], callback_data=f"set_parent||{name}||{p['name']}")]
        for p in panels
    ])
        await message.answer("این پنل زیر کدام پنل ساخته شود؟", reply_markup=kb)
        await state.clear()


    @router.message(F.text == "/panel_admin")
    async def admin_cmd(message: Message):
        if message.from_user.id != OWNER_ID:
            return
        if buttons_col.count_documents({}) == 0:
            await message.answer("هیچ دکمه‌ای وجود ندارد.")
            return
        await message.answer("⚙️ دکمه مورد نظر را انتخاب کنید:", reply_markup=admin_panel_markup())


    @router.message(F.text == "/remove")
    async def remove_cmd(message: Message):
        if message.from_user.id != OWNER_ID:
            return
        markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 {btn['name']}", callback_data=f"delete||{btn['_id']}")]
        for btn in buttons_col.find()
    ])
        await message.answer("🗑 کدام دکمه حذف شود؟", reply_markup=markup)


    @router.inline_query(F.query == "self-nix-panel-tjm")
    async def inline_panel(query: InlineQuery):
        uid = query.from_user.id
        history.setdefault(uid, ["root"])
        markup = build_panel_markup(uid, "root")
        result = InlineQueryResultArticle(
            id=f"panel_{uid}",
            title="📋 پنل Self Nix",
        input_message_content=InputTextMessageContent(message_text=MAIN_TEXT, parse_mode="HTML"),
        reply_markup=markup
    )
        await query.answer([result], cache_time=5)


# ==================== Callback Handlers ====================
    @router.callback_query(F.data.startswith("open_"))
    async def open_panel(call: CallbackQuery):
        _, owner_id, name, parent = call.data.split("_", 3)
        uid = call.from_user.id
        if int(owner_id) != uid:
            await call.answer("دسترسی ندارید.", show_alert=True)
            return

        btn = buttons_col.find_one({"name": name, "parent": parent})
        if not btn:
            await call.answer("پیدا نشد.", show_alert=True)
            return

        _reset_timer(uid, call)
        history.setdefault(uid, []).append(name)

        if btn.get("type") != "panel":
            markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"back_{uid}_{parent}", style="success")]
        ])
            await call.message.edit_text(btn.get("text", ""), reply_markup=markup, parse_mode="HTML")
            return

        markup = build_panel_markup(uid, parent=name, show_back=True)
        if not list(buttons_col.find({"parent": name})):
            markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📭 خالی", callback_data="noop")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"back_{uid}_{name}", style="success")]
        ])

        text_to_show = btn.get("text") or get_panel_text(name)
        await call.message.edit_text(text_to_show, reply_markup=markup, parse_mode="HTML")


    @router.callback_query(F.data.startswith("back_"))
    async def back_handler(call: CallbackQuery):
        _, uid_str, parent = call.data.split("_", 2)
        uid = int(uid_str)
        if uid != call.from_user.id:
            return
    
        _reset_timer(uid, call)
        hist = history.get(uid, ["root"])
        if len(hist) > 1:
            hist.pop()
        current = hist[-1] if hist else "root"
        history[uid] = hist

        text = MAIN_TEXT if current == "root" else get_panel_text(current)
        markup = build_panel_markup(uid, current, show_back=(current != "root"))
        await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


    @router.callback_query(F.data.startswith("close_"))
    async def close_handler(call: CallbackQuery):
        uid = int(call.data.split("_")[1])
        if uid != call.from_user.id:
            return
        inline_id = getattr(call, "inline_message_id", None)
        chat_id = call.message.chat.id if call.message else None
        msg_id = call.message.message_id if call.message else None
        _close_panel(uid, inline_id=inline_id, chat_id=chat_id, msg_id=msg_id, reason="manual")
        await call.answer("بسته شد.")


    @router.callback_query(F.data.startswith("delete||"))
    async def delete_button(call: CallbackQuery):
        if call.from_user.id != OWNER_ID:
            return
        btn_id = call.data.split("||")[1]
        buttons_col.delete_one({"_id": btn_id})
        await call.answer("حذف شد ✅")
        await call.message.edit_text("دکمه حذف شد.", reply_markup=admin_panel_markup())


    @router.callback_query(F.data.startswith("edit_menu||"))
    async def edit_menu(call: CallbackQuery):
        if call.from_user.id != OWNER_ID:
            return
        btn_id = call.data.split("||")[1]
        btn = buttons_col.find_one({"_id": btn_id})
        if not btn:
            await call.answer("پیدا نشد.")
            return

        markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تغییر نام", callback_data=f"rename||{btn_id}")],
        [InlineKeyboardButton(text="📝 تغییر متن", callback_data=f"edit_text||{btn_id}")],
        [InlineKeyboardButton(text="📍 تغییر مختصات", callback_data=f"move_pos||{btn_id}")],
        [InlineKeyboardButton(text="🗑 حذف", callback_data=f"delete||{btn_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel")]
    ])
        await call.message.edit_text(f"ویرایش: {btn['name']}", reply_markup=markup)


    @router.callback_query(F.data.startswith("rename||"))
    async def rename_start(call: CallbackQuery, state: FSMContext):
        if call.from_user.id != OWNER_ID:
            return
        await state.update_data(btn_id=call.data.split("||")[1])
        await call.message.answer("نام جدید را بفرست:")
        await state.set_state(EditStates.waiting_rename)


    @router.message(EditStates.waiting_rename)
    async def rename_save(message: Message, state: FSMContext):
        if message.from_user.id != OWNER_ID:
            return
        data = await state.get_data()
        buttons_col.update_one({"_id": data["btn_id"]}, {"$set": {"name": message.text.strip()}})
        await message.answer("✅ نام تغییر کرد.")
        await state.clear()


    @router.callback_query(F.data.startswith("edit_text||"))
    async def edit_text_start(call: CallbackQuery, state: FSMContext):
        if call.from_user.id != OWNER_ID:
            return
        await state.update_data(btn_id=call.data.split("||")[1])
        await call.message.answer("متن جدید را بفرست:")
        await state.set_state(EditStates.waiting_edit_text)


    @router.message(EditStates.waiting_edit_text)
    async def edit_text_save(message: Message, state: FSMContext):
        if message.from_user.id != OWNER_ID:
            return
        data = await state.get_data()
        buttons_col.update_one({"_id": data["btn_id"]}, {"$set": {"text": message.text.strip()}})
        await message.answer("✅ متن آپدیت شد.")
        await state.clear()


    @router.callback_query(F.data.startswith("move_pos||"))
    async def move_pos_start(call: CallbackQuery, state: FSMContext):
        if call.from_user.id != OWNER_ID:
            return
        await state.update_data(btn_id=call.data.split("||")[1])
        await call.message.answer("مختصات جدید (row col) مثلاً: 2 3")
        await state.set_state(EditStates.waiting_position)


    @router.message(EditStates.waiting_position)
    async def move_pos_save(message: Message, state: FSMContext):
        if message.from_user.id != OWNER_ID:
            return
        data = await state.get_data()
        try:
            row, col = map(int, message.text.strip().split())
            buttons_col.update_one({"_id": data["btn_id"]}, {"$set": {"row": row, "col": col}})
            await message.answer("✅ موقعیت تغییر کرد.")
        except:
            await message.answer("فرمت اشتباه است.")
        await state.clear()


    @router.callback_query(F.data.startswith("set_parent||"))
    async def set_parent_handler(call: CallbackQuery):
        if call.from_user.id != OWNER_ID:
            return
        parts = call.data.split("||")
        name, parent = parts[1], parts[2]
        if parent == name:
            parent = "root"
        buttons_col.update_one({"name": name}, {"$set": {"parent": parent, "type": "panel"}})
        await call.answer("✅ ساخته شد")
        if bot:
            await call.message.edit_text(MAIN_TEXT, reply_markup=build_panel_markup(call.from_user.id, "root"))


    @router.callback_query(F.data.startswith("set_textparent||"))
    async def set_textparent(call: CallbackQuery, state: FSMContext):
        if call.from_user.id != OWNER_ID:
            return
        parts = call.data.split("||")
        await state.update_data(name=parts[1], parent=parts[2])
        await call.message.answer("متن دکمه را بفرست:")
        await state.set_state(AddButtonStates.waiting_text)


    @router.message(AddButtonStates.waiting_text)
    async def save_text_panel(message: Message, state: FSMContext):
        data = await state.get_data()
        buttons_col.insert_one({
        "_id": str(uuid.uuid4()),
        "name": data["name"],
        "parent": data["parent"],
        "type": "text_panel",
        "text": message.text.strip(),
        "row": 0, "col": 0
    })
        await message.answer(f"✅ دکمه «{data['name']}» ساخته شد.")
        await state.clear()


    @router.callback_query(F.data == "cancel")
    async def cancel_handler(call: CallbackQuery):
        await call.message.edit_text("عملیات لغو شد.")
        await call.answer()


    @router.callback_query(F.data == "noop")
    async def noop(call: CallbackQuery):
        await call.answer()


# ==================== تابع راه‌اندازی (هسته ربات) ====================
    async def setup_panel(bot_instance: Bot):

        global bot
        bot = bot_instance
        print("✅ ماژول Self Nix Panel راه‌اندازی شد (وابسته به هسته ربات)")


# ==================== اجرای مستقیم غیرفعال ====================
    print("ℹ️ این ماژول فقط از طریق ایمپورت در هسته ربات فعال می‌شود.")
    print("   حتماً از تابع setup_panel(bot) در ربات اصلی استفاده کنید.")
