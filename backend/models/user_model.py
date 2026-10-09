"""
backend/models/user_model.py

User data access object for MongoDB.
Handles user synchronization from Clerk OTP, profile preferences, and subscription tiers.
"""

from datetime import datetime
from backend.db import db_manager
from backend.config import Config

# Master admin email - automatically granted admin privileges
MASTER_ADMIN_EMAIL = "offsray7044@gmail.com"

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
            # Auto-grant admin role for master admin email
            if email == MASTER_ADMIN_EMAIL and existing.get("role") != "admin":
                update_data["role"] = "admin"
            db_manager.users.update_one(query, {"$set": update_data})
            return db_manager.users.find_one(query)

        new_user = {
            "clerk_id": clerk_id,
            "email": email,
            "name": name or "SignBridge User",
            "image_url": image_url or "",
            "role": "admin" if email == MASTER_ADMIN_EMAIL else "user",
            "plan": "free",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "stripe_subscription_status": None,
            "stripe_subscription_current_period_end": None,
            "lifetime_purchase": False,
            "lifetime_purchase_date": None,
            "custom_training_purchased": False,
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
    def get_effective_plan(clerk_id):
        """
        Returns the authoritative current effective plan for a user,
        distinguishing between active vs canceled/expired subscriptions,
        lifetime purchases, and fallback to free.
        """
        user = UserModel.get_by_clerk_id(clerk_id)
        if not user:
            return "free"

        if user.get("lifetime_purchase") or user.get("plan") == "lifetime":
            return "lifetime"

        plan = user.get("plan", "free")
        if plan == "premium":
            sub_status = user.get("stripe_subscription_status")
            stripe_sub = user.get("stripe_subscription", {})
            if isinstance(stripe_sub, dict) and stripe_sub.get("status"):
                sub_status = stripe_sub.get("status")

            if sub_status in ["active", "trialing"]:
                return "premium"
            else:
                # Expired or canceled subscription -> effective plan is free
                return "free"

        return plan if plan in Config.PLANS else "free"

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
    def update_subscription(clerk_id, plan, stripe_customer_id=None, stripe_subscription_id=None, stripe_subscription_status=None, stripe_subscription_current_period_end=None):
        """Updates user tier upon successful Stripe Checkout."""
        update = {"plan": plan, "updated_at": datetime.utcnow()}
        if stripe_customer_id:
            update["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id:
            update["stripe_subscription_id"] = stripe_subscription_id
        if stripe_subscription_status:
            update["stripe_subscription_status"] = stripe_subscription_status
        if stripe_subscription_current_period_end:
            update["stripe_subscription_current_period_end"] = stripe_subscription_current_period_end
        db_manager.users.update_one({"clerk_id": clerk_id}, {"$set": update}, upsert=True)
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def grant_lifetime_access(clerk_id, stripe_customer_id=None):
        """Grant lifetime access to user."""
        now = datetime.utcnow()
        update = {
            "plan": "lifetime",
            "lifetime_purchase": True,
            "lifetime_purchase_date": now,
            "updated_at": now,
        }
        if stripe_customer_id:
            update["stripe_customer_id"] = stripe_customer_id
        db_manager.users.update_one({"clerk_id": clerk_id}, {"$set": update}, upsert=True)
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def grant_custom_training_access(clerk_id):
        """Grant custom training purchase access."""
        update = {
            "custom_training_purchased": True,
            "updated_at": datetime.utcnow(),
        }
        db_manager.users.update_one({"clerk_id": clerk_id}, {"$set": update}, upsert=True)
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def revoke_subscription(clerk_id):
        """Revoke subscription access (downgrade to free)."""
        update = {
            "plan": "free",
            "stripe_subscription_id": None,
            "stripe_subscription_status": None,
            "stripe_subscription_current_period_end": None,
            "updated_at": datetime.utcnow(),
        }
        db_manager.users.update_one({"clerk_id": clerk_id}, {"$set": update}, upsert=True)
        return db_manager.users.find_one({"clerk_id": clerk_id})

    @staticmethod
    def get_user_entitlements(clerk_id):
        """Get effective entitlements for a user."""
        from backend.models.usage_model import EntitlementModel
        return EntitlementModel.get_user_entitlements(clerk_id)
