import telebot
from telebot import types
import json
import os

OWNER_ID = 8588914809
DB_FILE = "buttons.json"

class PanelManager:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.buttons_db = self.load_buttons()  # لیست ردیف‌ها
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
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    # ---------------- پنل کاربران ----------------
    def main_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        for row in self.buttons_db:
            buttons = []
            for btn in row:
                if btn.get("name"):
                    buttons.append(types.InlineKeyboardButton(
                        btn["name"],
                        callback_data=f"btn_{user_id}_{btn['name']}"
                    ))
            if buttons:
                markup.row(*buttons)
        return markup

    # ---------------- پنل بازگشت ----------------
    def back_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=f"back_{user_id}"
        ))
        return markup

    # ---------------- پنل ادمین ----------------
    def admin_panel(self, btn_name):
        markup = types.InlineKeyboardMarkup()
        # ردیف اول: جابجایی عمودی
        markup.row(
            types.InlineKeyboardButton("⬆️ بالا", callback_data=f"move_up_{btn_name}"),
            types.InlineKeyboardButton("⬇️ پایین", callback_data=f"move_down_{btn_name}")
        )
        # ردیف دوم: جابجایی افقی
        markup.row(
            types.InlineKeyboardButton("⬅️ چپ", callback_data=f"move_left_{btn_name}"),
            types.InlineKeyboardButton("➡️ راست", callback_data=f"move_right_{btn_name}")
        )
        # ردیف سوم: حذف و بازگشت
        markup.row(
            types.InlineKeyboardButton("❌ حذف", callback_data=f"remove_{btn_name}"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")
        )
        return markup

    # ================= ثبت handler =================
    def register_handlers(self):
        # -------- افزودن دکمه --------
        @self.bot.message_handler(commands=['add'])
        def add_button_start(message):
            if message.from_user.id != OWNER_ID:
                return
            self.bot.send_message(message.chat.id, "اسم دکمه را بفرست")
            self.user_state[message.from_user.id] = "wait_name"

        @self.bot.message_handler(func=lambda m: True)
        def add_button_process(message):
            if message.from_user.id != OWNER_ID:
                return
            uid = message.from_user.id

            if self.user_state.get(uid) == "wait_name":
                if not message.text.strip():
                    self.bot.reply_to(message, "اسم خالی مجاز نیست")
                    return
                self.temp_button[uid] = {"name": message.text.strip()}
                self.user_state[uid] = "wait_text"
                self.bot.send_message(message.chat.id, "متن دکمه را بفرست")
                return

            if self.user_state.get(uid) == "wait_text":
                name = self.temp_button[uid]["name"]
                text = message.text
                # ذخیره در ردیف اول به صورت پیش‌فرض
                if not self.buttons_db:
                    self.buttons_db.append([{"name": name, "text": text}])
                else:
                    self.buttons_db[0].append({"name": name, "text": text})
                self.save_buttons()
                self.user_state.pop(uid)
                self.temp_button.pop(uid)
                self.bot.send_message(message.chat.id, "✅ دکمه اضافه شد")

        # -------- حذف دکمه (دستور /remov) --------
        @self.bot.message_handler(commands=['remov'])
        def remove_button(message):
            if message.from_user.id != OWNER_ID: return
            if not self.buttons_db:
                self.bot.send_message(message.chat.id, "هیچ دکمه‌ای وجود ندارد")
                return
            markup = types.InlineKeyboardMarkup()
            for row in self.buttons_db:
                for btn in row:
                    markup.add(types.InlineKeyboardButton(
                        f"❌ {btn['name']}",
                        callback_data=f"remove_{btn['name']}"
                    ))
            self.bot.send_message(
                message.chat.id,
                "روی دکمه‌ای که میخوای حذف بشه بزن",
                reply_markup=markup
            )

        # -------- پنل ادمین --------
        @self.bot.message_handler(commands=['panel_admin'])
        def panel_admin_cmd(message):
            if message.from_user.id != OWNER_ID: return
            if not self.buttons_db:
                self.bot.send_message(message.chat.id, "هیچ دکمه‌ای وجود ندارد")
                return
            first_btn = self.buttons_db[0][0]["name"]
            self.bot.send_message(
                message.chat.id,
                f"🛠 پنل ادمین - مدیریت دکمه‌ها: {first_btn}",
                reply_markup=self.admin_panel(first_btn)
            )

        # -------- نمایش پنل کاربران بر اساس آیدی --------
        @self.bot.message_handler(func=lambda m: True)
        def show_user_panel(message):
            text = message.text.strip()
            if not text:
                return  # اگر خالی بود، هیچی نشون نده
            self.bot.send_message(
                message.chat.id,
                "📖 پنل راهنمای ربات ⦁ Self Nix:",
                reply_markup=self.main_panel(message.from_user.id)
            )

        # -------- Callback --------
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            data = call.data
            click_user = call.from_user.id

            # ----- بازگشت پنل ادمین -----
            if data == "back_admin" and click_user == OWNER_ID:
                if call.message:
                    self.bot.edit_message_text(
                        "📖 پنل راهنمای ربات ⦁ Self Nix:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=None
                    )
                return

            # ----- عملیات ادمین -----
            if click_user == OWNER_ID:
                # حذف دکمه
                if data.startswith("remove_"):
                    name = data.replace("remove_", "")
                    for row in self.buttons_db:
                        row[:] = [b for b in row if b["name"] != name]
                    self.buttons_db = [r for r in self.buttons_db if r]
                    self.save_buttons()
                    self.bot.answer_callback_query(call.id, "دکمه حذف شد ✅")
                    if self.buttons_db:
                        first_btn = self.buttons_db[0][0]["name"]
                        if call.message:
                            self.bot.edit_message_text(
                                f"🛠 پنل ادمین - مدیریت دکمه‌ها: {first_btn}",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=self.admin_panel(first_btn)
                            )
                    else:
                        if call.message:
                            self.bot.edit_message_text(
                                "📖 پنل راهنمای ربات ⦁ Self Nix:",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=None
                            )
                    return

                # جابجایی دکمه‌ها
                if data.startswith("move_"):
                    parts = data.split("_", 2)
                    direction, btn_name = parts[1], parts[2]

                    row_idx = col_idx = -1
                    for i, row in enumerate(self.buttons_db):
                        for j, b in enumerate(row):
                            if b["name"] == btn_name:
                                row_idx, col_idx = i, j
                                break
                        if row_idx != -1:
                            break

                    if row_idx == -1: return

                    # جابجایی عمودی
                    if direction == "up" and row_idx > 0:
                        self.buttons_db[row_idx], self.buttons_db[row_idx-1] = self.buttons_db[row_idx-1], self.buttons_db[row_idx]
                    elif direction == "down" and row_idx < len(self.buttons_db)-1:
                        self.buttons_db[row_idx], self.buttons_db[row_idx+1] = self.buttons_db[row_idx+1], self.buttons_db[row_idx]

                    # جابجایی افقی
                    elif direction == "left" and col_idx > 0:
                        self.buttons_db[row_idx][col_idx], self.buttons_db[row_idx][col_idx-1] = self.buttons_db[row_idx][col_idx-1], self.buttons_db[row_idx][col_idx]
                    elif direction == "right" and col_idx < len(self.buttons_db[row_idx])-1:
                        self.buttons_db[row_idx][col_idx], self.buttons_db[row_idx][col_idx+1] = self.buttons_db[row_idx][col_idx+1], self.buttons_db[row_idx][col_idx]

                    self.save_buttons()
                    if call.message:
                        self.bot.edit_message_reply_markup(
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=self.admin_panel(btn_name)
                        )
                    return

            # ----- نمایش دکمه کاربران -----
            if data.startswith("btn_"):
                _, owner_id, name = data.split("_", 2)
                owner_id = int(owner_id)
                text = "یافت نشد"
                for row in self.buttons_db:
                    for b in row:
                        if b["name"] == name:
                            text = b.get("text", "یافت نشد")
                            break
                if call.inline_message_id:
                    self.bot.edit_message_text(
                        text,
                        inline_message_id=call.inline_message_id,
                        reply_markup=self.back_panel(owner_id)
                    )
                elif call.message:
                    self.bot.edit_message_text(
                        text,
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=self.back_panel(owner_id)
                    )

print("PanelManager ready")
