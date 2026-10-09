"""
backend/routes/admin_routes.py

Admin dashboard API endpoints.
Requires admin role authorization.
"""

from flask import Blueprint, request, g
from backend.utils.clerk_auth import require_auth
from backend.utils.helpers import api_response
from backend.models.admin_model import AdminModel, AdminActionLog, AdminAuthorization
from backend.models.custom_training_model import CustomTrainingRequest, UserCustomModel
from backend.models.language_model import LanguageRegistry
from backend.config import Config
from backend.db import db_manager
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def require_admin(f):
    """Decorator to require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AdminAuthorization.is_admin(g.clerk_id):
            return api_response(success=False, error="Admin access required", status_code=403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.get("/dashboard")
@require_auth
@require_admin
def get_dashboard():
    """Get admin dashboard statistics."""
    stats = AdminModel.get_dashboard_stats()
    AdminActionLog.log_action(g.clerk_id, "view_dashboard", "dashboard", "main")
    return api_response(data=stats)


@admin_bp.get("/users")
@require_auth
@require_admin
def get_users():
    """Get paginated user list."""
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    plan_filter = request.args.get("plan")
    search = request.args.get("search")

    result = AdminModel.get_user_list(page, per_page, plan_filter, search)
    AdminActionLog.log_action(g.clerk_id, "list_users", "users", "all", {"page": page, "filter": plan_filter})
    return api_response(data=result)


@admin_bp.get("/training-requests")
@require_auth
@require_admin
def get_training_requests():
    """Get all training requests with optional status filter."""
    status_filter = request.args.get("status")
    requests = CustomTrainingRequest.get_all_requests(status_filter)
    AdminActionLog.log_action(g.clerk_id, "list_training_requests", "training_requests", "all", {"status": status_filter})
    return api_response(data={"requests": requests})


@admin_bp.get("/training-request/<request_id>")
@require_auth
@require_admin
def get_training_request_detail(request_id):
    """Get detailed view of a training request."""
    request_obj = AdminModel.get_training_request_detail(request_id)
    if not request_obj:
        return api_response(success=False, error="Request not found", status_code=404)
    return api_response(data={"request": request_obj})


@admin_bp.post("/training-request/<request_id>/status")
@require_auth
@require_admin
def update_training_request_status(request_id):
    """Update training request status."""
    data = request.get_json() or {}
    new_status = data.get("status")
    notes = data.get("notes", "")

    if not new_status:
        return api_response(success=False, error="Missing status", status_code=400)

    request_obj, error = CustomTrainingRequest.update_status(request_id, new_status, g.clerk_id, notes)
    if error:
        return api_response(success=False, error=error.get("error"), data=error, status_code=400)

    AdminActionLog.log_action(
        g.clerk_id,
        f"update_training_status_{new_status.lower()}",
        "training_request",
        request_id,
        {"new_status": new_status, "notes": notes}
    )

    return api_response(data={"request": request_obj}, message=f"Status updated to {new_status}")


@admin_bp.post("/training-request/<request_id>/approve")
@require_auth
@require_admin
def approve_training_model(request_id):
    """Approve a trained model for production use."""
    data = request.get_json() or {}
    model_path = data.get("model_path")
    notes = data.get("notes", "")

    if not model_path:
        return api_response(success=False, error="Missing model_path", status_code=400)

    request_obj, error = CustomTrainingRequest.approve_model(request_id, g.clerk_id, model_path, notes)
    if error:
        return api_response(success=False, error=error.get("error"), data=error, status_code=400)

    AdminActionLog.log_action(
        g.clerk_id,
        "approve_training_model",
        "training_request",
        request_id,
        {"model_path": model_path, "notes": notes}
    )

    return api_response(data={"request": request_obj}, message="Model approved and activated for user")


@admin_bp.post("/training-request/<request_id>/reject")
@require_auth
@require_admin
def reject_training_request(request_id):
    """Reject a training request."""
    data = request.get_json() or {}
    reason = data.get("reason", "No reason provided")

    request_obj, error = CustomTrainingRequest.reject_request(request_id, g.clerk_id, reason)
    if error:
        return api_response(success=False, error=error.get("error"), data=error, status_code=400)

    AdminActionLog.log_action(
        g.clerk_id,
        "reject_training_request",
        "training_request",
        request_id,
        {"reason": reason}
    )

    return api_response(data={"request": request_obj}, message="Request rejected")


@admin_bp.get("/languages")
@require_auth
@require_admin
def get_languages():
    """Get all languages for admin management."""
    languages = LanguageRegistry.get_all_languages()
    return api_response(data={"languages": languages})


@admin_bp.post("/languages")
@require_auth
@require_admin
def update_language():
    """Update language configuration."""
    data = request.get_json() or {}
    language_id = data.get("language_id")
    updates = data.get("updates", {})

    if not language_id:
        return api_response(success=False, error="Missing language_id", status_code=400)

    # Remove protected fields
    protected = ["id", "created_at"]
    for field in protected:
        updates.pop(field, None)

    language = LanguageRegistry.update_language(language_id, updates)
    if not language:
        return api_response(success=False, error="Language not found", status_code=404)

    AdminActionLog.log_action(
        g.clerk_id,
        "update_language",
        "language",
        language_id,
        updates
    )

    return api_response(data={"language": language}, message="Language updated")


@admin_bp.post("/languages/custom")
@require_auth
@require_admin
def add_custom_language():
    """Add a custom trained language to the registry."""
    data = request.get_json() or {}

    required = ["id", "name", "native_name", "country", "variant", "model_id"]
    for field in required:
        if not data.get(field):
            return api_response(success=False, error=f"Missing required field: {field}", status_code=400)

    language = LanguageRegistry.add_custom_language(data)

    AdminActionLog.log_action(
        g.clerk_id,
        "add_custom_language",
        "language",
        language["id"],
        {"language": language}
    )

    return api_response(data={"language": language}, message="Custom language added to registry")


@admin_bp.get("/payments")
@require_auth
@require_admin
def get_payments():
    """Get recent payments."""
    limit = min(int(request.args.get("limit", 50)), 200)
    payments = AdminModel.get_recent_payments(limit)
    return api_response(data=payments)


@admin_bp.get("/action-logs")
@require_auth
@require_admin
def get_action_logs():
    """Get admin action logs."""
    limit = min(int(request.args.get("limit", 100)), 500)
    admin_id = request.args.get("admin_id")
    target_type = request.args.get("target_type")
    logs = AdminActionLog.get_logs(limit, admin_id, target_type)
    return api_response(data={"logs": logs})


@admin_bp.post("/users/<user_id>/plan")
@require_auth
@require_admin
def update_user_plan(user_id):
    """Manually update a user's plan (admin only)."""
    data = request.get_json() or {}
    new_plan = data.get("plan")

    if new_plan not in ["free", "premium", "lifetime"]:
        return api_response(success=False, error="Invalid plan", status_code=400)

    from backend.models.user_model import UserModel
    user = UserModel.get_by_clerk_id(user_id)
    if not user:
        return api_response(success=False, error="User not found", status_code=404)

    update = {"plan": new_plan, "updated_at": datetime.utcnow()}
    if new_plan == "lifetime":
        update["lifetime_purchase"] = True
        update["lifetime_purchase_date"] = datetime.utcnow()
    elif new_plan == "premium":
        update["lifetime_purchase"] = False

    db_manager.users.update_one({"clerk_id": user_id}, {"$set": update})

    AdminActionLog.log_action(
        g.clerk_id,
        "update_user_plan",
        "user",
        user_id,
        {"new_plan": new_plan}
    )

    return api_response(message=f"User plan updated to {new_plan}")


@admin_bp.post("/users/<user_id>/admin")
@require_auth
@require_admin
def toggle_admin_role(user_id):
    """Grant or revoke admin role for a user (master admin only)."""
    # Check if current user is master admin
    current_user = db_manager.users.find_one({"clerk_id": g.clerk_id})
    if not current_user or current_user.get("email") != "offsray7044@gmail.com":
        return api_response(success=False, error="Only master admin can manage admin roles", status_code=403)

    data = request.get_json() or {}
    action = data.get("action")  # "grant" or "revoke"

    if action not in ["grant", "revoke"]:
        return api_response(success=False, error="Invalid action. Use 'grant' or 'revoke'", status_code=400)

    from backend.models.user_model import UserModel
    user = UserModel.get_by_clerk_id(user_id)
    if not user:
        return api_response(success=False, error="User not found", status_code=404)

    if action == "grant":
        db_manager.users.update_one(
            {"clerk_id": user_id},
            {"$set": {"role": "admin", "admin_granted_at": datetime.utcnow(), "admin_granted_by": g.clerk_id}}
        )
        message = f"Admin role granted to user"
    else:
        # Prevent revoking master admin
        if user.get("email") == "offsray7044@gmail.com":
            return api_response(success=False, error="Cannot revoke master admin", status_code=400)
        db_manager.users.update_one(
            {"clerk_id": user_id},
            {"$set": {"role": "user"}}
        )
        message = f"Admin role revoked from user"

    AdminActionLog.log_action(
        g.clerk_id,
        f"{action}_admin_role",
        "user",
        user_id,
        {"target_user_id": user_id, "target_email": user.get("email")}
    )

    return api_response(message=message)