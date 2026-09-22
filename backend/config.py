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
    STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_signbridge_pro_monthly")
    STRIPE_PRICE_LIFETIME = os.getenv("STRIPE_PRICE_LIFETIME", "price_signbridge_lifetime")

    # Pricing Tiers
    PLANS = {
        "free": {
            "name": "Free Tier",
            "price": 0,
            "features": ["Sign-to-Speech (Standard)", "Speech-to-Sign (Basic)", "Community Signs"],
        },
        "pro_monthly": {
            "name": "SignBridge Pro (Monthly)",
            "price": 9.99,
            "currency": "usd",
            "stripe_price_id": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_signbridge_pro_monthly"),
            "features": [
                "Unlimited Live AI Sign Translation",
                "Advanced Indian & Regional Signs (ISL)",
                "Full Natural Grammar Synthesizer",
                "Priority Speech Audio & Offline Mode",
            ],
        },
        "lifetime": {
            "name": "SignBridge Lifetime Access",
            "price": 79.99,
            "currency": "usd",
            "stripe_price_id": os.getenv("STRIPE_PRICE_LIFETIME", "price_signbridge_lifetime"),
            "features": [
                "Lifetime Access to All Current & Future Features",
                "All Regional Sign Language Packs",
                "Direct API & Developer Access",
                "VIP Support",
            ],
        },
    }
