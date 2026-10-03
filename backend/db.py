"""
backend/db.py

MongoDB connection manager for SignBridge with health monitoring
and safe in-memory fallback for local development.
"""

import logging
from backend.config import Config

logger = logging.getLogger("signbridge.db")

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

    def find_one(self, query):
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
        return results

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
            self.db = {
                "users": InMemoryCollection("users"),
                "gestures": InMemoryCollection("gestures"),
                "payments": InMemoryCollection("payments"),
                "conversations": InMemoryCollection("conversations"),
            }

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
