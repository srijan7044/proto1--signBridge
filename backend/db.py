"""
backend/db.py

MongoDB connection manager for SignBridge with health monitoring
and safe in-memory fallback for local development.
"""

import logging
from backend.config import Config

logger = logging.getLogger("signbridge.db")

class InMemoryCursor(list):
    """List subclass that mimics PyMongo cursor.sort() signature."""
    def sort(self, key_or_list=None, direction=1, *args, **kwargs):
        if isinstance(key_or_list, str):
            key_field = key_or_list
            reverse = (direction == -1)
        elif isinstance(key_or_list, (list, tuple)) and key_or_list:
            first = key_or_list[0]
            if isinstance(first, (list, tuple)):
                key_field = first[0]
                reverse = (first[1] == -1)
            else:
                key_field = str(first)
                reverse = (direction == -1)
        else:
            return super().sort(*args, **kwargs)

        super().sort(key=lambda x: x.get(key_field, "") or "", reverse=reverse)
        return self


class InMemoryCollection:
    """Safe in-memory fallback collection when MongoDB is offline."""
    def __init__(self, name):
        self.name = name
        self._data = []

    def insert_one(self, doc):
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            import uuid
            doc_copy["_id"] = str(uuid.uuid4())
        self._data.append(doc_copy)
        class InsertResult:
            inserted_id = doc_copy["_id"]
        return InsertResult()

    def insert_many(self, docs, *args, **kwargs):
        inserted_ids = []
        for d in docs:
            res = self.insert_one(d)
            inserted_ids.append(res.inserted_id)
        class InsertManyResult:
            pass
        res = InsertManyResult()
        res.inserted_ids = inserted_ids
        return res

    def find_one(self, query=None):
        query = query or {}
        for item in self._data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return dict(item)
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        results = []
        for item in self._data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                res = dict(item)
                if projection and projection.get("_id") == 0:
                    res.pop("_id", None)
                results.append(res)
        return InMemoryCursor(results)

    def update_one(self, query, update, upsert=False):
        set_vals = update.get("$set", {})
        for idx, item in enumerate(self._data):
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                self._data[idx].update(set_vals)
                class UpdateResult:
                    matched_count = 1
                    modified_count = 1
                return UpdateResult()
        if upsert:
            new_doc = dict(query)
            new_doc.update(set_vals)
            self.insert_one(new_doc)
            class UpsertResult:
                matched_count = 0
                modified_count = 1
            return UpsertResult()
        class NoOpResult:
            matched_count = 0
            modified_count = 0
        return NoOpResult()

    def count_documents(self, query=None):
        if not query:
            return len(self._data)
        return len(self.find(query))


class InMemoryDatabase(dict):
    """Dictionary subclass that dynamically creates InMemoryCollections when accessed."""
    def __missing__(self, key):
        col = InMemoryCollection(key)
        self[key] = col
        return col


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_connected = False
        self._init_connection()

    def _init_connection(self):
        try:
            from pymongo import MongoClient
            self.client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=Config.MONGO_TIMEOUT_MS
            )
            # Test connection
            self.client.admin.command("ping")
            self.db = self.client[Config.MONGO_DB_NAME]
            self.is_connected = True
            logger.info(f"Connected to MongoDB database: {Config.MONGO_DB_NAME}")
        except Exception as e:
            self.is_connected = False
            logger.warning(
                f"MongoDB connection failed ({e}). Falling back to In-Memory mode."
            )
            self.db = InMemoryDatabase({
                "users": InMemoryCollection("users"),
                "gestures": InMemoryCollection("gestures"),
                "payments": InMemoryCollection("payments"),
                "conversations": InMemoryCollection("conversations"),
                "usage_sessions": InMemoryCollection("usage_sessions"),
                "monthly_usage": InMemoryCollection("monthly_usage"),
                "languages": InMemoryCollection("languages"),
                "custom_training_requests": InMemoryCollection("custom_training_requests"),
                "user_custom_models": InMemoryCollection("user_custom_models"),
                "custom_models": InMemoryCollection("custom_models"),
                "custom_model_samples": InMemoryCollection("custom_model_samples"),
                "training_payments": InMemoryCollection("training_payments"),
                "admin_action_logs": InMemoryCollection("admin_action_logs"),
            })

    @property
    def users(self):
        if self.is_connected:
            return self.db["users"]
        return self.db["users"]

    @property
    def gestures(self):
        if self.is_connected:
            return self.db["gestures"]
        return self.db["gestures"]

    @property
    def payments(self):
        if self.is_connected:
            return self.db["payments"]
        return self.db["payments"]

    @property
    def conversations(self):
        if self.is_connected:
            return self.db["conversations"]
        return self.db["conversations"]

    @property
    def usage_sessions(self):
        if self.is_connected:
            return self.db["usage_sessions"]
        return self.db["usage_sessions"]

    @property
    def monthly_usage(self):
        if self.is_connected:
            return self.db["monthly_usage"]
        return self.db["monthly_usage"]

    @property
    def languages(self):
        if self.is_connected:
            return self.db["languages"]
        return self.db["languages"]

    @property
    def custom_training_requests(self):
        if self.is_connected:
            return self.db["custom_training_requests"]
        return self.db["custom_training_requests"]

    @property
    def user_custom_models(self):
        if self.is_connected:
            return self.db["user_custom_models"]
        return self.db["user_custom_models"]

    @property
    def training_payments(self):
        if self.is_connected:
            return self.db["training_payments"]
        return self.db["training_payments"]

    @property
    def admin_action_logs(self):
        if self.is_connected:
            return self.db["admin_action_logs"]
        return self.db["admin_action_logs"]

    def health_check(self):
        if not self.is_connected:
            return {
                "status": "fallback_in_memory",
                "message": "MongoDB is offline. Operating in in-memory mode.",
                "database": Config.MONGO_DB_NAME,
            }
        try:
            self.client.admin.command("ping")
            return {
                "status": "connected",
                "message": "MongoDB connection active and healthy.",
                "database": Config.MONGO_DB_NAME,
                "collections": self.db.list_collection_names(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global database instance
db_manager = DatabaseManager()
