"""
backend/models/usage_model.py

Productive usage tracking and subscription entitlement models for MongoDB.
Handles usage sessions, monthly summaries, and entitlement validation.
"""

from datetime import datetime, timedelta
from backend.db import db_manager
import uuid


class UsageModel:
    """Model for tracking productive usage sessions."""

    @staticmethod
    def start_session(user_id, activity_type="sign_recognition"):
        """Start a new productive usage session."""
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        period_end = datetime(now.year + (now.month // 12), (now.month % 12) + 1, 1)

        session = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "activity_type": activity_type,
            "period_start": period_start,
            "period_end": period_end,
            "start_time": now,
            "last_heartbeat": now,
            "end_time": None,
            "accumulated_seconds": 0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        res = db_manager.db["usage_sessions"].insert_one(session)
        session["_id"] = str(res.inserted_id)
        return session

    @staticmethod
    def get_active_session(user_id):
        """Get the user's currently active session."""
        return db_manager.db["usage_sessions"].find_one({
            "user_id": user_id,
            "status": "active"
        })

    @staticmethod
    def heartbeat(session_id, user_id):
        """Update session with heartbeat and accumulate time."""
        session = db_manager.db["usage_sessions"].find_one({
            "session_id": session_id,
            "user_id": user_id,
            "status": "active"
        })
        if not session:
            return None

        now = datetime.utcnow()
        last_heartbeat = session.get("last_heartbeat", session["start_time"])
        elapsed = int((now - last_heartbeat).total_seconds())

        # Cap elapsed time to prevent abuse (max 2x heartbeat interval)
        max_elapsed = 120  # 2 minutes max per heartbeat
        elapsed = min(elapsed, max_elapsed)

        new_accumulated = session.get("accumulated_seconds", 0) + elapsed

        db_manager.db["usage_sessions"].update_one(
            {"session_id": session_id},
            {"$set": {
                "last_heartbeat": now,
                "accumulated_seconds": new_accumulated,
                "updated_at": now,
            }}
        )
        return new_accumulated

    @staticmethod
    def stop_session(session_id, user_id):
        """Stop a usage session and finalize accumulated time."""
        session = db_manager.db["usage_sessions"].find_one({
            "session_id": session_id,
            "user_id": user_id,
            "status": "active"
        })
        if not session:
            return None

        now = datetime.utcnow()
        last_heartbeat = session.get("last_heartbeat", session["start_time"])
        elapsed = int((now - last_heartbeat).total_seconds())
        elapsed = min(elapsed, 120)

        final_accumulated = session.get("accumulated_seconds", 0) + elapsed

        db_manager.db["usage_sessions"].update_one(
            {"session_id": session_id},
            {"$set": {
                "end_time": now,
                "accumulated_seconds": final_accumulated,
                "status": "completed",
                "updated_at": now,
            }}
        )

        # Update monthly summary
        MonthlyUsageModel.add_usage(user_id, session["period_start"], final_accumulated, session["activity_type"])

        return final_accumulated

    @staticmethod
    def cleanup_stale_sessions():
        """Mark sessions as expired if no heartbeat for timeout period."""
        timeout = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes
        db_manager.db["usage_sessions"].update_many(
            {"status": "active", "last_heartbeat": {"$lt": timeout}},
            {"$set": {"status": "expired", "updated_at": datetime.utcnow()}}
        )


class MonthlyUsageModel:
    """Model for monthly usage summaries."""

    @staticmethod
    def get_current_period():
        """Get current UTC month period boundaries."""
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1)
        else:
            period_end = datetime(now.year, now.month + 1, 1)
        return period_start, period_end

    @staticmethod
    def get_monthly_summary(user_id, period_start=None):
        """Get monthly usage summary for a user."""
        if period_start is None:
            period_start, _ = MonthlyUsageModel.get_current_period()

        summary = db_manager.db["monthly_usage"].find_one({
            "user_id": user_id,
            "period_start": period_start
        })
        return summary

    @staticmethod
    def add_usage(user_id, period_start, seconds, activity_type="sign_recognition"):
        """Add usage seconds to monthly summary (atomic upsert)."""
        period_end = period_start + timedelta(days=32)
        period_end = datetime(period_end.year, period_end.month, 1)

        now = datetime.utcnow()
        db_manager.db["monthly_usage"].update_one(
            {"user_id": user_id, "period_start": period_start},
            {
                "$inc": {"total_seconds": seconds},
                "$set": {"period_end": period_end, "updated_at": now},
                "$setOnInsert": {"created_at": now, "activity_breakdown": {}}
            },
            upsert=True
        )
        # Also update activity breakdown
        db_manager.db["monthly_usage"].update_one(
            {"user_id": user_id, "period_start": period_start},
            {"$inc": {f"activity_breakdown.{activity_type}": seconds}}
        )

    @staticmethod
    def get_usage_with_allowance(user_id):
        """Get current usage with free allowance info."""
        from backend.config import Config
        period_start, period_end = MonthlyUsageModel.get_current_period()
        summary = MonthlyUsageModel.get_monthly_summary(user_id, period_start)

        used_seconds = summary.get("total_seconds", 0) if summary else 0
        allowance = Config.FREE_MONTHLY_ALLOWANCE_SECONDS
        remaining = max(0, allowance - used_seconds)
        percentage = min(100, (used_seconds / allowance * 100) if allowance > 0 else 0)

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "used_seconds": used_seconds,
            "allowance_seconds": allowance,
            "remaining_seconds": remaining,
            "percentage_used": round(percentage, 1),
            "used_formatted": MonthlyUsageModel.format_seconds(used_seconds),
            "remaining_formatted": MonthlyUsageModel.format_seconds(remaining),
            "allowance_formatted": MonthlyUsageModel.format_seconds(allowance),
        }

    @staticmethod
    def format_seconds(seconds):
        """Format seconds as human readable string."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")
        return " ".join(parts)

    @staticmethod
    def can_user_start_session(user_id, user_plan):
        """Check if user can start a new productive session."""
        from backend.config import Config
        entitlements = Config.get_user_entitlements(user_plan)

        if entitlements.get("unlimited_usage"):
            return True, None

        usage = MonthlyUsageModel.get_usage_with_allowance(user_id)
        if usage["remaining_seconds"] <= 0:
            return False, {
                "message": "Monthly free allowance exhausted",
                "upgrade_required": True,
                "usage": usage
            }
        return True, None


class EntitlementModel:
    """Model for managing user entitlements and subscription status."""

    @staticmethod
    def get_user_entitlements(user_id):
        """Get all entitlements for a user."""
        user = db_manager.users.find_one({"clerk_id": user_id})
        if not user:
            return Config.get_user_entitlements("free")

        plan = user.get("plan", "free")
        entitlements = Config.get_user_entitlements(plan)

        # Check for lifetime purchase
        if user.get("lifetime_purchase"):
            lifetime_entitlements = Config.get_user_entitlements("lifetime")
            entitlements.update(lifetime_entitlements)

        # Check for custom training purchase
        if user.get("custom_training_purchased"):
            entitlements["custom_training"] = True

        # Check active subscription status
        if plan == "premium":
            stripe_sub = user.get("stripe_subscription", {})
            if stripe_sub.get("status") in ["active", "trialing"]:
                pass  # Entitlements already applied
            else:
                # Subscription expired/canceled - downgrade to free
                entitlements = Config.get_user_entitlements("free")

        return entitlements

    @staticmethod
    def has_language_access(user_id, language_code):
        """Check if user has access to a specific language."""
        entitlements = EntitlementModel.get_user_entitlements(user_id)
        allowed_languages = entitlements.get("languages", ["en"])
        return language_code in allowed_languages or "regional" in allowed_languages

    @staticmethod
    def get_accessible_languages(user_id):
        """Get list of languages accessible to user."""
        entitlements = EntitlementModel.get_user_entitlements(user_id)
        return entitlements.get("languages", ["en"])

    @staticmethod
    def can_use_feature(user_id, feature):
        """Check if user can use a specific feature."""
        entitlements = EntitlementModel.get_user_entitlements(user_id)
        return entitlements.get(feature, False)


# Import Config here to avoid circular import
from backend.config import Config