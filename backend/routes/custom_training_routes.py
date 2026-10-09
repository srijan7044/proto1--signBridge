"""
backend/routes/custom_training_routes.py

Custom Model Training request API endpoints.
Handles request creation, payment, and status tracking.
"""

import os
from flask import Blueprint, request, g
from backend.utils.clerk_auth import require_auth, optional_auth
from backend.utils.helpers import api_response
from backend.config import Config
from backend.models.custom_training_model import CustomTrainingRequest, UserCustomModel, TrainingPayment
from backend.models.payment_model import PaymentModel
from backend.models.user_model import UserModel
from backend.models.language_model import LanguageRegistry
from backend.db import db_manager
import stripe

custom_training_bp = Blueprint("custom_training", __name__, url_prefix="/api/custom-training")


def get_stripe_key():
    if Config.STRIPE_SECRET_KEY and not Config.STRIPE_SECRET_KEY.startswith("sk_test_signbridge"):
        stripe.api_key = Config.STRIPE_SECRET_KEY
        return True
    return False


@custom_training_bp.get("/check-eligibility")
@require_auth
def check_eligibility():
    """
    Check if the current authenticated user has purchased custom model training
    and view their active/submitted requests.
    """
    user = UserModel.get_by_clerk_id(g.clerk_id)
    if not user:
        return api_response(success=False, error="User not found", status_code=404)

    has_purchased = bool(user.get("custom_training_purchased"))
    if not has_purchased:
        # Check if there is a paid payment in payments or training_payments collections
        paid_payment = db_manager.payments.find_one({
            "user_id": g.clerk_id,
            "plan": "custom_training",
            "status": "paid"
        }) or db_manager.db["training_payments"].find_one({
            "user_id": g.clerk_id,
            "status": "paid"
        })
        if paid_payment:
            has_purchased = True
            UserModel.grant_custom_training_access(g.clerk_id)

    user_requests = CustomTrainingRequest.get_user_requests(g.clerk_id)
    pending_request = next((r for r in user_requests if r.get("status") in ["PAID_PENDING_REVIEW", "UNDER_REVIEW", "TRAINING", "VALIDATING"]), None)

    return api_response(data={
        "has_purchased": has_purchased,
        "has_pending_request": pending_request is not None,
        "user_email": user.get("email", ""),
        "user_name": user.get("display_name") or user.get("first_name") or "",
        "requests": user_requests,
    })


@custom_training_bp.post("/request")
@require_auth
def create_training_request():
    """
    Create a new custom model training request after verified payment.
    Body: {
        "language": "Target Language Name",
        "country": "Country/Region",
        "variant": "Regional Variant (optional)",
        "description": "Model Description",
        "use_case": "Intended Use Case",
        "additional_requirements": "Additional Info (optional)",
        "contact_email": "user@example.com"
    }
    """
    data = request.get_json() or {}

    # Validate required fields
    language = (data.get("language") or "").strip()
    country = (data.get("country") or "").strip()
    description = (data.get("description") or "").strip()
    use_case = (data.get("use_case") or "").strip()
    variant = (data.get("variant") or "").strip()
    additional_reqs = (data.get("additional_requirements") or data.get("dataset_info", {}).get("description") or "").strip()

    if not language:
        return api_response(success=False, error="Target language name is required.", status_code=400)
    if not country:
        return api_response(success=False, error="Country or region is required.", status_code=400)
    if not description:
        return api_response(success=False, error="Model description is required.", status_code=400)
    if not use_case:
        return api_response(success=False, error="Intended use case is required.", status_code=400)

    language_id = (data.get("language_id") or language.lower().replace(" ", "_"))[:30]

    # Verify that the user has a verified custom training purchase
    user = UserModel.get_by_clerk_id(g.clerk_id)
    has_purchased = bool(user and user.get("custom_training_purchased"))

    if not has_purchased:
        paid_payment = db_manager.payments.find_one({
            "user_id": g.clerk_id,
            "plan": "custom_training",
            "status": "paid"
        }) or db_manager.db["training_payments"].find_one({
            "user_id": g.clerk_id,
            "status": "paid"
        })
        if paid_payment:
            has_purchased = True
            UserModel.grant_custom_training_access(g.clerk_id)

    if not has_purchased:
        return api_response(
            success=False,
            error="Payment required: Please purchase Custom Model Training ($15.00) before submitting a request.",
            status_code=403
        )

    # Check for existing pending request for same language
    existing_request = db_manager.db["custom_training_requests"].find_one({
        "user_id": g.clerk_id,
        "language_id": language_id,
        "status": {"$in": ["DRAFT", "PAYMENT_PENDING", "PAID_PENDING_REVIEW", "UNDER_REVIEW", "TRAINING", "VALIDATING"]}
    })
    if existing_request:
        return api_response(
            success=False,
            error=f"You already have a pending training request for '{language}'.",
            data={"existing_request_id": existing_request["request_id"]},
            status_code=400
        )

    language_data = {
        "language": language,
        "language_id": language_id,
        "country": country,
        "variant": variant,
    }

    dataset_info = {
        "description": additional_reqs,
        "contact_email": data.get("contact_email") or (user.get("email") if user else ""),
        "use_case": use_case,
    }

    request_obj = CustomTrainingRequest.create_request(
        g.clerk_id,
        language_data,
        f"{description}\n\nUse Case: {use_case}",
        dataset_info
    )

    # Set status to PAID_PENDING_REVIEW and payment_status to paid since user is verified
    CustomTrainingRequest.update_payment_info(request_obj["request_id"], session_id="verified_user_purchase")
    request_obj = CustomTrainingRequest.get_request(request_obj["request_id"])

    return api_response(
        data={"request": request_obj},
        message="Custom Model Training request submitted successfully! Our engineers will review it shortly."
    )


@custom_training_bp.get("/requests")
@require_auth
def get_user_requests():
    """Get all custom training requests for current user."""
    requests = CustomTrainingRequest.get_user_requests(g.clerk_id)
    return api_response(data={"requests": requests})


@custom_training_bp.get("/request/<request_id>")
@require_auth
def get_request(request_id):
    """Get a specific training request."""
    request_obj = CustomTrainingRequest.get_request(request_id)
    if not request_obj:
        return api_response(success=False, error="Request not found", status_code=404)

    # Verify ownership
    if request_obj["user_id"] != g.clerk_id:
        return api_response(success=False, error="Unauthorized", status_code=403)

    return api_response(data={"request": request_obj})


@custom_training_bp.post("/request/<request_id>/checkout")
@require_auth
def create_training_checkout(request_id):
    """Create Stripe Checkout session for custom training payment."""
    request_obj = CustomTrainingRequest.get_request(request_id)
    if not request_obj:
        return api_response(success=False, error="Request not found", status_code=404)

    if request_obj["user_id"] != g.clerk_id:
        return api_response(success=False, error="Unauthorized", status_code=403)

    if request_obj["status"] not in ["DRAFT", "PAYMENT_PENDING"]:
        return api_response(success=False, error="Request cannot be paid at this stage", status_code=400)

    # Get user email
    user = UserModel.get_by_clerk_id(g.clerk_id)
    email = user.get("email") if user else ""

    # Development mode simulation
    if not get_stripe_key():
        import uuid
        mock_session_id = f"cs_test_training_{uuid.uuid4().hex[:12]}"
        TrainingPayment.record_payment(g.clerk_id, request_id, mock_session_id, 15, "usd")
        CustomTrainingRequest.update_status(request_id, "PAYMENT_PENDING")
        return api_response(
            data={
                "session_id": mock_session_id,
                "checkout_url": f"/app.html?payment=success&session_id={mock_session_id}&plan=custom_training",
                "simulated": True,
            },
            message="Training checkout session initialized (Development Simulation mode)."
        )

    try:
        host_url = request.host_url.rstrip("/")
        plan = Config.PLANS["custom_training"]

        price_data = {
            "currency": "usd",
            "product_data": {
                "name": plan["name"],
                "description": f"Custom model training for {request_obj['language']}",
                "tax_code": "txcd_10000000",
            },
            "unit_amount": int(plan["price_usd"] * 100),
        }

        session = stripe.checkout.Session.create(
            line_items=[{"price_data": price_data, "quantity": 1}],
            mode="payment",
            customer_email=email if email else None,
            client_reference_id=g.clerk_id,
            metadata={
                "plan_id": "custom_training",
                "clerk_id": g.clerk_id,
                "request_id": request_id,
            },
            success_url=f"{host_url}/app.html?payment=success&session_id={{CHECKOUT_SESSION_ID}}&plan=custom_training",
            cancel_url=f"{host_url}/app.html?canceled=true",
        )

        TrainingPayment.record_payment(g.clerk_id, request_id, session.id, 15, "usd")
        CustomTrainingRequest.update_status(request_id, "PAYMENT_PENDING")

        return api_response(data={"checkout_url": session.url, "session_id": session.id})

    except stripe.error.StripeError as e:
        return api_response(success=False, error=str(e), status_code=500)


@custom_training_bp.post("/verify-payment")
@require_auth
def verify_training_payment():
    """Verify a custom training payment."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    request_id = data.get("request_id")

    if not session_id:
        return api_response(success=False, error="Missing session_id", status_code=400)

    if get_stripe_key():
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status != "paid":
                return api_response(
                    success=False,
                    message="Payment not completed",
                    data={"payment_status": session.payment_status},
                    status_code=400
                )

            payment_intent_id = session.get("payment_intent")
            if request_id:
                CustomTrainingRequest.update_payment_info(request_id, session_id, payment_intent_id)
            TrainingPayment.update_payment_status(session_id, "paid", payment_intent_id)
            UserModel.grant_custom_training_access(g.clerk_id)

            return api_response(
                data={
                    "session_id": session.id,
                    "payment_status": session.payment_status,
                    "verified": True,
                }
            )
        except Exception as e:
            return api_response(success=False, error=str(e), status_code=500)
    else:
        # Development mode
        payment = TrainingPayment.get_payment_by_session(session_id) or PaymentModel.get_payment(session_id)
        if payment:
            TrainingPayment.update_payment_status(session_id, "paid")
            if request_id:
                CustomTrainingRequest.update_payment_info(request_id, session_id)
            UserModel.grant_custom_training_access(g.clerk_id)
            return api_response(
                data={"session_id": session_id, "payment_status": "paid", "verified": True}
            )
        return api_response(success=False, error="Session not found", status_code=404)


# ============================================================================
# USER-OWNED CUSTOM MODEL WORKSPACE ENDPOINTS
# ============================================================================

@custom_training_bp.get("/workspaces")
@require_auth
def get_user_workspaces():
    """Get all custom model workspaces owned by the authenticated user."""
    workspaces = UserCustomModel.get_all_workspaces(g.clerk_id)
    for w in workspaces:
        w["_id"] = str(w["_id"])
    return api_response(data={"workspaces": workspaces})


@custom_training_bp.get("/workspace/<model_id>")
@require_auth
def get_user_workspace(model_id):
    """Get a specific custom model workspace (owner verification enforced)."""
    workspace = UserCustomModel.get_workspace(g.clerk_id, model_id)
    if not workspace:
        return api_response(success=False, error="Workspace not found or access denied.", status_code=404)
    workspace["_id"] = str(workspace["_id"])
    return api_response(data={"workspace": workspace})


@custom_training_bp.post("/workspace/<model_id>/labels")
@require_auth
def set_workspace_labels(model_id):
    """Configure target letters/labels for the user workspace."""
    data = request.get_json() or {}
    labels = data.get("labels", [])
    target_samples = int(data.get("target_samples_per_label", 30))
    workspace, err = UserCustomModel.update_labels(g.clerk_id, model_id, labels, target_samples)
    if err:
        return api_response(success=False, error=err, status_code=400)
    workspace["_id"] = str(workspace["_id"])
    return api_response(data={"workspace": workspace}, message="Target labels configured successfully.")


@custom_training_bp.post("/workspace/<model_id>/collect-sample")
@require_auth
def collect_workspace_sample(model_id):
    """
    Add a training sample (camera image frame or extracted feature vector)
    associated with model_id, user_id, and label.
    """
    label = request.form.get("label") or (request.get_json() or {}).get("label")
    if not label:
        return api_response(success=False, error="Target label is required", status_code=400)

    feature_vector = None
    if "image" in request.files:
        try:
            import io, cv2, numpy as np
            from PIL import Image
            from utils import create_hands_detector, extract_feature_vector

            file = request.files["image"]
            image_bytes = file.read()
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_np = np.array(pil_img)

            detector = create_hands_detector(static_image_mode=True, max_num_hands=2)
            results = detector.process(image_np)
            detector.close()

            if not results.multi_hand_landmarks:
                return api_response(success=False, error="No hands detected in image frame. Please adjust hand positioning.", status_code=400)

            feature_vector = extract_feature_vector(results.multi_hand_landmarks, results.multi_handedness).tolist()
        except Exception as e:
            return api_response(success=False, error=f"Feature extraction failed: {e}", status_code=400)
    else:
        data = request.get_json() or {}
        feature_vector = data.get("feature_vector")

    if not feature_vector:
        return api_response(success=False, error="No feature vector or camera image frame provided", status_code=400)

    workspace, err = UserCustomModel.add_sample(g.clerk_id, model_id, label, feature_vector)
    if err:
        return api_response(success=False, error=err, status_code=400)

    workspace["_id"] = str(workspace["_id"])
    return api_response(data={"workspace": workspace, "collected_label": str(label).upper()})


@custom_training_bp.post("/workspace/<model_id>/train")
@require_auth
def train_workspace_model(model_id):
    """Train Random Forest classifier on the model owner's dataset."""
    workspace, err = UserCustomModel.train_model(g.clerk_id, model_id)
    if err:
        return api_response(success=False, error=err, status_code=400)
    workspace["_id"] = str(workspace["_id"])
    return api_response(
        data={"workspace": workspace},
        message=f"Model successfully trained! Version {workspace.get('version', 1)} is ready for testing."
    )


@custom_training_bp.post("/workspace/<model_id>/predict")
@require_auth
def predict_workspace_model(model_id):
    """Perform real-time prediction using the user's trained custom model."""
    workspace = UserCustomModel.get_workspace(g.clerk_id, model_id)
    if not workspace or workspace.get("status") != "trained" or not workspace.get("model_path"):
        return api_response(success=False, error="Model is not trained yet or unavailable", status_code=400)

    model_path = workspace["model_path"]
    if not os.path.exists(model_path):
        return api_response(success=False, error="Trained model artifact missing from storage.", status_code=404)

    if "image" not in request.files:
        return api_response(success=False, error="No image frame uploaded.", status_code=400)

    try:
        import io, cv2, numpy as np, joblib
        from PIL import Image
        from utils import create_hands_detector, extract_feature_vector

        file = request.files["image"]
        image_bytes = file.read()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(pil_img)

        detector = create_hands_detector(static_image_mode=True, max_num_hands=2)
        results = detector.process(image_np)
        detector.close()

        if not results.multi_hand_landmarks:
            return api_response(data={"label": None, "confidence": 0.0, "message": "No hand detected"})

        feats = extract_feature_vector(results.multi_hand_landmarks, results.multi_handedness)

        loaded = joblib.load(model_path)
        clf = loaded["model"] if isinstance(loaded, dict) else loaded
        labels = loaded["labels"] if isinstance(loaded, dict) and "labels" in loaded else list(clf.classes_)

        proba = clf.predict_proba([feats])[0]
        best_idx = int(np.argmax(proba))
        predicted_label = str(clf.classes_[best_idx])
        confidence = float(proba[best_idx])

        return api_response(data={
            "label": predicted_label,
            "confidence": round(confidence, 3),
            "model_id": model_id,
            "version": workspace.get("version", 1)
        })
    except Exception as e:
        return api_response(success=False, error=f"Prediction failed: {e}", status_code=500)