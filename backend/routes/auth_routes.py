"""
backend/routes/auth_routes.py

Authentication and user profile routes for Clerk Email OTP integration.
"""

from flask import Blueprint, request, g
from backend.config import Config
from backend.models.user_model import UserModel
from backend.utils.clerk_auth import require_auth, optional_auth
from backend.utils.helpers import api_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.get("/config")
def get_auth_config():
    """Returns the Clerk Publishable Key for frontend initialization."""
    return api_response(
        data={
            "clerk_publishable_key": Config.CLERK_PUBLISHABLE_KEY,
            "stripe_publishable_key": Config.STRIPE_PUBLISHABLE_KEY,
        }
    )


@auth_bp.post("/sync")
def sync_user():
    """
    Called when a user logs in via Clerk Email OTP to synchronize
    profile and preferences into MongoDB.
    """
    data = request.get_json() or {}
    clerk_id = data.get("clerk_id") or data.get("id")
    email = data.get("email")
    name = data.get("name")
    image_url = data.get("image_url")

    if not clerk_id or not email:
        return api_response(
            success=False,
            error="Missing clerk_id or email in request body.",
            status_code=400
        )

    user = UserModel.sync_clerk_user(
        clerk_id=clerk_id,
        email=email,
        name=name,
        image_url=image_url
    )
    return api_response(data=user, message="User profile synchronized successfully.")


@auth_bp.get("/profile")
@require_auth
def get_profile():
    """Fetches user profile and settings from MongoDB."""
    user = UserModel.get_by_clerk_id(g.clerk_id)
    if not user:
        # Auto-sync if not present
        claims = g.user_claims or {}
        user = UserModel.sync_clerk_user(
            clerk_id=g.clerk_id,
            email=claims.get("email", ""),
            name=claims.get("name", "")
        )
    return api_response(data=user)


@auth_bp.put("/preferences")
@require_auth
def update_preferences():
    """Updates user language, sign system, and speech preferences."""
    data = request.get_json() or {}
    updated_user = UserModel.update_preferences(g.clerk_id, data)
    if not updated_user:
        return api_response(success=False, error="User not found.", status_code=404)
    return api_response(data=updated_user, message="Preferences updated successfully.")
