"""
backend/models/user_model.py

User data access object for MongoDB.
Handles user synchronization from Clerk OTP, profile preferences, and subscription tiers.
"""

from datetime import datetime
from backend.db import db_manager

class UserModel:
    @staticmethod
    def sync_clerk_user(clerk_id, email, name=None, image_url=None):
        """
        Upserts a user record upon Clerk OTP authentication.
        """
        now = datetime.utcnow()
        query = {"clerk_id": clerk_id}
        existing = db_manager.users.find_one(query)

        if existing:
            update_data = {
                "email": email or existing.get("email"),
                "name": name or existing.get("name", "SignBridge User"),
                "image_url": image_url or existing.get("image_url", ""),
                "last_login_at": now,
            }
            db_manager.users.update_one(query, {"$set": update_data})
            return db_manager.users.find_one(query)

        new_user = {
            "clerk_id": clerk_id,
            "email": email,
            "name": name or "SignBridge User",
            "image_url": image_url or "",
            "role": "user",
            "plan": "free",
            "stripe_customer_id": None,
            "preferences": {
                "auto_speak": True,
                "auto_add": True,
                "preferred_sign_system": "ASL",  # ASL or ISL
                "preferred_language": "en",       # en, hi, bn, etc.
                "speech_rate": 1.0,
            },
            "created_at": now,
            "last_login_at": now,
        }
        db_manager.users.insert_one(new_user)
        return db_manager.users.find_one(query)

    @staticmethod
    def get_by_clerk_id(clerk_id):
        if not clerk_id:
            return None
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def update_preferences(clerk_id, preferences_dict):
        """Updates user custom preferences (auto_speak, sign system, language)."""
        user = db_manager.users.find_one({"clerk_id": clerk_id})
        if not user:
            return None
        current_prefs = user.get("preferences", {})
        current_prefs.update(preferences_dict)
        db_manager.users.update_one(
            {"clerk_id": clerk_id},
            {"$set": {"preferences": current_prefs, "updated_at": datetime.utcnow()}}
        )
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def update_subscription(clerk_id, plan, stripe_customer_id=None):
        """Updates user tier upon successful Stripe Checkout."""
        update = {"plan": plan, "updated_at": datetime.utcnow()}
        if stripe_customer_id:
            update["stripe_customer_id"] = stripe_customer_id
        db_manager.users.update_one({"clerk_id": clerk_id}, {"$set": update})
        return db_manager.users.find_one({"clerk_id": clerk_id})
