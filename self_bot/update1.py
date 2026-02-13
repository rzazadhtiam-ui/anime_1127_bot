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
        self.user_state = {}
        self.temp_button = {}
        self.register_handlers()

    # ---------------- ذخیره ----------------
    def save_buttons(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.buttons_db, f, ensure_ascii=False, indent=4)

    # ---------------- لود ----------------
    def load_buttons(self):
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return []

    # ---------------- پیدا کردن دکمه ----------------
    def find_button(self, btn_id):
        for i, row in enumerate(self.buttons_db):
            for j, btn in enumerate(row):
                if btn["id"] == btn_id:
                    return i, j, btn
        return None, None, None

    # ---------------- پنل کاربران ----------------
    def main_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        for row in self.buttons_db:
            buttons = []
            for btn in row:
                buttons.append(
                    types.InlineKeyboardButton(
                        btn["name"],
                        callback_data=f"btn_{user_id}_{btn['id']}"
                    )
                )
            if buttons:
                markup.row(*buttons)
        return markup

    # ---------------- پنل بازگشت ----------------
    def back_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data=f"back_{user_id}"
            )
        )
        return markup

    # ---------------- پنل انتخاب دکمه برای ادمین ----------------
    def admin_buttons_list(self):
        markup = types.InlineKeyboardMarkup()
        for row in self.buttons_db:
            for btn in row:
                markup.add(
                    types.InlineKeyboardButton(
                        f"⚙️ {btn['name']}",
                        callback_data=f"admin_{btn['id']}"
                    )
                )
        return markup

    # ---------------- پنل کنترل دکمه ----------------
    def admin_control_panel(self, btn_id):
        markup = types.InlineKeyboardMarkup()

        markup.row(
            types.InlineKeyboardButton("⬆️ ردیف بالا", callback_data=f"row_up_{btn_id}"),
            types.InlineKeyboardButton("⬇️ ردیف پایین", callback_data=f"row_down_{btn_id}")
        )

        markup.row(
            types.InlineKeyboardButton("⬅️ چپ", callback_data=f"col_left_{btn_id}"),
            types.InlineKeyboardButton("➡️ راست", callback_data=f"col_right_{btn_id}")
        )

        markup.row(
            types.InlineKeyboardButton("➕ ردیف جدید", callback_data=f"new_row_{btn_id}")
        )

        markup.row(
            types.InlineKeyboardButton("❌ حذف", callback_data=f"del_{btn_id}")
        )

        return markup

    # ================= ثبت هندلر =================
    def register_handlers(self):

        # -------- INLINE --------
        @self.bot.inline_handler(lambda q: True)
        def inline_panel(query):

            markup = self.main_panel(query.from_user.id)

            article = types.InlineQueryResultArticle(
                id="panel",
                title="📖 پنل ربات",
                input_message_content=types.InputTextMessageContent(
                    "📖 پنل راهنمای ربات:"
                ),
                reply_markup=markup
            )

            self.bot.answer_inline_query(query.id, [article], cache_time=1)

        # -------- افزودن دکمه --------
        @self.bot.message_handler(commands=["add"])
        def add_start(message):

            if message.from_user.id != OWNER_ID:
                return

            self.user_state[OWNER_ID] = "wait_name"
            self.bot.reply_to(message, "اسم دکمه را بفرست")

        # -------- حذف و مدیریت --------
        @self.bot.message_handler(commands=["admin", "remove"])
        def admin_panel(message):

            if message.from_user.id != OWNER_ID:
                return

            if not self.buttons_db:
                self.bot.send_message(message.chat.id, "هیچ دکمه‌ای وجود ندارد")
                return

            self.bot.send_message(
                message.chat.id,
                "پنل مدیریت دکمه‌ها",
                reply_markup=self.admin_buttons_list()
            )

        # -------- پردازش متن --------
        @self.bot.message_handler(content_types=["text"])
        def text_handler(message):

            if message.from_user.id != OWNER_ID:
                return

            uid = OWNER_ID

            if self.user_state.get(uid) == "wait_name":

                name = message.text.strip()
                if not name:
                    return

                self.temp_button[uid] = {"name": name}
                self.user_state[uid] = "wait_text"
                self.bot.reply_to(message, "متن دکمه را بفرست")
                return

            if self.user_state.get(uid) == "wait_text":

                text = message.text.strip()
                name = self.temp_button[uid]["name"]

                new_btn = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "text": text
                }

                if not self.buttons_db:
                    self.buttons_db.append([new_btn])
                else:
                    self.buttons_db[0].append(new_btn)

                self.save_buttons()

                self.user_state.pop(uid)
                self.temp_button.pop(uid)

                self.bot.reply_to(message, "✅ دکمه اضافه شد")

        # -------- CALLBACK --------
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):

            data = call.data
            user_id = call.from_user.id

            # ---------- بازگشت ----------
            if data.startswith("back_"):

                owner = int(data.split("_")[1])

                self.bot.edit_message_text(
                    "📖 پنل راهنما:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.main_panel(owner)
                )
                return

            # ---------- نمایش متن ----------
            if data.startswith("btn_"):

                _, owner, btn_id = data.split("_")
                owner = int(owner)

                _, _, btn = self.find_button(btn_id)
                if not btn:
                    return

                self.bot.edit_message_text(
                    btn["text"],
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.back_panel(owner)
                )
                return

            # ---------- انتخاب دکمه ادمین ----------
            if data.startswith("admin_") and user_id == OWNER_ID:

                btn_id = data.replace("admin_", "")

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control_panel(btn_id)
                )
                return

            # ---------- حذف ----------
            if data.startswith("del_") and user_id == OWNER_ID:

                btn_id = data.replace("del_", "")

                row, col, _ = self.find_button(btn_id)
                if row is None:
                    return

                self.buttons_db[row].pop(col)

                if not self.buttons_db[row]:
                    self.buttons_db.pop(row)

                self.save_buttons()

                self.bot.edit_message_text(
                    "✅ حذف شد",
                    call.message.chat.id,
                    call.message.message_id
                )
                return

            # ---------- انتقال ردیف بالا ----------
            if data.startswith("row_up_") and user_id == OWNER_ID:

                btn_id = data.replace("row_up_", "")
                row, col, btn = self.find_button(btn_id)

                if row > 0:
                    self.buttons_db[row].pop(col)
                    self.buttons_db[row - 1].append(btn)

                    if not self.buttons_db[row]:
                        self.buttons_db.pop(row)

                    self.save_buttons()

                return

            # ---------- انتقال ردیف پایین ----------
            if data.startswith("row_down_") and user_id == OWNER_ID:

                btn_id = data.replace("row_down_", "")
                row, col, btn = self.find_button(btn_id)

                if row < len(self.buttons_db) - 1:
                    self.buttons_db[row].pop(col)
                    self.buttons_db[row + 1].append(btn)

                    if not self.buttons_db[row]:
                        self.buttons_db.pop(row)

                    self.save_buttons()

                return

            # ---------- جابجایی داخل ردیف ----------
            if data.startswith("col_left_") and user_id == OWNER_ID:

                btn_id = data.replace("col_left_", "")
                row, col, _ = self.find_button(btn_id)

                if col > 0:
                    self.buttons_db[row][col], self.buttons_db[row][col - 1] = \
                        self.buttons_db[row][col - 1], self.buttons_db[row][col]

                    self.save_buttons()

                return

            if data.startswith("col_right_") and user_id == OWNER_ID:

                btn_id = data.replace("col_right_", "")
                row, col, _ = self.find_button(btn_id)

                if col < len(self.buttons_db[row]) - 1:
                    self.buttons_db[row][col], self.buttons_db[row][col + 1] = \
                        self.buttons_db[row][col + 1], self.buttons_db[row][col]

                    self.save_buttons()

                return

            # ---------- انتقال به ردیف جدید ----------
            if data.startswith("new_row_") and user_id == OWNER_ID:

                btn_id = data.replace("new_row_", "")
                row, col, btn = self.find_button(btn_id)

                self.buttons_db[row].pop(col)
                self.buttons_db.append([btn])

                if not self.buttons_db[row]:
                    self.buttons_db.pop(row)

                self.save_buttons()
                return


print("PanelManager Ready")
