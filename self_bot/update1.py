import telebot
from telebot import types
from pymongo import MongoClient
import certifi
import threading
import time
import uuid
MAIN_TEXT = "📖  ⦁ Self Nix پنل راهنما ربات  :"
OWNER_ID = 6433381392
PANEL_TIMEOUT = 180  # ثانیه = ۳ دقیقه

# ================= Mongo =================
mongo_uri = "mongodb://strawhatmusicdb_db_user:db_strawhatmusic@" \
            "ac-hw2zgfj-shard-00-00.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-01.morh5s8.mongodb.net:27017," \
            "ac-hw2zgfj-shard-00-02.morh5s8.mongodb.net:27017" \
            "?replicaSet=atlas-7m1dmi-shard-0&ssl=true&authSource=admin"

client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client["self_panel_db"]
buttons_col = db["buttons"]
buttons_col.create_index("name")


class PanelManager:

    def __init__(self, bot):
        self.bot = bot
        self.waiting_position = {}
        self.pending_panel = {}
        self.history = {}
        self.ROOT = "root"

        # ── تایمر: {uid: {"timer": Timer, "inline_id": str, "chat_id": int, "msg_id": int}}
        self._timers = {}

        self.register_handlers()

    # ========================================================
    #  تایمر بی‌فعالیت
    # ========================================================

    def _reset_timer(self, uid: int, call):
        """هر بار که کاربر روی پنل کلیک می‌کند تایمر ریست می‌شود."""
        self._cancel_timer(uid)

        inline_id = getattr(call, "inline_message_id", None)
        chat_id   = call.message.chat.id if not inline_id else None
        msg_id    = call.message.message_id if not inline_id else None

        def _expire():
            self._close_panel(
                uid,
                inline_id=inline_id,
                chat_id=chat_id,
                msg_id=msg_id,
                reason="timeout"
            )

        t = threading.Timer(PANEL_TIMEOUT, _expire)
        t.daemon = True
        t.start()
        self._timers[uid] = t

    def _cancel_timer(self, uid: int):
        if uid in self._timers:
            self._timers.pop(uid).cancel()

    def _close_panel(self, uid: int, *, inline_id=None, chat_id=None, msg_id=None, reason="manual"):
        """پنل را می‌بندد؛ reason: 'manual' یا 'timeout'."""
        self._cancel_timer(uid)
        self.history.pop(uid, None)

        if reason == "timeout":
            text = "⏱ <b>پنل به دلیل عدم فعالیت بسته شد</b>"
        else:
            text = "✅ <b>پنل با موفقیت بسته شد</b>"

        try:
            if inline_id:
                self.bot.edit_message_text(
                    text,
                    inline_message_id=inline_id,
                    parse_mode="HTML"
                )
            elif chat_id and msg_id:
                self.bot.edit_message_text(
                    text,
                    chat_id,
                    msg_id,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"close_panel error: {e}")

    # ========================================================
    #  سازنده markup ها
    # ========================================================

    def _green_btn(self, label: str, cb: str) -> types.InlineKeyboardButton:
        """دکمه سبز — تلگرام با ایموجی 🟢 پس‌زمینه سبز نمی‌دهد؛
        بهترین راه قابل‌اعتماد روی همه کلاینت‌ها استفاده از
        InlineKeyboardButton با text خالص + web_app یا url نیست.
        تنها گزینه واقعی برای رنگ کامل دکمه، استفاده از
        login_url / pay است که اینجا کاربرد ندارد.
        پس متن دکمه را با نشانه‌ی سبز می‌سازیم تا کاملاً سبز به‌نظر برسد."""
        return types.InlineKeyboardButton(f" {label}", callback_data=cb)


    def build_panel_markup(self, user_id: int, parent: str, show_back=False):
        """ساخت markup با رعایت row/col برای همه سطوح (root و پنل‌های سطح ۱)"""
        markup = types.InlineKeyboardMarkup()

        buttons = list(buttons_col.find({"parent": parent}))

        grid = {}

        for btn in buttons:
            r = int(btn.get("row", 0))
            c = int(btn.get("col", 0))

            grid.setdefault(r, {})[c] = types.InlineKeyboardButton(
                btn["name"],
                callback_data=f"open_{user_id}_{btn['name']}_{parent}"
            )

        # ساخت ردیف‌ها بر اساس grid
        for r in sorted(grid.keys()):
            row_buttons = []
            for c in sorted(grid[r].keys()):
                row_buttons.append(grid[r][c])

            if row_buttons:
                markup.row(*row_buttons)

        if show_back and parent != "root":
            markup.add(
                self._green_btn("بازگشت", f"back_{user_id}_{parent}")
            )

        if parent == "root":
            markup.add(
                types.InlineKeyboardButton(
                    "❌ بستن پنل",
                    callback_data=f"close_{user_id}"
                )
            )

        return markup

    def main_panel(self, user_id, parent="root", show_back=False):
        return self.build_panel_markup(user_id, parent, show_back)

    def back_only_panel(self, user_id, parent="root"):
        markup = types.InlineKeyboardMarkup()
        markup.row(self._green_btn("بازگشت", f"back_{user_id}_{parent}"))
        return markup

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

    def admin_panel(self):
        markup = types.InlineKeyboardMarkup()

        for btn in buttons_col.find():
            markup.add(
    types.InlineKeyboardButton(
        f"{btn['name']} | {btn['type']}",
        callback_data=f"edit_menu||{btn['_id']}"
    )
)

        return markup

    # ========================================================
    #  ابزارها
    # ========================================================

    def safe_edit(self, call, text, markup):
        try:
            if getattr(call, "inline_message_id", None):
                self.bot.edit_message_text(
                    text,
                    inline_message_id=call.inline_message_id,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                self.bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(e)

    def safe_answer(self, call, text="done"):
        try:
            self.bot.answer_callback_query(call.id, text)
        except:
            pass

    # ========================================================
    #  ثبت هندلرها
    # ========================================================

    def register_handlers(self):

        # ===== /add =====
        @self.bot.message_handler(commands=['add'])
        def add_button(message):
            if message.from_user.id != OWNER_ID:
                return

            msg = self.bot.send_message(message.chat.id, "اسم دکمه را بفرست:")

            def get_name(m):
                name = m.text.strip()

                step_msg = self.bot.send_message(
                    m.chat.id,
                    "نوع دکمه را انتخاب کن:\n"
                    "1 = panel  (زیرمنو — سطح ۱)\n"
                    "2 = text_panel  (متن — سطح ۲)"
                )

                def get_type(t):
                    ttype = t.text.strip()

                    # ---------- TEXT PANEL (سطح ۲) ----------
                    if ttype == "2":
                        # نمایش پنل‌های سطح ۱ برای انتخاب والد
                        panels = list(buttons_col.find({"type": "panel"}))

                        if not panels:
                            self.bot.send_message(
                                t.chat.id,
                                "⚠️ ابتدا باید یک دکمه panel (سطح ۱) بسازی.\n"
                                "دکمه text_panel باید زیر یک panel قرار بگیرد."
                            )
                            return

                        markup = types.InlineKeyboardMarkup()
                        for p in panels:
                            markup.add(
                                types.InlineKeyboardButton(
                                    f"📁 {p['name']}",
                                    callback_data=f"set_textparent||{name}||{p['name']}"
                                )
                            )

                        self.bot.send_message(
                            t.chat.id,
                            f"دکمه «{name}» زیر کدام پنل (سطح ۱) قرار بگیرد؟",
                            reply_markup=markup
                        )
                        return

                    # ---------- PANEL (سطح ۱) ----------
                    panels = list(buttons_col.find({"type": "panel"}))

                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton(
                            "📁 root  (پنل اصلی)",
                            callback_data=f"set_parent||{name}||root"
                        )
                    )
                    for p in panels:
                        markup.add(
                            types.InlineKeyboardButton(
                                p["name"],
                                callback_data=f"set_parent||{name}||{p['name']}"
                            )
                        )

                    self.bot.send_message(
                        t.chat.id,
                        "این پنل زیر کدام پنل ساخته شود؟",
                        reply_markup=markup
                    )

                self.bot.register_next_step_handler(step_msg, get_type)

            self.bot.register_next_step_handler(msg, get_name)

        # ===== /remove =====
        @self.bot.message_handler(commands=['remove'])
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

        # ===== /panel_admin =====
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
        @self.bot.inline_handler(func=lambda q: q.query and q.query.strip() == "self-nix-panel-tjm")
        def inline_handler(q):
            uid = q.from_user.id
            self.history[uid] = ["root"]

            result = types.InlineQueryResultArticle(
                id="panel",
                title="📋 پنل سلف",
                input_message_content=types.InputTextMessageContent(
                    MAIN_TEXT,
                    parse_mode="HTML"
                ),
                reply_markup=self.main_panel(uid, parent="root")
            )

            self.bot.answer_inline_query(q.id, [result], cache_time=0)

        # ===== CALLBACK =====
        @self.bot.callback_query_handler(
            func=lambda c: c.data.startswith((
    "open_", "delete||",
    "edit_menu||", "rename||",
    "edit_text||", "move||",
    "move_pos||", "set_parent||",
    "set_textparent||", "set_new_parent||",
    "back_", "close_"
))
        )
        def callback(call):
            data = call.data
            uid  = call.from_user.id

            # ---------- open ----------
            if data.startswith("open_"):
                _, owner_id, name, parent = data.split("_", 3)

                if int(owner_id) != uid:
                    return
                            

                btn = buttons_col.find_one({
            "name": name,
            "parent": parent
        })

                if not btn:
                    self.safe_answer(call, "not found")
                    return

                self._reset_timer(uid, call)

                if btn.get("type") != "panel":
                    self.history.setdefault(uid, []).append(name)
                    # سطح ۲: نمایش متن + دکمه بازگشت سبز
                    self.safe_edit(
                        call,
                        btn.get("text", ""),
                        self.back_only_panel(uid, parent)
                    )
                    return

                # سطح ۱: نمایش زیردکمه‌ها با رعایت row/col (بار اول هم درست)
                self.history.setdefault(uid, []).append(name)

                markup = self.build_panel_markup(uid, parent=name, show_back=True)

                # اگر پنل خالی بود
                if not buttons_col.find_one({"parent": name}):
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📭 خالی", callback_data="noop"))
                    markup.add(self._green_btn("بازگشت", f"back_{uid}_{name}"))

                text_to_show = btn.get("text") or f"📂 {name}"

                self.safe_edit(call, text_to_show, markup)

            # ---------- back ----------
            elif data.startswith("back_"):
                _, uid_str, parent = data.split("_", 2)
                uid = int(uid_str)

                if uid != call.from_user.id:
                    return

                self._reset_timer(uid, call)

                hist = self.history.get(uid, ["root"])

                if len(hist) <= 1:
                    self.safe_edit(call, MAIN_TEXT, self.main_panel(uid, "root"))
                    return

                hist.pop()
                last = hist[-1]
                self.history[uid] = hist

                self.safe_edit(
                    call,
                    MAIN_TEXT,
                    self.main_panel(uid, last, show_back=(last != "root"))
                )

            # ---------- remove ----------
            

            elif data.startswith("delete||"):
                if uid != OWNER_ID:
                    return
    
                btn_id = data.split("||")[1]

                buttons_col.delete_one({"_id": btn_id})

                self.safe_answer(call, "حذف شد")
                self.safe_edit(call, MAIN_TEXT, self.admin_panel())

            # ---------- editpos ----------
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

            # ---------- set_parent (panel سطح ۱) ----------
            elif data.startswith("set_parent||"):
                parts  = data.split("||")
                name   = parts[1]
                parent = parts[2]

                if parent == name:
                    parent = "root"

                buttons_col.update_one(
    {"name": name},
    {"$set": {"parent": parent}}
)

                self.safe_answer(call, "✅ ساخته شد")
                self.safe_edit(call, MAIN_TEXT, self.main_panel(uid, "root"))

            # ---------- set_textparent (text_panel سطح ۲ — انتخاب والد) ----------
            elif data.startswith("set_textparent||"):
                parts       = data.split("||")
                name        = parts[1]
                parent_name = parts[2]

                # حالا متن را می‌خواهیم
                msg = self.bot.send_message(
                    call.message.chat.id,
                    f"متن نمایشی دکمه «{name}» را بفرست:"
                )

                def save_text_panel(txt):
                    buttons_col.insert_one({
    "_id": str(uuid.uuid4()),
    "name": name,
    "parent": parent_name,
    "type": "text_panel",
    "text": txt.text,
    "row": 0,
    "col": 0
})
                    self.bot.send_message(txt.chat.id, f"✅ دکمه «{name}» زیر «{parent_name}» ساخته شد")

                self.bot.register_next_step_handler(msg, save_text_panel)
                self.safe_answer(call, "متن را بفرست")

            # ---------- close ----------
            elif data.startswith("close_"):
                inline_id = getattr(call, "inline_message_id", None)
                chat_id   = call.message.chat.id if not inline_id else None
                msg_id    = call.message.message_id if not inline_id else None

                self._close_panel(
                    uid,
                    inline_id=inline_id,
                    chat_id=chat_id,
                    msg_id=msg_id,
                    reason="manual"
                )

            elif data.startswith("edit_menu||"):
                if uid != OWNER_ID:
                    return

                btn_id = data.split("||")[1]
                btn = buttons_col.find_one({"_id": btn_id})

                markup = types.InlineKeyboardMarkup()

                markup.add(types.InlineKeyboardButton(
        "✏️ تغییر نام",
        callback_data=f"rename||{btn_id}"
    ))

                markup.add(types.InlineKeyboardButton(
        "📝 تغییر متن",
        callback_data=f"edit_text||{btn_id}"
    ))

                markup.add(types.InlineKeyboardButton(
        "📂 تغییر والد (جابجایی)",
        callback_data=f"move||{btn_id}"
    ))

                markup.add(types.InlineKeyboardButton(
        "📍 تغییر مختصات",
        callback_data=f"move_pos||{btn_id}"
    ))

                markup.add(types.InlineKeyboardButton(
        "🗑 حذف",
        callback_data=f"delete||{btn_id}"
    ))

                self.safe_edit(call, "⚙️ ویرایش دکمه:", markup)

            elif data.startswith("rename||"):
                btn_id = data.split("||")[1]

                msg = self.bot.send_message(call.message.chat.id, "نام جدید:")

                def save(m):
                    buttons_col.update_one(
            {"_id": btn_id},
            {"$set": {"name": m.text}}
        )
                    self.bot.send_message(m.chat.id, "✅ تغییر کرد")

                self.bot.register_next_step_handler(msg, save)

            elif data.startswith("edit_text||"):
                btn_id = data.split("||")[1]

                msg = self.bot.send_message(call.message.chat.id, "متن جدید:")

                def save(m):
                    buttons_col.update_one(
            {"_id": btn_id},
            {"$set": {"text": m.text}}
        )
                    self.bot.send_message(m.chat.id, "✅ متن آپدیت شد")

                self.bot.register_next_step_handler(msg, save)

            elif data.startswith("move||"):
                btn_id = data.split("||")[1]

                panels = list(buttons_col.find({"type": "panel"}))

                markup = types.InlineKeyboardMarkup()

                for p in panels:
                    markup.add(types.InlineKeyboardButton(
            p["name"],
            callback_data=f"set_new_parent||{btn_id}||{p['_id']}"
        ))

                markup.add(types.InlineKeyboardButton(
        "root",
        callback_data=f"set_new_parent||{btn_id}||root"
    ))

                self.safe_edit(call, "انتخاب پنل جدید:", markup)

            elif data.startswith("set_new_parent||"):
                _, btn_id, parent_id = data.split("||")

                buttons_col.update_one(
        {"_id": btn_id},
        {"$set": {"parent": parent_id}}
    )

                self.safe_answer(call, "منتقل شد")

    # ========================================================
    #  ثبت مختصات
    # ========================================================

    def set_position(self, message):
        uid = message.from_user.id

        if uid not in self.waiting_position:
            return

        btn_id = self.waiting_position.pop(uid)

        try:
            row, col = map(int, message.text.split())

            buttons_col.update_one(
            {"_id": btn_id},
            {"$set": {"row": row, "col": col}}
        )

            self.bot.send_message(message.chat.id, "✅ جابه‌جا شد")

        except:
            self.bot.send_message(message.chat.id, "فرمت اشتباه")
