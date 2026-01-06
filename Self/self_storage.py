# ================================================================
# self_storage_mongo.py — دیتابیس MongoDB سبک و کامل
# نسخه کامل | سازگار با db.data | پشتیبانی چند اکانت
# ================================================================

from pymongo import MongoClient
import json

class Storage:
    def __init__(self, account_name="default"):
        """
        account_name: برای هر اکانت یک دیتابیس جداگانه
        """
        self.MONGO_URI = "mongodb://jinx:titi_jinx@ac-yjpvg6o-shard-00-00.35gzto0.mongodb.net:27017,ac-yjpvg6o-shard-00-01.35gzto0.mongodb.net:27017,ac-yjpvg6o-shard-00-02.35gzto0.mongodb.net:27017/?replicaSet=atlas-fzmhnh-shard-0&ssl=true&authSource=admin"
        self.client = MongoClient(self.MONGO_URI)
        self.db = self.client[f"selfbot_{account_name}"]  # دیتابیس جداگانه برای هر اکانت
        self.users_col = self.db["users"]
        self.groups_col = self.db["groups"]
        self.status_col = self.db["bot_status"]

        # سازگار با db.data
        self.data = {
            "users": self._load_all_users(),
            "groups": self._load_all_groups(),
            "bot_status": self._load_all_status()
        }

    # ================================
    # کاربران
    # ================================
    def _user(self, user_id):
        user_id = str(user_id)
        user = self.users_col.find_one({"user_id": user_id})
        if user:
            try:
                return json.loads(user["data"])
            except:
                return {}
        else:
            default = {
                "clock": {"timezone": "Asia/Tehran", "bio_enabled": False, "name_enabled": False, "font_id": None},
                "silence": {"is_silenced": False, "expire_time": 0, "reason": ""},
                "block": {"is_blocked": False},
                "welcome": {"enabled": False, "message": ""},
                "status": {"online": True},
                "warnings": 0
            }
            self.users_col.insert_one({"user_id": user_id, "data": json.dumps(default)})
            self._refresh_data()
            return default

    def get_user_key(self, user_id, section, key):
        user = self._user(user_id)
        return user.get(section, {}).get(key)

    def set_user_key(self, user_id, section, key, value):
        user = self._user(user_id)
        if section not in user:
            user[section] = {}
        user[section][key] = value
        self.users_col.update_one({"user_id": str(user_id)}, {"$set": {"data": json.dumps(user)}}, upsert=True)
        self._refresh_data()

    def increase_warning(self, user_id):
        user = self._user(user_id)
        user["warnings"] = user.get("warnings", 0) + 1
        self.users_col.update_one({"user_id": str(user_id)}, {"$set": {"data": json.dumps(user)}}, upsert=True)
        self._refresh_data()
        return user["warnings"]

    # ================================
    # گروه‌ها
    # ================================
    def _group(self, chat_id):
        chat_id = str(chat_id)
        group = self.groups_col.find_one({"chat_id": chat_id})
        if group:
            try:
                return json.loads(group["data"])
            except:
                return {}
        else:
            default = {
                "welcome_enabled": False,
                "welcome_message": "",
                "muted_users": [],
                "blocked_users": [],
                "settings": {"max_warnings": 8, "auto_mute_time": 60}
            }
            self.groups_col.insert_one({"chat_id": chat_id, "data": json.dumps(default)})
            self._refresh_data()
            return default

    def get_group_key(self, chat_id, key):
        group = self._group(chat_id)
        return group.get(key)

    def set_group_key(self, chat_id, key, value):
        group = self._group(chat_id)
        group[key] = value
        self.groups_col.update_one({"chat_id": str(chat_id)}, {"$set": {"data": json.dumps(group)}}, upsert=True)
        self._refresh_data()

    def add_muted_user(self, chat_id, user_id):
        group = self._group(chat_id)
        if user_id not in group["muted_users"]:
            group["muted_users"].append(user_id)
        self.groups_col.update_one({"chat_id": str(chat_id)}, {"$set": {"data": json.dumps(group)}}, upsert=True)
        self._refresh_data()

    # ================================
    # وضعیت بات
    # ================================
    def get_bot_status(self, key):
        status = self.status_col.find_one({"key": key})
        return status["value"] if status else None

    def set_bot_status(self, key, value):
        self.status_col.update_one({"key": key}, {"$set": {"value": str(value)}}, upsert=True)
        self._refresh_data()

    # ================================
    # لود کل داده‌ها
    # ================================
    def _load_all_users(self):
        result = {}
        for doc in self.users_col.find({}):
            try:
                result[doc["user_id"]] = json.loads(doc["data"])
            except:
                result[doc["user_id"]] = {}
        return result

    def _load_all_groups(self):
        result = {}
        for doc in self.groups_col.find({}):
            try:
                result[doc["chat_id"]] = json.loads(doc["data"])
            except:
                result[doc["chat_id"]] = {}
        return result

    def _load_all_status(self):
        result = {}
        for doc in self.status_col.find({}):
            result[doc["key"]] = doc["value"]
        return result

    def _refresh_data(self):
        """آپدیت data برای سازگاری با db.data"""
        self.data["users"] = self._load_all_users()
        self.data["groups"] = self._load_all_groups()
        self.data["bot_status"] = self._load_all_status()
