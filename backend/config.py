"""
backend/config.py

Centralized configuration for SignBridge backend.
Loads environment variables from .env and defines runtime parameters.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    # Server
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "127.0.0.1")
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY = os.getenv("SECRET_KEY", "signbridge_default_secret_key_2026")

    # Directory Paths
    BASE_DIR = BASE_DIR
    DATA_DIR = os.path.join(BASE_DIR, "data")
    MODEL_DIR = os.path.join(BASE_DIR, "model")
    WEB_DIR = os.path.join(BASE_DIR, "web")
    MODEL_PATH = os.path.join(MODEL_DIR, "sign_classifier.joblib")
    LABELS_PATH = os.path.join(MODEL_DIR, "labels.joblib")

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/signbridge_db")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "signbridge_db")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", 3000))

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "https://api.clerk.dev/v1/jwks")

    # Stripe Payment Gateway
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_PREMIUM_MONTHLY = os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_signbridge_premium_monthly")
    STRIPE_PRICE_LIFETIME = os.getenv("STRIPE_PRICE_LIFETIME", "price_signbridge_lifetime")
    STRIPE_PRICE_CUSTOM_TRAINING = os.getenv("STRIPE_PRICE_CUSTOM_TRAINING", "price_signbridge_custom_training")

    @classmethod
    def log_stripe_version(cls):
        if cls.STRIPE_SECRET_KEY:
            import stripe
            logger = __import__("logging").getLogger("signbridge.config")
            logger.info("Stripe SDK version: %s", getattr(stripe, "_version", "unknown"))
            logger.info("Stripe key type: %s", "test" if cls.STRIPE_SECRET_KEY.startswith("sk_test_") else "live")

    # Exchange Rate for INR display (USD to INR)
    USD_TO_INR_RATE = float(os.getenv("USD_TO_INR_RATE", "83.0"))
    EXCHANGE_RATE_PROVIDER = os.getenv("EXCHANGE_RATE_PROVIDER", "fixed")  # fixed, exchangerate-api, openexchangerates
    EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "")

    # Usage Tracking
    FREE_MONTHLY_ALLOWANCE_SECONDS = int(os.getenv("FREE_MONTHLY_ALLOWANCE_SECONDS", "14400"))  # 4 hours
    USAGE_HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("USAGE_HEARTBEAT_INTERVAL_SECONDS", "30"))
    USAGE_INACTIVITY_TIMEOUT_SECONDS = int(os.getenv("USAGE_INACTIVITY_TIMEOUT_SECONDS", "120"))

    # Subscription Plans
    PLANS = {
        "free": {
            "id": "free",
            "name": "Free",
            "price_usd": 0,
            "price_inr": 0,
            "billing_interval": None,
            "stripe_price_id": None,
            "features": {
                "productive_hours_monthly": 4,
                "productive_seconds_monthly": 14400,
                "languages": ["en"],
                "unlimited_usage": False,
                "ai_assistant": False,
                "custom_training": False,
            },
            "description": "4 productive hours per month, English only",
        },
        "premium": {
            "id": "premium",
            "name": "Premium",
            "price_usd": 29.48,
            "price_inr": 0,  # Calculated dynamically
            "billing_interval": "month",
            "stripe_price_id": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_signbridge_premium_monthly"),
            "features": {
                "productive_hours_monthly": None,
                "productive_seconds_monthly": None,
                "languages": ["en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "or", "as"],
                "unlimited_usage": True,
                "ai_assistant": True,  # Future feature flag
                "custom_training": False,
            },
            "description": "Unlimited usage, all supported languages, AI assistant (coming soon)",
        },
        "lifetime": {
            "id": "lifetime",
            "name": "Lifetime",
            "price_usd": 2000,
            "price_inr": 0,  # Calculated dynamically
            "billing_interval": None,
            "stripe_price_id": os.getenv("STRIPE_PRICE_LIFETIME", "price_signbridge_lifetime"),
            "features": {
                "productive_hours_monthly": None,
                "productive_seconds_monthly": None,
                "languages": ["en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "or", "as", "regional"],
                "unlimited_usage": True,
                "ai_assistant": True,  # Future feature flag
                "custom_training": False,
            },
            "description": "One-time payment, lifetime access, all regional languages",
        },
        "custom_training": {
            "id": "custom_training",
            "name": "Custom Model Training",
            "price_usd": 15,
            "price_inr": 0,  # Calculated dynamically
            "billing_interval": None,
            "stripe_price_id": os.getenv("STRIPE_PRICE_CUSTOM_TRAINING", "price_signbridge_custom_training"),
            "features": {
                "custom_model_request": True,
            },
            "description": "Request a custom sign language model for your language",
        },
    }

    @classmethod
    def get_plan(cls, plan_id):
        """Get plan with calculated INR price."""
        plan = cls.PLANS.get(plan_id)
        if plan and plan["price_usd"] > 0:
            plan = plan.copy()
            plan["price_inr"] = round(plan["price_usd"] * cls.USD_TO_INR_RATE)
        return plan

    @classmethod
    def get_all_plans(cls):
        """Get all plans with calculated INR prices."""
        plans = {}
        for pid, plan in cls.PLANS.items():
            plans[pid] = cls.get_plan(pid)
        return plans

    @classmethod
    def get_user_entitlements(cls, user_plan):
        """Get entitlements for a user's plan."""
        plan = cls.PLANS.get(user_plan, cls.PLANS["free"])
        return plan["features"]
