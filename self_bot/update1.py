import telebot
from telebot import types
import json
import os
import uuid

OWNER_ID = 8588914809
DB_FILE = "buttons.json"

class PanelManager:

    def __init__(self, bot):
        self.bot = bot
        self.buttons_db = self.load_buttons()
        self.admin_preview_message = None
        self.waiting_name = False
        self.waiting_text = False
        self.temp_name = ""
        self.register_handlers()

    # ---------------- storage ----------------
    def save_buttons(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.buttons_db, f, ensure_ascii=False, indent=4)

    def load_buttons(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    # ---------------- helpers ----------------
    def find_button(self, btn_id):
        for r, row in enumerate(self.buttons_db):
            for c, btn in enumerate(row):
                if btn["id"] == btn_id:
                    return r, c, btn
        return None, None, None

    # ---------------- user panel ----------------
    def main_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        for row in self.buttons_db:
            btns = []
            for btn in row:
                btns.append(types.InlineKeyboardButton(
                    btn["name"],
                    callback_data=f"btn_{user_id}_{btn['id']}"
                ))
            markup.row(*btns)
        return markup

    def back_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=f"back_{user_id}"
        ))
        return markup

    # ---------------- realtime preview ----------------
    def update_admin_preview(self):
        if not self.admin_preview_message:
            return
        chat_id, msg_id = self.admin_preview_message
        try:
            self.bot.edit_message_reply_markup(
                chat_id,
                msg_id,
                reply_markup=self.main_panel(OWNER_ID)
            )
        except:
            pass

    # ================= handlers =================
    def register_handlers(self):

        # -------- show preview --------
        @self.bot.message_handler(commands=["admin"])
        def admin(message):
            if message.from_user.id != OWNER_ID:
                return

            preview = self.bot.send_message(
                message.chat.id,
                "📋 پیش نمایش پنل کاربر",
                reply_markup=self.main_panel(OWNER_ID)
            )
            self.admin_preview_message = (preview.chat.id, preview.message_id)
            self.bot.reply_to(message, "✅ آماده")

        # -------- add button --------
        @self.bot.message_handler(commands=["add"])
        def add(message):
            if message.from_user.id != OWNER_ID:
                return
            self.bot.reply_to(message, "اسم دکمه؟")
            self.waiting_name = True

        # -------- text handler --------
        @self.bot.message_handler(content_types=["text"])
        def text_handler(message):
            if message.from_user.id != OWNER_ID:
                return

            if self.waiting_name:
                self.temp_name = message.text
                self.waiting_name = False
                self.waiting_text = True
                self.bot.reply_to(message, "متن دکمه؟")
                return

            if self.waiting_text:
                new_btn = {
                    "id": str(uuid.uuid4()),
                    "name": self.temp_name,
                    "text": message.text
                }

                if not self.buttons_db:
                    self.buttons_db.append([new_btn])
                else:
                    self.buttons_db[0].append(new_btn)

                self.save_buttons()
                self.update_admin_preview()

                self.waiting_text = False
                self.bot.reply_to(message, "✅ دکمه اضافه شد")
                return

        # -------- inline query --------
        @self.bot.inline_query_handler(func=lambda q: True)
        def inline_query(query):
            results = [
                types.InlineQueryResultArticle(
                    id="panel",
                    title="📋 باز کردن پنل",
                    input_message_content=types.InputTextMessageContent("پنل 👇"),
                    reply_markup=self.main_panel(query.from_user.id)
                )
            ]
            self.bot.answer_inline_query(query.id, results, cache_time=1)

        # -------- callbacks --------
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            data = call.data
            uid = call.from_user.id

            # ===== user button =====
            if data.startswith("btn_"):
                _, user_id, btn_id = data.split("_")
                if str(uid) != user_id:
                    return
                _, _, btn = self.find_button(btn_id)
                if not btn:
                    return
                self.bot.edit_message_text(
                    btn["text"],
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.back_panel(uid)
                )
                return

            # ===== back =====
            if data.startswith("back_"):
                user_id = data.split("_")[1]
                if str(uid) != user_id:
                    return
                self.bot.edit_message_text(
                    "پنل 👇",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.main_panel(uid)
                )
                return

            # ===== delete, move, newrow (admin only) =====
            if uid != OWNER_ID:
                return

            # delete
            if data.startswith("del_"):
                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)
                if r is None:
                    return
                self.buttons_db[r].pop(c)
                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "✅ حذف شد")
                return

            # left
            if data.startswith("left_"):
                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)
                if r is None or c == 0:
                    return
                self.buttons_db[r][c], self.buttons_db[r][c-1] = self.buttons_db[r][c-1], self.buttons_db[r][c]
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "جابجا شد")
                return

            # right
            if data.startswith("right_"):
                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)
                if r is None or c >= len(self.buttons_db[r]) - 1:
                    return
                self.buttons_db[r][c], self.buttons_db[r][c+1] = self.buttons_db[r][c+1], self.buttons_db[r][c]
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "جابجا شد")
                return

            # up
            if data.startswith("up_"):
                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)
                if r is None or r == 0:
                    return
                self.buttons_db[r].pop(c)
                target = self.buttons_db[r-1]
                if c <= len(target):
                    target.insert(c, btn)
                else:
                    target.append(btn)
                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "جابجا شد")
                return

            # down
            if data.startswith("down_"):
                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)
                if r is None or r >= len(self.buttons_db) - 1:
                    return
                self.buttons_db[r].pop(c)
                target = self.buttons_db[r+1]
                if c <= len(target):
                    target.insert(c, btn)
                else:
                    target.append(btn)
                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "جابجا شد")
                return

            # new row
            if data.startswith("newrow_"):
                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)
                if r is None:
                    return
                self.buttons_db[r].pop(c)
                self.buttons_db.append([btn])
                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)
                self.save_buttons()
                self.update_admin_preview()
                self.bot.answer_callback_query(call.id, "ردیف جدید ساخته شد")
                return

print("PanelManager Ready")
