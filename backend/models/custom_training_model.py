"""
backend/models/custom_training_model.py

Custom Model Training request management with admin review workflow.
Handles training requests, payments, admin review, and model activation.
"""

from datetime import datetime
from backend.db import db_manager
import uuid


class CustomTrainingRequest:
    """Model for custom model training requests."""

    # Valid states in the workflow
    STATES = [
        "DRAFT",
        "PAYMENT_PENDING",
        "PAID_PENDING_REVIEW",
        "UNDER_REVIEW",
        "NEEDS_INFORMATION",
        "TRAINING",
        "VALIDATING",
        "APPROVED",
        "REJECTED",
        "REFUNDED",
    ]

    # Valid transitions
    VALID_TRANSITIONS = {
        "DRAFT": ["PAYMENT_PENDING", "REJECTED"],
        "PAYMENT_PENDING": ["PAID_PENDING_REVIEW", "REJECTED", "DRAFT"],
        # Admin can move directly to UNDER_REVIEW, skip to TRAINING, request info, reject,
        # or fast-approve a simple request without a separate review step.
        "PAID_PENDING_REVIEW": ["UNDER_REVIEW", "TRAINING", "NEEDS_INFORMATION", "APPROVED", "REJECTED"],
        "UNDER_REVIEW": ["TRAINING", "NEEDS_INFORMATION", "APPROVED", "REJECTED"],
        # NEEDS_INFORMATION: admin read user's clarification → can move back to review or approve directly.
        "NEEDS_INFORMATION": ["PAID_PENDING_REVIEW", "UNDER_REVIEW", "APPROVED", "REJECTED"],
        "TRAINING": ["VALIDATING", "NEEDS_INFORMATION", "REJECTED"],
        "VALIDATING": ["APPROVED", "REJECTED", "NEEDS_INFORMATION", "TRAINING"],
        "APPROVED": ["REJECTED"],  # Only admin can revoke after approval
        "REJECTED": ["PAID_PENDING_REVIEW"],  # User can request re-review after rejection
        "REFUNDED": [],
    }

    @staticmethod
    def create_request(user_id, language_data, use_case, dataset_info=None):
        """Create a new custom training request (draft state)."""
        now = datetime.utcnow()
        request = {
            "request_id": str(uuid.uuid4()),
            "user_id": user_id,
            "language": language_data.get("language", "").strip(),
            "language_id": language_data.get("language_id", "").lower().replace(" ", "_"),
            "country": language_data.get("country", ""),
            "variant": language_data.get("variant", ""),
            "description": use_case,
            "dataset_info": dataset_info or {},
            "status": "DRAFT",
            "payment_status": "pending",
            "stripe_session_id": None,
            "stripe_payment_intent_id": None,
            "admin_notes": "",
            "reviewed_by": None,
            "reviewed_at": None,
            "training_started_at": None,
            "training_completed_at": None,
            "model_metadata": {},
            "validation_metrics": {},
            "created_at": now,
            "updated_at": now,
        }
        res = db_manager.db["custom_training_requests"].insert_one(request)
        request["_id"] = str(res.inserted_id)
        return request

    @staticmethod
    def get_request(request_id):
        """Get a training request by ID."""
        return db_manager.db["custom_training_requests"].find_one({"request_id": request_id})

    @staticmethod
    def get_user_requests(user_id):
        """Get all training requests for a user."""
        return list(db_manager.db["custom_training_requests"].find({"user_id": user_id}).sort("created_at", -1))

    @staticmethod
    def get_all_requests(status_filter=None):
        """Get all training requests (admin)."""
        query = {}
        if status_filter:
            query["status"] = status_filter
        return list(db_manager.db["custom_training_requests"].find(query).sort("created_at", -1))

    @staticmethod
    def update_status(request_id, new_status, admin_id=None, notes=None):
        """Update request status with validation."""
        request = CustomTrainingRequest.get_request(request_id)
        if not request:
            return None, {"error": "Request not found"}

        current_status = request["status"]
        valid_next = CustomTrainingRequest.VALID_TRANSITIONS.get(current_status, [])

        if new_status not in valid_next:
            return None, {
                "error": f"Invalid transition from {current_status} to {new_status}",
                "valid_transitions": valid_next
            }

        update = {"status": new_status, "updated_at": datetime.utcnow()}
        if admin_id:
            update["reviewed_by"] = admin_id
            update["reviewed_at"] = datetime.utcnow()
        if notes:
            update["admin_notes"] = notes

        if new_status == "TRAINING":
            update["training_started_at"] = datetime.utcnow()
        elif new_status == "APPROVED":
            update["training_completed_at"] = datetime.utcnow()

        db_manager.db["custom_training_requests"].update_one(
            {"request_id": request_id},
            {"$set": update}
        )

        if new_status == "APPROVED":
            UserCustomModel.initialize_workspace(request["user_id"], request_id)

        return CustomTrainingRequest.get_request(request_id), None

    @staticmethod
    def update_payment_info(request_id, session_id, payment_intent_id=None):
        """Update payment information after checkout."""
        update = {
            "payment_status": "paid",
            "stripe_session_id": session_id,
            "status": "PAID_PENDING_REVIEW",
            "updated_at": datetime.utcnow(),
        }
        if payment_intent_id:
            update["stripe_payment_intent_id"] = payment_intent_id

        db_manager.db["custom_training_requests"].update_one(
            {"request_id": request_id},
            {"$set": update}
        )
        return CustomTrainingRequest.get_request(request_id)

    @staticmethod
    def update_training_results(request_id, model_metadata, validation_metrics):
        """Update training results and validation metrics."""
        update = {
            "model_metadata": model_metadata,
            "validation_metrics": validation_metrics,
            "status": "VALIDATING",
            "updated_at": datetime.utcnow(),
        }
        db_manager.db["custom_training_requests"].update_one(
            {"request_id": request_id},
            {"$set": update}
        )
        return CustomTrainingRequest.get_request(request_id)

    @staticmethod
    def approve_model(request_id, admin_id, model_path, admin_notes=""):
        """Approve a trained model for production use."""
        request = CustomTrainingRequest.get_request(request_id)
        if not request:
            return None, {"error": "Request not found"}

        if request["status"] not in ["VALIDATING", "TRAINING", "UNDER_REVIEW", "PAID_PENDING_REVIEW"]:
            return None, {"error": f"Cannot approve from status {request['status']}"}

        update = {
            "status": "APPROVED",
            "model_metadata": {**request.get("model_metadata", {}), "model_path": model_path, "approved_at": datetime.utcnow().isoformat()},
            "reviewed_by": admin_id,
            "reviewed_at": datetime.utcnow(),
            "admin_notes": admin_notes,
            "updated_at": datetime.utcnow(),
        }
        db_manager.db["custom_training_requests"].update_one(
            {"request_id": request_id},
            {"$set": update}
        )

        # Grant user access to custom language and initialize workspace
        UserCustomModel.grant_access(request["user_id"], request["language_id"], request_id)
        UserCustomModel.initialize_workspace(request["user_id"], request_id)

        return CustomTrainingRequest.get_request(request_id), None

    @staticmethod
    def reject_request(request_id, admin_id, reason):
        """Reject a training request."""
        request = CustomTrainingRequest.get_request(request_id)
        if not request:
            return None, {"error": "Request not found"}

        update = {
            "status": "REJECTED",
            "reviewed_by": admin_id,
            "reviewed_at": datetime.utcnow(),
            "admin_notes": reason,
            "updated_at": datetime.utcnow(),
        }
        db_manager.db["custom_training_requests"].update_one(
            {"request_id": request_id},
            {"$set": update}
        )
        return CustomTrainingRequest.get_request(request_id), None


class UserCustomModel:
    """Model for tracking and managing user's approved custom model workspaces."""

    @staticmethod
    def grant_access(user_id, language_id, request_id):
        """Grant user access to their approved custom model."""
        now = datetime.utcnow()
        access = {
            "user_id": user_id,
            "language_id": language_id,
            "request_id": request_id,
            "granted_at": now,
            "is_active": True,
        }
        db_manager.db["user_custom_models"].update_one(
            {"user_id": user_id, "language_id": language_id},
            {"$set": access},
            upsert=True
        )
        return access

    @staticmethod
    def initialize_workspace(user_id, request_id):
        """
        Initialize an isolated custom model workspace for an approved request.
        Idempotent: returns existing workspace if already initialized.
        """
        request_obj = CustomTrainingRequest.get_request(request_id)
        if not request_obj:
            return None

        # Check if workspace already exists
        existing = db_manager.db["custom_models"].find_one({
            "user_id": user_id,
            "request_id": request_id
        })
        if existing:
            return existing

        import uuid
        model_id = f"cm_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        workspace = {
            "model_id": model_id,
            "user_id": user_id,
            "request_id": request_id,
            "name": f"Custom Model - {request_obj.get('language', 'Signs')}",
            "language": request_obj.get("language", "Custom"),
            "language_id": request_obj.get("language_id", "custom_lang"),
            "status": "awaiting_data",  # awaiting_data -> collecting_samples -> ready_to_train -> training -> trained -> failed
            "labels": ["A", "B", "C", "D", "E"],
            "target_samples_per_label": 30,
            "sample_counts": {},
            "version": 1,
            "model_path": None,
            "metrics": {},
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }

        db_manager.db["custom_models"].insert_one(workspace)
        UserCustomModel.grant_access(user_id, workspace["language_id"], request_id)
        return workspace

    @staticmethod
    def get_workspace(user_id, model_id):
        """Get a user's custom model workspace by model_id."""
        return db_manager.db["custom_models"].find_one({
            "model_id": model_id,
            "user_id": user_id
        })

    @staticmethod
    def get_all_workspaces(user_id):
        """Get all custom model workspaces owned by a user."""
        return list(db_manager.db["custom_models"].find({"user_id": user_id}).sort("created_at", -1))

    @staticmethod
    def update_labels(user_id, model_id, labels, target_samples=30):
        """Configure target letters/labels for the workspace."""
        workspace = UserCustomModel.get_workspace(user_id, model_id)
        if not workspace:
            return None, "Workspace not found"

        clean_labels = [str(lbl).strip().upper() for lbl in labels if str(lbl).strip()]
        if len(clean_labels) < 2:
            return None, "At least 2 labels are required for training"

        update = {
            "labels": clean_labels,
            "target_samples_per_label": max(10, min(100, target_samples)),
            "status": "collecting_samples",
            "updated_at": datetime.utcnow()
        }

        db_manager.db["custom_models"].update_one(
            {"model_id": model_id, "user_id": user_id},
            {"$set": update}
        )
        return UserCustomModel.get_workspace(user_id, model_id), None

    @staticmethod
    def add_sample(user_id, model_id, label, feature_vector):
        """Add a landmark feature vector sample to the dataset."""
        workspace = UserCustomModel.get_workspace(user_id, model_id)
        if not workspace:
            return None, "Workspace not found"

        clean_label = str(label).strip().upper()
        if clean_label not in workspace.get("labels", []):
            return None, f"Label '{clean_label}' is not in configured target labels"

        if not isinstance(feature_vector, (list, tuple)) or len(feature_vector) != 126:
            return None, "Feature vector must contain exactly 126 numbers"

        sample = {
            "model_id": model_id,
            "user_id": user_id,
            "label": clean_label,
            "feature_vector": [float(x) for x in feature_vector],
            "created_at": datetime.utcnow()
        }
        db_manager.db["custom_model_samples"].insert_one(sample)

        # Update sample counts
        counts = workspace.get("sample_counts", {})
        counts[clean_label] = counts.get(clean_label, 0) + 1

        # Check if ready to train
        target = workspace.get("target_samples_per_label", 30)
        labels = workspace.get("labels", [])
        sufficient_classes = sum(1 for l in labels if counts.get(l, 0) >= 10)
        
        new_status = workspace.get("status")
        if sufficient_classes >= 2:
            new_status = "ready_to_train"
        else:
            new_status = "collecting_samples"

        db_manager.db["custom_models"].update_one(
            {"model_id": model_id, "user_id": user_id},
            {"$set": {
                "sample_counts": counts,
                "status": new_status,
                "updated_at": datetime.utcnow()
            }}
        )

        return UserCustomModel.get_workspace(user_id, model_id), None

    @staticmethod
    def train_model(user_id, model_id):
        """Train Random Forest classifier on user's collected dataset."""
        import os
        import re
        import joblib
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score
        from backend.config import Config

        workspace = UserCustomModel.get_workspace(user_id, model_id)
        if not workspace:
            return None, "Workspace not found"

        # Fetch samples
        samples = list(db_manager.db["custom_model_samples"].find({
            "model_id": model_id,
            "user_id": user_id
        }))

        if len(samples) < 10:
            return None, "Insufficient samples for training. Collect at least 10 samples per label."

        X = np.array([s["feature_vector"] for s in samples], dtype=np.float32)
        y = np.array([s["label"] for s in samples])

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            return None, "At least 2 unique classes are required to train a classifier model."

        # Mark as training
        db_manager.db["custom_models"].update_one(
            {"model_id": model_id, "user_id": user_id},
            {"$set": {"status": "training", "updated_at": datetime.utcnow()}}
        )

        try:
            # Train Random Forest Classifier
            clf = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                class_weight="balanced",
                random_state=42
            )

            acc = 1.0
            if len(X) >= 20:
                X_tr, X_val, y_tr, y_val = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y if len(unique_classes) > 1 else None
                )
                clf.fit(X_tr, y_tr)
                preds = clf.predict(X_val)
                acc = float(accuracy_score(y_val, preds))
            else:
                clf.fit(X, y)

            # Sanitize paths to prevent traversal
            safe_uid = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
            safe_mid = re.sub(r'[^a-zA-Z0-9_-]', '_', model_id)

            user_model_dir = os.path.join(Config.MODEL_DIR, "custom", safe_uid)
            os.makedirs(user_model_dir, exist_ok=True)

            model_file_path = os.path.join(user_model_dir, f"{safe_mid}.joblib")

            model_artifact = {
                "model": clf,
                "labels": sorted(list(unique_classes)),
                "version": workspace.get("version", 1)
            }
            joblib.dump(model_artifact, model_file_path)

            new_version = workspace.get("version", 1) + 1
            metrics = {
                "accuracy": round(acc * 100, 1),
                "num_samples": len(samples),
                "num_classes": len(unique_classes),
                "labels": list(unique_classes),
                "trained_at": datetime.utcnow().isoformat()
            }

            db_manager.db["custom_models"].update_one(
                {"model_id": model_id, "user_id": user_id},
                {"$set": {
                    "status": "trained",
                    "model_path": model_file_path,
                    "version": new_version,
                    "metrics": metrics,
                    "error_message": None,
                    "updated_at": datetime.utcnow()
                }}
            )

            return UserCustomModel.get_workspace(user_id, model_id), None

        except Exception as e:
            db_manager.db["custom_models"].update_one(
                {"model_id": model_id, "user_id": user_id},
                {"$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.utcnow()
                }}
            )
            return None, f"Training failed: {e}"

    @staticmethod
    def get_user_models(user_id):
        """Get all approved custom models for a user."""
        return list(db_manager.db["user_custom_models"].find({"user_id": user_id, "is_active": True}))

    @staticmethod
    def has_access(user_id, language_id):
        """Check if user has access to a custom language."""
        access = db_manager.db["user_custom_models"].find_one({
            "user_id": user_id,
            "language_id": language_id,
            "is_active": True
        })
        return access is not None

    @staticmethod
    def revoke_access(user_id, language_id):
        """Revoke user's access to a custom model (admin only)."""
        db_manager.db["user_custom_models"].update_one(
            {"user_id": user_id, "language_id": language_id},
            {"$set": {"is_active": False, "revoked_at": datetime.utcnow()}}
        )

        """Revoke user's access to a custom model (admin only)."""
        db_manager.db["user_custom_models"].update_one(
            {"user_id": user_id, "language_id": language_id},
            {"$set": {"is_active": False, "revoked_at": datetime.utcnow()}}
        )


class TrainingPayment:
    """Model for tracking custom training payments."""

    @staticmethod
    def record_payment(user_id, request_id, session_id, amount_usd=15, currency="usd"):
        """Record a training payment."""
        payment = {
            "payment_id": str(uuid.uuid4()),
            "user_id": user_id,
            "request_id": request_id,
            "session_id": session_id,
            "amount_usd": amount_usd,
            "currency": currency,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        res = db_manager.db["training_payments"].insert_one(payment)
        payment["_id"] = str(res.inserted_id)
        return payment

    @staticmethod
    def update_payment_status(session_id, status, payment_intent_id=None):
        """Update payment status."""
        update = {"status": status, "updated_at": datetime.utcnow()}
        if payment_intent_id:
            update["payment_intent_id"] = payment_intent_id
        db_manager.db["training_payments"].update_one(
            {"session_id": session_id},
            {"$set": update}
        )
        return db_manager.db["training_payments"].find_one({"session_id": session_id})

    @staticmethod
    def get_payment_by_session(session_id):
        """Get payment by Stripe session ID."""
        return db_manager.db["training_payments"].find_one({"session_id": session_id})