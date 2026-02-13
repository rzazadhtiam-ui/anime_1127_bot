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
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    # ---------------- پیدا کردن دکمه ----------------
    def find_button(self, btn_id):
        for r, row in enumerate(self.buttons_db):
            for c, btn in enumerate(row):
                if btn["id"] == btn_id:
                    return r, c, btn
        return None, None, None

    # ---------------- پنل کاربر ----------------
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

    # ---------------- پنل بازگشت ----------------
    def back_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=f"back_{user_id}"
        ))
        return markup

    # ---------------- لیست ادمین ----------------
    def admin_buttons(self):
        markup = types.InlineKeyboardMarkup()
        for row in self.buttons_db:
            for btn in row:
                markup.add(types.InlineKeyboardButton(
                    f"⚙️ {btn['name']}",
                    callback_data=f"admin_{btn['id']}"
                ))
        return markup

    # ---------------- پنل کنترل ----------------
    def admin_control(self, btn_id):
        markup = types.InlineKeyboardMarkup()

        markup.row(
            types.InlineKeyboardButton("⬆️", callback_data=f"up_{btn_id}"),
            types.InlineKeyboardButton("⬇️", callback_data=f"down_{btn_id}")
        )

        markup.row(
            types.InlineKeyboardButton("⬅️", callback_data=f"left_{btn_id}"),
            types.InlineKeyboardButton("➡️", callback_data=f"right_{btn_id}")
        )

        markup.add(
            types.InlineKeyboardButton("➕ ردیف جدید", callback_data=f"newrow_{btn_id}")
        )

        markup.add(
            types.InlineKeyboardButton("❌ حذف", callback_data=f"del_{btn_id}")
        )

        return markup

    # ================= handlers =================
    def register_handlers(self):

        # ---------- add ----------
        @self.bot.message_handler(commands=["add"])
        def add(message):
            if message.from_user.id != OWNER_ID:
                return
            self.user_state[OWNER_ID] = "name"
            self.bot.reply_to(message, "اسم دکمه؟")

        # ---------- admin ----------
        @self.bot.message_handler(commands=["admin"])
        def admin(message):
            if message.from_user.id != OWNER_ID:
                return
            self.bot.send_message(
                message.chat.id,
                "مدیریت دکمه‌ها",
                reply_markup=self.admin_buttons()
            )

        # ---------- text ----------
        @self.bot.message_handler(content_types=["text"])
        def text_handler(message):

            if message.from_user.id != OWNER_ID:
                return

            if self.user_state.get(OWNER_ID) == "name":
                self.temp_button["name"] = message.text
                self.user_state[OWNER_ID] = "text"
                self.bot.reply_to(message, "متن دکمه؟")
                return

            if self.user_state.get(OWNER_ID) == "text":

                new_btn = {
                    "id": str(uuid.uuid4()),
                    "name": self.temp_button["name"],
                    "text": message.text
                }

                if not self.buttons_db:
                    self.buttons_db.append([new_btn])
                else:
                    self.buttons_db[0].append(new_btn)

                self.save_buttons()

                self.user_state.clear()
                self.temp_button.clear()

                self.bot.reply_to(message, "✅ اضافه شد")

        # ---------- callback ----------
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):

            data = call.data
            uid = call.from_user.id

            # ===== انتخاب دکمه ادمین =====
            if data.startswith("admin_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return

            # ===== حذف =====
            if data.startswith("del_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)

                self.buttons_db[r].pop(c)
                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)

                self.save_buttons()

                self.bot.edit_message_text(
                    "حذف شد",
                    call.message.chat.id,
                    call.message.message_id
                )
                return

            # ===== move left =====
            if data.startswith("left_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)

                if c > 0:
                    self.buttons_db[r][c], self.buttons_db[r][c-1] = \
                        self.buttons_db[r][c-1], self.buttons_db[r][c]

                    self.save_buttons()

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return

            # ===== move right =====
            if data.startswith("right_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, _ = self.find_button(btn_id)

                if c < len(self.buttons_db[r]) - 1:
                    self.buttons_db[r][c], self.buttons_db[r][c+1] = \
                        self.buttons_db[r][c+1], self.buttons_db[r][c]

                    self.save_buttons()

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return

            # ===== move up =====
            if data.startswith("up_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)

                if r > 0:
                    self.buttons_db[r].pop(c)
                    self.buttons_db[r-1].append(btn)

                    if not self.buttons_db[r]:
                        self.buttons_db.pop(r)

                    self.save_buttons()

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return

            # ===== move down =====
            if data.startswith("down_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)

                if r < len(self.buttons_db) - 1:
                    self.buttons_db[r].pop(c)
                    self.buttons_db[r+1].append(btn)

                    if not self.buttons_db[r]:
                        self.buttons_db.pop(r)

                    self.save_buttons()

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return

            # ===== ردیف جدید =====
            if data.startswith("newrow_") and uid == OWNER_ID:

                btn_id = data.split("_")[1]
                r, c, btn = self.find_button(btn_id)

                self.buttons_db[r].pop(c)
                self.buttons_db.append([btn])

                if not self.buttons_db[r]:
                    self.buttons_db.pop(r)

                self.save_buttons()

                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.admin_control(btn_id)
                )
                return


print("PanelManager Ready")
