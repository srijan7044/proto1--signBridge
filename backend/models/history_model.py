"""
backend/models/history_model.py

Conversation transcripts and translation logging model for MongoDB.
"""

from datetime import datetime
from backend.db import db_manager

class HistoryModel:
    @staticmethod
    def log_translation(user_id, raw_gloss, translated_sentence, mode="sign_to_speech", sign_system="ASL"):
        doc = {
            "user_id": user_id,
            "mode": mode,
            "sign_system": sign_system,
            "raw_gloss": raw_gloss,
            "translated_sentence": translated_sentence,
            "created_at": datetime.utcnow(),
        }
        res = db_manager.conversations.insert_one(doc)
        return str(res.inserted_id)

    @staticmethod
    def get_recent_history(user_id=None, limit=20):
        query = {"user_id": user_id} if user_id else {}
        return list(db_manager.conversations.find(query))[-limit:]
