"""
backend/routes/translate_routes.py

Real-time sign prediction, text-to-sign animation sequence generation,
and gloss-to-sentence grammar synthesis.
"""

import os
import io
import cv2
import numpy as np
import joblib
from PIL import Image
from flask import Blueprint, request, g, jsonify
import base64
import logging
from backend.config import Config
from backend.models.history_model import HistoryModel
from backend.db import db_manager
from backend.utils.clerk_auth import optional_auth
from backend.utils.helpers import api_response
from utils import (
    create_hands_detector,
    extract_feature_vector,
    mp_drawing,
    mp_hands,
    mp_drawing_styles,
)
from backend.utils.word_engine import gloss_to_sentence, get_predictive_suggestions

logger = logging.getLogger("signbridge.translate")

def encode_image(frame_bgr):
    ok, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None
    return base64.b64encode(buffer).decode("utf-8")

translate_bp = Blueprint("translate", __name__, url_prefix="/api")

# Lazy-loaded model state
_model = None
_labels = None
_detector = None


def get_detector():
    global _detector
    if _detector is None:
        _detector = create_hands_detector(max_num_hands=2)
    return _detector


def load_model():
    global _model, _labels
    if _model is None:
        if not os.path.exists(Config.MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {Config.MODEL_PATH}.")
        loaded = joblib.load(Config.MODEL_PATH)
        _model = loaded["model"] if isinstance(loaded, dict) else loaded
        _labels = joblib.load(Config.LABELS_PATH) if os.path.exists(Config.LABELS_PATH) else list(_model.classes_)
    return _model, _labels


@translate_bp.get("/health")
def health_check():
    """System health check endpoint."""
    model_loaded = os.path.exists(Config.MODEL_PATH)
    labels_count = len(_labels) if _labels else (len(joblib.load(Config.LABELS_PATH)) if os.path.exists(Config.LABELS_PATH) else 0)
    db_health = db_manager.health_check()
    return api_response(
        data={
            "status": "healthy",
            "model_ready": model_loaded,
            "labels_count": labels_count,
            "database": db_health,
        }
    )


@translate_bp.get("/labels")
def list_labels():
    """Returns the list of signs recognized by the model."""
    try:
        _, labels = load_model()
        return api_response(data={"labels": sorted(list(labels)), "count": len(labels)})
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@translate_bp.post("/predict")
def predict_frame():
    """
    Accepts an uploaded image/frame and returns predicted sign, confidence, and annotated preview.
    """
    if "image" not in request.files:
        return api_response(success=False, error="No image file provided in form-data.", status_code=400)

    try:
        model, _ = load_model()
    except Exception as e:
        return api_response(success=False, error=f"Classifier unavailable: {e}", status_code=500)

    file = request.files["image"]
    image_bytes = file.read()
    if not image_bytes:
        return api_response(success=False, error="Empty image frame received.", status_code=400)

    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(pil_img)
        h, w, _ = image_np.shape

        detector = get_detector()
        results = detector.process(image_np)

        label = None
        confidence = 0.0

        if results.multi_hand_landmarks:
            feats = extract_feature_vector(
                results.multi_hand_landmarks, results.multi_handedness
            )
            proba = model.predict_proba([feats])[0]
            best_idx = int(np.argmax(proba))
            label = str(model.classes_[best_idx])
            confidence = float(proba[best_idx])

        return jsonify({
            "label": label,
            "confidence": confidence,
            "image": None,
        })
    except Exception as e:
        logger.exception("Prediction failed")
        return api_response(success=False, error=f"Prediction failed: {e}", status_code=500)


@translate_bp.post("/text-to-sign")
def text_to_sign_api():
    """
    Translates spoken or typed text into a 3D animated skeleton sequence.
    """
    data = request.get_json() or {}
    sentence = data.get("sentence", "").strip()
    if not sentence:
        return api_response(success=False, error="Please enter or speak a sentence first.", status_code=400)

    try:
        from text_to_sign import sentence_to_gloss, build_sequence
        gloss = sentence_to_gloss(sentence)
        frames, spans = build_sequence(gloss)

        frames_list = frames.tolist() if len(frames) > 0 else []
        spans_list = [{"word": w, "start": int(s), "end": int(e)} for w, s, e in spans]

        return jsonify({
            "sentence": sentence,
            "gloss": gloss,
            "num_frames": len(frames_list),
            "frames": frames_list,
            "spans": spans_list,
        })
    except Exception as e:
        logger.exception("Text-to-sign failed")
        return api_response(success=False, error=f"Generation failed: {e}", status_code=500)


@translate_bp.post("/gloss-to-sentence")
@optional_auth
def gloss_to_sentence_api():
    """
    Translates a sequence of sign gloss words into a natural, grammatically
    fluent English sentence and provides predictive suggestion chips.
    """
    data = request.get_json() or {}
    gloss = data.get("gloss", "")
    try:
        sentence = gloss_to_sentence(gloss)
        suggestions = get_predictive_suggestions(gloss)

        # Log conversation if user is authenticated
        if g.clerk_id and sentence:
            HistoryModel.log_translation(
                user_id=g.clerk_id,
                raw_gloss=gloss,
                translated_sentence=sentence
            )

        return jsonify({
            "gloss": gloss,
            "sentence": sentence,
            "suggestions": suggestions,
        })
    except Exception as e:
        logger.exception("Gloss to sentence failed")
        return api_response(success=False, error=f"Grammar synthesis failed: {e}", status_code=500)


@translate_bp.get("/history")
@optional_auth
def get_history():
    """Returns recent translation history."""
    history = HistoryModel.get_recent_history(user_id=g.clerk_id, limit=25)
    return api_response(data=history)
