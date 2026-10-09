"""
backend/models/admin_model.py

Admin dashboard models for user statistics, training request management,
and system monitoring.
"""

from datetime import datetime, timedelta
from backend.db import db_manager
from backend.config import Config


class AdminModel:
    """Admin dashboard statistics and management."""

    @staticmethod
    def get_dashboard_stats():
        """Get overall system statistics for admin dashboard."""
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        # User counts by plan
        total_users = db_manager.users.count_documents({})
        free_users = db_manager.users.count_documents({"plan": "free"})
        premium_users = db_manager.users.count_documents({"plan": "premium"})
        lifetime_users = db_manager.users.count_documents({"plan": "lifetime"})

        # Custom training requests
        total_requests = db_manager.db["custom_training_requests"].count_documents({})
        pending_review = db_manager.db["custom_training_requests"].count_documents({
            "status": {"$in": ["PAID_PENDING_REVIEW", "UNDER_REVIEW", "NEEDS_INFORMATION"]}
        })
        training = db_manager.db["custom_training_requests"].count_documents({"status": "TRAINING"})
        validating = db_manager.db["custom_training_requests"].count_documents({"status": "VALIDATING"})
        approved = db_manager.db["custom_training_requests"].count_documents({"status": "APPROVED"})
        rejected = db_manager.db["custom_training_requests"].count_documents({"status": "REJECTED"})

        # Revenue (this month)
        monthly_payments = list(db_manager.payments.find({
            "created_at": {"$gte": month_start},
            "status": "paid"
        }))
        monthly_revenue = sum(p.get("amount", 0) for p in monthly_payments)

        # Training payments this month
        monthly_training_payments = list(db_manager.db["training_payments"].find({
            "created_at": {"$gte": month_start},
            "status": "paid"
        }))
        training_revenue = sum(p.get("amount_usd", 0) for p in monthly_training_payments)

        return {
            "users": {
                "total": total_users,
                "free": free_users,
                "premium": premium_users,
                "lifetime": lifetime_users,
            },
            "custom_training": {
                "total_requests": total_requests,
                "pending_review": pending_review,
                "training": training,
                "validating": validating,
                "approved": approved,
                "rejected": rejected,
            },
            "revenue": {
                "monthly_subscription_usd": round(monthly_revenue, 2),
                "monthly_training_usd": round(training_revenue, 2),
                "monthly_total_usd": round(monthly_revenue + training_revenue, 2),
            },
            "generated_at": now.isoformat(),
        }

    @staticmethod
    def get_user_list(page=1, per_page=20, plan_filter=None, search=None):
        """Get paginated user list for admin."""
        query = {}
        if plan_filter:
            query["plan"] = plan_filter
        if search:
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}},
                {"clerk_id": {"$regex": search, "$options": "i"}},
            ]

        skip = (page - 1) * per_page
        users = list(db_manager.users.find(query).skip(skip).limit(per_page).sort("created_at", -1))
        total = db_manager.users.count_documents(query)

        # Add usage info for each user
        for user in users:
            from backend.models.usage_model import MonthlyUsageModel
            usage = MonthlyUsageModel.get_usage_with_allowance(user["clerk_id"])
            user["current_usage"] = usage

        return {
            "users": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            }
        }

    @staticmethod
    def get_training_request_detail(request_id):
        """Get detailed view of a training request for admin."""
        from backend.models.custom_training_model import CustomTrainingRequest
        request = CustomTrainingRequest.get_request(request_id)
        if not request:
            return None

        # Get user info
        user = db_manager.users.find_one({"clerk_id": request["user_id"]})
        request["user"] = user

        # Get payment info
        payment = db_manager.db["training_payments"].find_one({"request_id": request_id})
        request["payment"] = payment

        return request

    @staticmethod
    def get_recent_payments(limit=50):
        """Get recent payments for admin review."""
        payments = list(db_manager.payments.find({}).sort("created_at", -1).limit(limit))
        training_payments = list(db_manager.db["training_payments"].find({}).sort("created_at", -1).limit(limit))
        return {
            "subscriptions": payments,
            "training_payments": training_payments,
        }


class AdminActionLog:
    """Audit log for admin actions."""

    @staticmethod
    def log_action(admin_id, action, target_type, target_id, details=None):
        """Log an admin action."""
        log = {
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,  # "user", "training_request", "language", etc.
            "target_id": target_id,
            "details": details or {},
            "timestamp": datetime.utcnow(),
        }
        db_manager.db["admin_action_logs"].insert_one(log)
        return log

    @staticmethod
    def get_logs(limit=100, admin_id=None, target_type=None):
        """Get admin action logs."""
        query = {}
        if admin_id:
            query["admin_id"] = admin_id
        if target_type:
            query["target_type"] = target_type
        return list(db_manager.db["admin_action_logs"].find(query).sort("timestamp", -1).limit(limit))


class AdminAuthorization:
    """Admin authorization utilities."""

    @staticmethod
    def is_admin(user_id):
        """Check if user is an admin."""
        user = db_manager.users.find_one({"clerk_id": user_id})
        if user and user.get("email") == "offsray7044@gmail.com":
            return True
        return user and user.get("role") == "admin"

    @staticmethod
    def require_admin(user_id):
        """Raise exception if user is not admin."""
        if not AdminAuthorization.is_admin(user_id):
            raise PermissionError("Admin access required")

    @staticmethod
    def grant_admin(user_id):
        """Grant admin role to user (super-admin only)."""
        db_manager.users.update_one(
            {"clerk_id": user_id},
            {"$set": {"role": "admin", "admin_granted_at": datetime.utcnow()}}
        )

    @staticmethod
    def revoke_admin(user_id):
        """Revoke admin role from user."""
        db_manager.users.update_one(
            {"clerk_id": user_id},
            {"$set": {"role": "user"}}
        )