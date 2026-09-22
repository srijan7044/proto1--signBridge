"""
backend/utils/clerk_auth.py

Clerk Authentication middleware and JWT validation decorator.
Handles Clerk Email OTP session tokens.
"""

from functools import wraps
import jwt
from flask import request, g
import logging
from backend.config import Config
from backend.utils.helpers import api_response

logger = logging.getLogger("signbridge.clerk")


def get_token_from_header():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1].strip()
    return None


def verify_clerk_token(token):
    """
    Verifies a Clerk JWT token.
    Decodes claims (sub, email, name, etc.).
    """
    if not token:
        return None

    try:
        # In production with CLERK_SECRET_KEY, verify signature
        if Config.CLERK_SECRET_KEY and not Config.CLERK_SECRET_KEY.startswith("sk_test_signbridge"):
            decoded = jwt.decode(
                token,
                Config.CLERK_SECRET_KEY,
                algorithms=["HS256", "RS256"],
                options={"verify_signature": True, "verify_aud": False}
            )
            return decoded
        else:
            # Development fallback: decode claims without signature check
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded
    except Exception as e:
        logger.warning(f"Clerk JWT validation error: {e}")
        return None


def require_auth(f):
    """Decorator to protect routes requiring authenticated Clerk session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return api_response(
                success=False,
                error="Unauthorized: Missing Authorization header (Bearer token).",
                status_code=401
            )

        claims = verify_clerk_token(token)
        if not claims:
            return api_response(
                success=False,
                error="Unauthorized: Invalid or expired Clerk session token.",
                status_code=401
            )

        g.user_claims = claims
        g.clerk_id = claims.get("sub") or claims.get("userId") or claims.get("id")
        return f(*args, **kwargs)
    return decorated

def optional_auth(f):
    """Decorator for routes where authentication is optional."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user_claims = None
        g.clerk_id = None
        token = get_token_from_header()
        if token:
            claims = verify_clerk_token(token)
            if claims:
                g.user_claims = claims
                g.clerk_id = (
                    claims.get("sub")
                    or claims.get("userId")
                    or claims.get("id")
                )
        return f(*args, **kwargs)
    return decorated
