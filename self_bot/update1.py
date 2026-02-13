import telebot
from telebot import types
import uuid
import json
import os

OWNER_ID = 8588914809
DB_FILE = "buttons.json"

class PanelManager:
    def __init__(self, bot: telebot.TeleBot):
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
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ---------------- پنل اصلی ----------------
    def main_panel(self, user_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for btn_name in self.buttons_db:
            if btn_name.strip():
                markup.add(types.InlineKeyboardButton(
                    btn_name,
                    callback_data=f"btn_{user_id}_{btn_name}"
                ))
        return markup

    # ---------------- پنل بازگشت ----------------
    def back_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data=f"back_{user_id}"
        ))
        return markup

    # ---------------- پنل حذف ----------------
    def remove_panel(self):
        if not self.buttons_db:
            return None
        markup = types.InlineKeyboardMarkup(row_width=2)
        for btn_name in self.buttons_db:
            markup.add(types.InlineKeyboardButton(
                f"❌ {btn_name}",
                callback_data=f"remove_{btn_name}"
            ))
        return markup

    # ---------------- پنل ادمین ----------------
    def admin_panel(self, btn_name):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬆️ بالا", callback_data=f"move_up_{btn_name}"),
            types.InlineKeyboardButton("⬇️ پایین", callback_data=f"move_down_{btn_name}"),
        )
        markup.add(
            types.InlineKeyboardButton("⬅️ چپ", callback_data=f"move_left_{btn_name}"),
            types.InlineKeyboardButton("➡️ راست", callback_data=f"move_right_{btn_name}")
        )
        markup.add(
            types.InlineKeyboardButton("❌ حذف", callback_data=f"remove_{btn_name}"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")
        )
        return markup

    # ================= ثبت handler =================
    def register_handlers(self):

        # -------- افزودن دکمه --------
        @self.bot.message_handler(commands=['add'])
        def add_button_start(message):
            if message.from_user.id != OWNER_ID: return
            self.bot.send_message(message.chat.id, "اسم دکمه را بفرست")
            self.user_state[message.from_user.id] = "wait_name"

        @self.bot.message_handler(func=lambda m: True)
        def add_button_process(message):
            if message.from_user.id != OWNER_ID: return
            uid = message.from_user.id

            if self.user_state.get(uid) == "wait_name":
                if not message.text or not message.text.strip():
                    self.bot.reply_to(message, "اسم خالی مجاز نیست")
                    return
                self.temp_button[uid] = {"name": message.text.strip()}
                self.user_state[uid] = "wait_text"
                self.bot.send_message(message.chat.id, "متن دکمه را بفرست")
                return

            if self.user_state.get(uid) == "wait_text":
                name = self.temp_button[uid]["name"]
                self.buttons_db[name] = message.text
                self.save_buttons()
                self.user_state.pop(uid)
                self.temp_button.pop(uid)
                self.bot.send_message(message.chat.id, "✅ دکمه اضافه شد")

        # -------- حذف دکمه --------
        @self.bot.message_handler(commands=['remov'])
        def remove_button(message):
            if message.from_user.id != OWNER_ID: return
            if not self.buttons_db:
                self.bot.send_message(message.chat.id, "هیچ دکمه‌ای وجود ندارد")
                return
            panel = self.remove_panel()
            self.bot.send_message(
                message.chat.id,
                "روی دکمه‌ای که میخوای حذف بشه بزن",
                reply_markup=panel
            )

        # -------- Inline Query --------
        @self.bot.inline_handler(func=lambda q: True)
        def inline_handler(q):
            user_id = q.from_user.id
            result = types.InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="📋پنل ربات ⦁ Self Nix",
                input_message_content=types.InputTextMessageContent("📖پنل راهنما ربات ⦁ Self Nix:"),
                reply_markup=self.main_panel(user_id)
            )
            self.bot.answer_inline_query(q.id, [result], cache_time=0)

        # -------- Callback --------
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            data = call.data
            click_user = call.from_user.id

            # ===== نمایش دکمه (ادمین و کاربر) =====
            if data.startswith("btn_"):
                _, owner_id, name = data.split("_", 2)
                owner_id = int(owner_id)
                if click_user == OWNER_ID:
                    if call.message:
                        self.bot.edit_message_text(
                            f"🛠 مدیریت دکمه: {name}",
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=self.admin_panel(name)
                        )
                else:
                    if owner_id != click_user:
                        self.bot.answer_callback_query(
                            call.id,
                            "❌ این پنل برای شما نیست",
                            show_alert=True
                        )
                        return
                    text = self.buttons_db.get(name, "یافت نشد")
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

            # ===== بازگشت =====
            elif data.startswith("back_"):
                owner_id = int(data.split("_")[1])
                if owner_id != click_user:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ این پنل برای شما نیست",
                        show_alert=True
                    )
                    return
                if call.inline_message_id:
                    self.bot.edit_message_text(
                        "پنل شما",
                        inline_message_id=call.inline_message_id,
                        reply_markup=self.main_panel(owner_id)
                    )
                elif call.message:
                    self.bot.edit_message_text(
                        "پنل شما",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=self.main_panel(owner_id)
                    )
            elif data == "back_admin" and click_user == OWNER_ID:
                if call.message:
                    self.bot.edit_message_text(
                        "پنل مدیریت دکمه‌ها",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=self.remove_panel()
                    )

            # ===== حذف دکمه =====
            elif data.startswith("remove_"):
                if click_user != OWNER_ID: return
                name = data.replace("remove_", "")
                if name in self.buttons_db:
                    del self.buttons_db[name]
                    self.save_buttons()
                    self.bot.answer_callback_query(call.id, "دکمه حذف شد ✅")
                    panel = self.remove_panel()
                    if call.message:
                        if panel:
                            self.bot.edit_message_reply_markup(
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=panel
                            )
                        else:
                            self.bot.edit_message_text(
                                "همه دکمه‌ها حذف شدند",
                                call.message.chat.id,
                                call.message.message_id
                            )

            # ===== جابه‌جایی دکمه (ادمین) =====
            elif data.startswith("move_") and click_user == OWNER_ID:
                parts = data.split("_", 2)
                direction, btn_name = parts[1], parts[2]

                keys = list(self.buttons_db.keys())
                index = keys.index(btn_name)

                if direction in ["up", "left"] and index > 0:
                    keys[index], keys[index-1] = keys[index-1], keys[index]
                elif direction in ["down", "right"] and index < len(keys)-1:
                    keys[index], keys[index+1] = keys[index+1], keys[index]

                # بازسازی دیکشنری با ترتیب جدید
                new_db = {k: self.buttons_db[k] for k in keys}
                self.buttons_db = new_db
                self.save_buttons()

                # بروزرسانی پیام ادمین
                if call.message:
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=self.admin_panel(btn_name)
                    )

print("PanelManager ready")
