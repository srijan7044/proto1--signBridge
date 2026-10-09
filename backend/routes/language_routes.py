"""
backend/routes/language_routes.py

Language access control and multilingual support API endpoints.
"""

from flask import Blueprint, request, g
from backend.utils.clerk_auth import require_auth, optional_auth
from backend.utils.helpers import api_response
from backend.models.language_model import LanguageRegistry, LanguageAccessControl

language_bp = Blueprint("language", __name__, url_prefix="/api/language")


@language_bp.get("/list")
@optional_auth
def list_languages():
    """Get list of languages (filtered by user entitlement if authenticated)."""
    if g.clerk_id:
        languages = LanguageAccessControl.get_user_accessible_languages(g.clerk_id)
    else:
        # Anonymous users only see free languages
        languages = LanguageRegistry.get_languages_for_entitlement("free")

    # Format for frontend
    formatted = []
    for lang in languages:
        formatted.append({
            "id": lang["id"],
            "name": lang["name"],
            "native_name": lang.get("native_name", lang["name"]),
            "country": lang.get("country"),
            "region": lang.get("region"),
            "variant": lang.get("variant"),
            "status": lang.get("status"),
            "features": lang.get("features", {}),
            "required_entitlement": lang.get("required_entitlement"),
            "is_active": lang.get("is_active", True),
        })

    return api_response(data={"languages": formatted})


@language_bp.get("/<language_id>")
@optional_auth
def get_language(language_id):
    """Get detailed information about a specific language."""
    if g.clerk_id:
        has_access, result = LanguageAccessControl.validate_language_access(g.clerk_id, language_id)
    else:
        language = LanguageRegistry.get_language(language_id)
        if not language:
            return api_response(success=False, error="Language not found", status_code=404)
        if not language.get("is_active"):
            return api_response(success=False, error="Language not available", status_code=403)
        if language.get("required_entitlement") != "free":
            return api_response(success=False, error="Subscription required", status_code=403)
        has_access, result = True, language

    if not has_access:
        return api_response(success=False, error=result.get("error"), data=result, status_code=403)

    return api_response(data={"language": result})


@language_bp.post("/switch")
@require_auth
def switch_language():
    """Switch user's preferred language."""
    data = request.get_json() or {}
    language_id = data.get("language_id")

    if not language_id:
        return api_response(success=False, error="Missing language_id", status_code=400)

    has_access, result = LanguageAccessControl.validate_language_access(g.clerk_id, language_id)
    if not has_access:
        return api_response(success=False, error=result.get("error"), data=result, status_code=403)

    # Update user preferences
    from backend.models.user_model import UserModel
    updated_user = UserModel.update_preferences(g.clerk_id, {"preferred_language": language_id})

    return api_response(
        data={"language": result, "preferences": updated_user.get("preferences") if updated_user else {}},
        message=f"Language switched to {result['name']}"
    )


@language_bp.get("/current")
@require_auth
def get_current_language():
    """Get user's current preferred language."""
    from backend.models.user_model import UserModel
    user = UserModel.get_by_clerk_id(g.clerk_id)
    if not user:
        return api_response(success=False, error="User not found", status_code=404)

    preferred = user.get("preferences", {}).get("preferred_language", "en")
    language = LanguageRegistry.get_language(preferred)

    return api_response(data={"language": language, "preferred_language": preferred})