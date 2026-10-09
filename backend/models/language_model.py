"""
backend/models/language_model.py

Language registry and multilingual access control for SignBridge.
Centralized language configuration with feature support matrix.
"""

from datetime import datetime
from backend.db import db_manager


class LanguageRegistry:
    """Centralized language registry with feature support matrix."""

    # Default language registry - can be overridden by database
    DEFAULT_LANGUAGES = {
        "en": {
            "id": "en",
            "name": "English",
            "native_name": "English",
            "country": "US",
            "region": "North America",
            "variant": "ASL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": True,
                "fingerspelling": True,
            },
            "required_entitlement": "free",
            "model_id": "sign_classifier_asl",
            "validation_status": "production",
            "is_active": True,
            "sort_order": 1,
        },
        "hi": {
            "id": "hi",
            "name": "Hindi",
            "native_name": "हिन्दी",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_hindi",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 2,
        },
        "bn": {
            "id": "bn",
            "name": "Bengali",
            "native_name": "বাংলা",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_bengali",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 3,
        },
        "ta": {
            "id": "ta",
            "name": "Tamil",
            "native_name": "தமிழ்",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_tamil",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 4,
        },
        "te": {
            "id": "te",
            "name": "Telugu",
            "native_name": "తెలుగు",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_telugu",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 5,
        },
        "mr": {
            "id": "mr",
            "name": "Marathi",
            "native_name": "मराठी",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_marathi",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 6,
        },
        "gu": {
            "id": "gu",
            "name": "Gujarati",
            "native_name": "ગુજરાતી",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_gujarati",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 7,
        },
        "kn": {
            "id": "kn",
            "name": "Kannada",
            "native_name": "ಕನ್ನಡ",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_kannada",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 8,
        },
        "ml": {
            "id": "ml",
            "name": "Malayalam",
            "native_name": "മലയാളം",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_malayalam",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 9,
        },
        "pa": {
            "id": "pa",
            "name": "Punjabi",
            "native_name": "ਪੰਜਾਬੀ",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_punjabi",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 10,
        },
        "or": {
            "id": "or",
            "name": "Odia",
            "native_name": "ଓଡ଼ିଆ",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_odia",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 11,
        },
        "as": {
            "id": "as",
            "name": "Assamese",
            "native_name": "অসমীয়া",
            "country": "IN",
            "region": "India",
            "variant": "ISL",
            "status": "supported",
            "features": {
                "sign_recognition": True,
                "text_to_sign": True,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": "sign_classifier_isl_assamese",
            "validation_status": "beta",
            "is_active": True,
            "sort_order": 12,
        },
        "es": {
            "id": "es",
            "name": "Spanish",
            "native_name": "Español",
            "country": "ES",
            "region": "Europe",
            "variant": "LSE",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 13,
        },
        "fr": {
            "id": "fr",
            "name": "French",
            "native_name": "Français",
            "country": "FR",
            "region": "Europe",
            "variant": "LSF",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 14,
        },
        "de": {
            "id": "de",
            "name": "German",
            "native_name": "Deutsch",
            "country": "DE",
            "region": "Europe",
            "variant": "DGS",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 15,
        },
        "zh": {
            "id": "zh",
            "name": "Chinese (Mandarin)",
            "native_name": "中文",
            "country": "CN",
            "region": "Asia",
            "variant": "CSL",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 16,
        },
        "ja": {
            "id": "ja",
            "name": "Japanese",
            "native_name": "日本語",
            "country": "JP",
            "region": "Asia",
            "variant": "JSL",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 17,
        },
        "ko": {
            "id": "ko",
            "name": "Korean",
            "native_name": "한국어",
            "country": "KR",
            "region": "Asia",
            "variant": "KSL",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 18,
        },
        "ar": {
            "id": "ar",
            "name": "Arabic",
            "native_name": "العربية",
            "country": "SA",
            "region": "Middle East",
            "variant": "ArSL",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 19,
        },
        "pt": {
            "id": "pt",
            "name": "Portuguese",
            "native_name": "Português",
            "country": "BR",
            "region": "South America",
            "variant": "Libras",
            "status": "planned",
            "features": {
                "sign_recognition": False,
                "text_to_sign": False,
                "speech_to_text": True,
                "gloss_to_sentence": False,
                "fingerspelling": True,
            },
            "required_entitlement": "premium",
            "model_id": None,
            "validation_status": "not_implemented",
            "is_active": False,
            "sort_order": 20,
        },
    }

    @staticmethod
    def initialize_db():
        """Initialize language registry in database if empty."""
        if db_manager.db["languages"].count_documents({}) == 0:
            for lang in LanguageRegistry.DEFAULT_LANGUAGES.values():
                lang["created_at"] = datetime.utcnow()
                lang["updated_at"] = datetime.utcnow()
                db_manager.db["languages"].insert_one(lang)

    @staticmethod
    def get_all_languages():
        """Get all languages from database (fallback to defaults)."""
        if not db_manager.is_connected:
            return list(LanguageRegistry.DEFAULT_LANGUAGES.values())

        languages = list(db_manager.db["languages"].find({}))
        if not languages:
            LanguageRegistry.initialize_db()
            languages = list(db_manager.db["languages"].find({}))

        # Sort by sort_order
        languages.sort(key=lambda x: x.get("sort_order", 999))
        return languages

    @staticmethod
    def get_language(language_id):
        """Get a specific language by ID."""
        if not db_manager.is_connected:
            return LanguageRegistry.DEFAULT_LANGUAGES.get(language_id)
        return db_manager.db["languages"].find_one({"id": language_id})

    @staticmethod
    def get_supported_languages():
        """Get only supported (active) languages."""
        return [l for l in LanguageRegistry.get_all_languages() if l.get("is_active")]

    @staticmethod
    def get_languages_for_entitlement(entitlement_level):
        """Get languages accessible for a given entitlement level."""
        entitlement_hierarchy = {
            "free": 0,
            "premium": 1,
            "lifetime": 2,
        }
        user_level = entitlement_hierarchy.get(entitlement_level, 0)

        languages = LanguageRegistry.get_supported_languages()
        accessible = []
        for lang in languages:
            required = lang.get("required_entitlement", "free")
            required_level = entitlement_hierarchy.get(required, 0)
            if user_level >= required_level:
                accessible.append(lang)
        return accessible

    @staticmethod
    def update_language(language_id, updates):
        """Update language configuration (admin only)."""
        updates["updated_at"] = datetime.utcnow()
        db_manager.db["languages"].update_one(
            {"id": language_id},
            {"$set": updates}
        )
        return LanguageRegistry.get_language(language_id)

    @staticmethod
    def add_custom_language(language_data):
        """Add a custom trained language (admin only)."""
        language_data.setdefault("id", language_data.get("id", "").lower().replace(" ", "_"))
        language_data.setdefault("status", "custom")
        language_data.setdefault("is_active", True)
        language_data.setdefault("created_at", datetime.utcnow())
        language_data.setdefault("updated_at", datetime.utcnow())
        language_data.setdefault("required_entitlement", "custom")
        db_manager.db["languages"].insert_one(language_data)
        return language_data


class LanguageAccessControl:
    """Language access validation for API endpoints."""

    @staticmethod
    def validate_language_access(user_id, language_code):
        """Validate if user can access a language."""
        language = LanguageRegistry.get_language(language_code)
        if not language:
            return False, {"error": "Language not found", "code": "LANGUAGE_NOT_FOUND"}

        if not language.get("is_active"):
            return False, {"error": "Language not available", "code": "LANGUAGE_INACTIVE"}

        # Check if user has required entitlement
        from backend.models.usage_model import EntitlementModel
        if not EntitlementModel.has_language_access(user_id, language_code):
            return False, {
                "error": "Subscription upgrade required for this language",
                "code": "ENTITLEMENT_REQUIRED",
                "required_plan": language.get("required_entitlement"),
                "language": language
            }

        return True, language

    @staticmethod
    def get_user_accessible_languages(user_id):
        """Get all languages accessible to a user with full details."""
        from backend.models.usage_model import EntitlementModel
        entitlements = EntitlementModel.get_user_entitlements(user_id)
        user_plan = "free"

        # Determine user's effective plan
        if entitlements.get("unlimited_usage") and entitlements.get("custom_training"):
            user_plan = "lifetime"
        elif entitlements.get("unlimited_usage"):
            user_plan = "premium"

        languages = LanguageRegistry.get_languages_for_entitlement(user_plan)
        return languages