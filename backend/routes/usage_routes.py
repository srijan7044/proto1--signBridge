"""
backend/routes/usage_routes.py

Productive usage tracking API endpoints.
Handles session start, heartbeat, stop, and usage summaries.
"""

from flask import Blueprint, request, g
from backend.utils.clerk_auth import require_auth
from backend.utils.helpers import api_response
from backend.models.usage_model import UsageModel, MonthlyUsageModel, EntitlementModel
from backend.config import Config
from datetime import datetime

usage_bp = Blueprint("usage", __name__, url_prefix="/api/usage")


@usage_bp.post("/start")
@require_auth
def start_usage_session():
    """
    Start a new productive usage session.
    Body: {"activity_type": "sign_recognition"} (optional)
    """
    data = request.get_json() or {}
    activity_type = data.get("activity_type", "sign_recognition")

    # Validate activity type
    valid_activities = ["sign_recognition", "text_to_sign", "speech_to_text", "translation", "practice"]
    if activity_type not in valid_activities:
        activity_type = "sign_recognition"

    # Check if user can start a session
    can_start, error = MonthlyUsageModel.can_user_start_session(g.clerk_id, g.user_claims.get("plan", "free"))
    if not can_start:
        return api_response(
            success=False,
            error=error.get("message", "Usage limit reached"),
            data=error,
            status_code=403
        )

    # Check for existing active session
    existing = UsageModel.get_active_session(g.clerk_id)
    if existing:
        # Return existing session instead of creating duplicate
        return api_response(
            data={
                "session": existing,
                "message": "Resumed existing session",
                "resumed": True,
            },
            message="Existing active session found"
        )

    session = UsageModel.start_session(g.clerk_id, activity_type)
    return api_response(data={"session": session}, message="Usage session started")


@usage_bp.post("/heartbeat")
@require_auth
def usage_heartbeat():
    """
    Send heartbeat for active usage session.
    Body: {"session_id": "..."}
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")

    if not session_id:
        return api_response(success=False, error="Missing session_id", status_code=400)

    accumulated = UsageModel.heartbeat(session_id, g.clerk_id)
    if accumulated is None:
        return api_response(success=False, error="Session not found or expired", status_code=404)

    # Check if user exceeded allowance (for free users)
    entitlements = EntitlementModel.get_user_entitlements(g.clerk_id)
    if not entitlements.get("unlimited_usage"):
        usage = MonthlyUsageModel.get_usage_with_allowance(g.clerk_id)
        if usage["remaining_seconds"] <= 0:
            # Auto-stop session
            UsageModel.stop_session(session_id, g.clerk_id)
            return api_response(
                success=False,
                error="Monthly allowance exhausted",
                data={"usage": usage, "limit_reached": True},
                status_code=403
            )

    return api_response(data={"accumulated_seconds": accumulated})


@usage_bp.post("/stop")
@require_auth
def stop_usage_session():
    """
    Stop a usage session.
    Body: {"session_id": "..."}
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")

    if not session_id:
        return api_response(success=False, error="Missing session_id", status_code=400)

    accumulated = UsageModel.stop_session(session_id, g.clerk_id)
    if accumulated is None:
        return api_response(success=False, error="Session not found", status_code=404)

    return api_response(
        data={"session_id": session_id, "accumulated_seconds": accumulated},
        message="Usage session stopped"
    )


@usage_bp.get("/current")
@require_auth
def get_current_session():
    """Get current active usage session."""
    session = UsageModel.get_active_session(g.clerk_id)
    if not session:
        return api_response(data={"session": None, "message": "No active session"})

    # Add elapsed time so far
    now = datetime.utcnow()
    last_heartbeat = session.get("last_heartbeat", session["start_time"])
    elapsed = int((now - last_heartbeat).total_seconds())
    current_total = session.get("accumulated_seconds", 0) + min(elapsed, 120)

    return api_response(data={
        "session": session,
        "current_accumulated_seconds": current_total,
    })


from backend.models.user_model import UserModel

@usage_bp.get("/summary")
@require_auth
def get_usage_summary():
    """Get monthly usage summary with allowance info."""
    usage = MonthlyUsageModel.get_usage_with_allowance(g.clerk_id)
    entitlements = EntitlementModel.get_user_entitlements(g.clerk_id)
    effective_plan = UserModel.get_effective_plan(g.clerk_id)

    return api_response(data={
        "usage": usage,
        "entitlements": entitlements,
        "plan": effective_plan,
    })


@usage_bp.get("/history")
@require_auth
def get_usage_history():
    """Get usage history for the user."""
    from datetime import datetime, timedelta

    # Get last 12 months of usage
    now = datetime.utcnow()
    history = []
    for i in range(12):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        period_start = datetime(year, month, 1)
        summary = MonthlyUsageModel.get_monthly_summary(g.clerk_id, period_start)
        if summary:
            history.append({
                "period_start": period_start.isoformat(),
                "total_seconds": summary.get("total_seconds", 0),
                "formatted": MonthlyUsageModel.format_seconds(summary.get("total_seconds", 0)),
            })

    return api_response(data={"history": history})