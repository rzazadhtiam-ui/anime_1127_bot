import telebot
from telebot import types
from pymongo import MongoClient
import certifi

MAIN_TEXT = "📖  ⦁ Self Nix پنل راهنما ربات  :"
OWNER_ID = 8588914809

# ================= Mongo =================
mongo_uri = "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@" \
            "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017" \
            "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"

client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client["self_panel_db"]
buttons_col = db["buttons"]

buttons_col.create_index("name", unique=True)


class PanelManager:

    def __init__(self, bot):
        self.bot = bot
        self.waiting_position = {}
        self.history = {}

        self.register_handlers()

    # ---------- گرفتن دکمه ----------
    def get_button(self, name):
        return buttons_col.find_one({"name": name})

    # ---------- ساخت پنل ----------
    def main_panel(self, user_id, show_back=False):

        markup = types.InlineKeyboardMarkup()
        rows = {}

        buttons = list(buttons_col.find())

        for btn in buttons:
            r = btn.get("row", 0)
            rows.setdefault(r, []).append(btn)

        for r in sorted(rows.keys()):
            sorted_cols = sorted(rows[r], key=lambda x: x.get("col", 0))

            markup.row(*[
                types.InlineKeyboardButton(
                    b["name"],
                    callback_data=f"btn_{user_id}_{b['name']}"
                )
                for b in sorted_cols
            ])

        if show_back:
            markup.row(
                types.InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data=f"back_{user_id}"
                )
            )

        return markup

    # ---------- فقط بازگشت ----------
    def back_only_panel(self, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data=f"back_{user_id}"
            )
        )
        return markup

    # ---------- پنل حذف ----------
    def remove_panel(self):
        markup = types.InlineKeyboardMarkup()

        for btn in buttons_col.find():
            markup.add(
                types.InlineKeyboardButton(
                    f"❌ {btn['name']}",
                    callback_data=f"remove_{btn['name']}"
                )
            )

        return markup

    # ---------- پنل ادمین ----------
    def admin_panel(self):
        markup = types.InlineKeyboardMarkup()

        for btn in buttons_col.find():
            markup.add(
                types.InlineKeyboardButton(
                    f"{btn['name']} ({btn.get('row',0)},{btn.get('col',0)})",
                    callback_data=f"editpos_{btn['name']}"
                )
            )

        return markup

    # ---------- ادیت امن ----------
    def safe_edit(self, call, text, markup):
        try:
            if call.inline_message_id:
                self.bot.edit_message_text(
                    text,
                    inline_message_id=call.inline_message_id,
                    reply_markup=markup
                )
            else:
                self.bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )
        except:
            pass

    # ---------- ثبت هندلر ----------
    def register_handlers(self):

        # ===== افزودن =====
        @self.bot.message_handler(commands=['add'])
        def add_button(message):

            if message.from_user.id != OWNER_ID:
                return

            msg = self.bot.send_message(message.chat.id, "اسم دکمه را بفرست")

            def get_name(m):
                name = m.text.strip()

                msg2 = self.bot.send_message(m.chat.id, "متن دکمه را بفرست")

                def get_text(t):
                    try:
                        buttons_col.insert_one({
                            "name": name,
                            "text": t.text,
                            "row": 0,
                            "col": buttons_col.count_documents({})
                        })
                        self.bot.send_message(t.chat.id, "✅ اضافه شد")
                    except:
                        self.bot.send_message(t.chat.id, "❌ دکمه با این نام وجود دارد")

                self.bot.register_next_step_handler(msg2, get_text)

            self.bot.register_next_step_handler(msg, get_name)

        # ===== حذف =====
        @self.bot.message_handler(commands=['remov'])
        def remove_cmd(message):

            if message.from_user.id != OWNER_ID:
                return

            if buttons_col.count_documents({}) == 0:
                self.bot.send_message(message.chat.id, "هیچ دکمه‌ای نیست")
                return

            self.bot.send_message(
                message.chat.id,
                "کدام دکمه حذف شود؟",
                reply_markup=self.remove_panel()
            )

        # ===== پنل ادمین =====
        @self.bot.message_handler(commands=['panel_admin'])
        def admin_cmd(message):

            if message.from_user.id != OWNER_ID:
                return

            self.bot.send_message(
                message.chat.id,
                "یک دکمه انتخاب کن و مختصات بده\nمثال: 1 2",
                reply_markup=self.admin_panel()
            )

        # ===== INLINE =====
        @self.bot.inline_handler(func=lambda q: True)
        def inline_handler(q):

            uid = q.from_user.id
            self.history[uid] = [MAIN_TEXT]

            result = types.InlineQueryResultArticle(
                id="panel",
                title="📋 پنل سلف",
                input_message_content=types.InputTextMessageContent(MAIN_TEXT),
                reply_markup=self.main_panel(uid)
            )

            self.bot.answer_inline_query(q.id, [result], cache_time=0)

        # ===== CALLBACK =====
        @self.bot.callback_query_handler(func=lambda c: c.data.startswith(("btn_", "remove_", "editpos_", "back_")))
        def callback(call):

            data = call.data
            uid = call.from_user.id

            # ---------- ورود دکمه ----------
            if data.startswith("btn_"):

                _, owner_id, name = data.split("_", 2)

                if int(owner_id) != uid:
                    return

                btn = self.get_button(name)
                if not btn:
                    return

                self.history.setdefault(uid, []).append(btn["text"])

                self.safe_edit(call, btn["text"], self.back_only_panel(uid))

            # ---------- بازگشت ----------
            elif data.startswith("back_"):

                if len(self.history.get(uid, [])) <= 1:
                    self.safe_edit(call, MAIN_TEXT, self.main_panel(uid))
                    return

                self.history[uid].pop()
                last = self.history[uid][-1]

                self.safe_edit(
                    call,
                    last,
                    self.main_panel(uid, len(self.history[uid]) > 1)
                )

            # ---------- حذف ----------
            elif data.startswith("remove_"):

                if uid != OWNER_ID:
                    return

                name = data.replace("remove_", "")

                buttons_col.delete_one({"name": name})

                self.bot.answer_callback_query(call.id, "حذف شد")

                if buttons_col.count_documents({}) > 0:
                    self.bot.edit_message_reply_markup(
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=self.remove_panel()
                    )
                else:
                    self.bot.edit_message_text(
                        "همه دکمه‌ها حذف شدند",
                        call.message.chat.id,
                        call.message.message_id
                    )

            # ---------- تغییر موقعیت ----------
            elif data.startswith("editpos_"):

                if uid != OWNER_ID:
                    return

                name = data.replace("editpos_", "")
                self.waiting_position[uid] = name

                msg = self.bot.send_message(
                    call.message.chat.id,
                    f"مختصات جدید {name} بده\nمثال: 1 2"
                )

                self.bot.register_next_step_handler(msg, self.set_position)

    # ---------- ثبت مختصات ----------
    def set_position(self, message):

        uid = message.from_user.id

        if uid not in self.waiting_position:
            return

        name = self.waiting_position.pop(uid)

        try:
            row, col = map(int, message.text.split())

            buttons_col.update_one(
                {"name": name},
                {"$set": {"row": row, "col": col}}
            )

            self.bot.send_message(message.chat.id, "✅ جابه‌جا شد")

        except:
            self.bot.send_message(message.chat.id, "فرمت اشتباه")