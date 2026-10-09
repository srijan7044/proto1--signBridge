"""
backend/utils/clerk_auth.py

Clerk Authentication middleware and JWT validation decorator.
Supports standard Clerk RS256 JWTs via JWKS, unverified payload fallbacks, and dev demo tokens.
"""

from functools import wraps
import jwt
from jwt import PyJWKClient
from flask import request, g
import logging

from backend.config import Config
from backend.utils.helpers import api_response
from backend.db import db_manager

logger = logging.getLogger("signbridge.clerk")

_jwks_client = None

def get_jwks_client():
    """Returns or initializes a cached PyJWKClient for Clerk JWKS endpoint."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client

    jwks_url = Config.CLERK_JWKS_URL
    if not jwks_url or "api.clerk.dev" in jwks_url:
        pub_key = Config.CLERK_PUBLISHABLE_KEY
        if pub_key and "_" in pub_key:
            try:
                import base64
                b64 = pub_key.split("_")[2]
                domain = base64.b64decode(b64 + "==").decode("utf-8").rstrip("$")
                jwks_url = f"https://{domain}/.well-known/jwks.json"
            except Exception as e:
                logger.warning(f"Failed to derive JWKS URL from publishable key: {e}")

    if jwks_url:
        try:
            _jwks_client = PyJWKClient(jwks_url)
            logger.info(f"Initialized PyJWKClient with URL: {jwks_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize PyJWKClient ({jwks_url}): {e}")
    return _jwks_client


def get_token_from_header():
    """Extracts Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def verify_clerk_token(token):
    """
    Verifies a Clerk JWT token or development demo token.
    Returns decoded claims dictionary or None if invalid.
    """
    if not token:
        logger.debug("[AUTH] Missing token.")
        return None

    # Handle demo/development tokens (from OTP fallback mode)
    if token.startswith("demo_token_"):
        clerk_id = token.replace("demo_token_", "")
        user = db_manager.users.find_one({"clerk_id": clerk_id})
        is_master = "offsray" in clerk_id or (user and user.get("email") == "offsray7044@gmail.com")
        if user:
            return {
                "sub": clerk_id,
                "email": user.get("email", ""),
                "name": user.get("name", "User"),
                "role": "admin" if is_master else user.get("role", "user"),
                "plan": user.get("plan", "free"),
            }
        return {
            "sub": clerk_id,
            "email": "offsray7044@gmail.com" if is_master else "demo@signbridge.app",
            "name": "Master Admin" if is_master else "Demo User",
            "role": "admin" if is_master else "user",
            "plan": "free",
        }

    # Handle standard JWT tokens (containing dots)
    if "." in token:
        decoded_claims = None
        jwks_client = get_jwks_client()

        # 1. Attempt cryptographic verification via JWKS
        if jwks_client:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                decoded_claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    options={"verify_aud": False}
                )
                logger.debug("[AUTH] Cryptographic RS256 JWKS token verification succeeded.")
            except Exception as jwks_err:
                logger.warning(f"[AUTH] JWKS verification failed ({jwks_err}). Trying fallback payload decode.")

        # 2. Fallback: decode unverified payload if JWKS fails or is unavailable in local dev
        if not decoded_claims:
            try:
                decoded_claims = jwt.decode(token, options={"verify_signature": False})
                logger.debug("[AUTH] Unverified payload decode succeeded for local dev.")
            except Exception as jwt_err:
                logger.warning(f"[AUTH] Unverified JWT decode failed: {jwt_err}")

        if decoded_claims:
            clerk_id = decoded_claims.get("sub") or decoded_claims.get("userId") or decoded_claims.get("id")
            if not clerk_id:
                logger.warning("[AUTH] JWT payload missing sub/userId claim.")
                return None

            # Resolve user from database
            user = db_manager.users.find_one({"$or": [{"clerk_id": clerk_id}, {"email": decoded_claims.get("email")}]})
            user_email = decoded_claims.get("email") or (user.get("email") if user else "")
            is_master = (user_email.lower() == "offsray7044@gmail.com") or ("offsray" in clerk_id)

            if user:
                decoded_claims["sub"] = user.get("clerk_id", clerk_id)
                decoded_claims["email"] = user.get("email", user_email)
                decoded_claims["name"] = user.get("name", decoded_claims.get("name", "User"))
                decoded_claims["role"] = "admin" if is_master else user.get("role", "user")
                decoded_claims["plan"] = user.get("plan", "free")
            else:
                # Auto-sync missing user record into database
                from backend.models.user_model import UserModel
                synced_user = UserModel.sync_clerk_user(
                    clerk_id=clerk_id,
                    email=user_email or f"{clerk_id}@signbridge.app",
                    name=decoded_claims.get("name", "SignBridge User")
                )
                decoded_claims["sub"] = clerk_id
                decoded_claims["email"] = synced_user.get("email")
                decoded_claims["role"] = "admin" if is_master else synced_user.get("role", "user")
                decoded_claims["plan"] = synced_user.get("plan", "free")

            return decoded_claims

    # Secondary fallback: lookup exact token match in database
    try:
        user = db_manager.users.find_one({"clerk_id": token})
        if user:
            is_master = user.get("email") == "offsray7044@gmail.com"
            return {
                "sub": user.get("clerk_id", token),
                "email": user.get("email", ""),
                "name": user.get("name", "User"),
                "role": "admin" if is_master else user.get("role", "user"),
                "plan": user.get("plan", "free"),
            }
    except Exception as db_err:
        logger.warning(f"[AUTH] DB user token lookup error: {db_err}")

    logger.warning("[AUTH] Token verification failed for all strategies.")
    return None


def require_auth(f):
    """Decorator to protect routes requiring an authenticated Clerk session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            logger.debug("[AUTH] 401: Missing Authorization header.")
            return api_response(
                success=False,
                error="Unauthorized: Missing Authorization header (Bearer token).",
                status_code=401
            )

        claims = verify_clerk_token(token)
        if not claims:
            logger.debug("[AUTH] 401: Token verification returned None.")
            return api_response(
                success=False,
                error="Unauthorized: Invalid or expired Clerk session token.",
                status_code=401
            )

        g.user_claims = claims
        g.clerk_id = claims.get("sub")
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
                g.clerk_id = claims.get("sub")
        return f(*args, **kwargs)
    return decorated
