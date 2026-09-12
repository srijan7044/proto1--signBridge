"""Flask API and web server for the sign language translator."""

import base64
import io
import os

import cv2
import joblib
import numpy as np
from flask import Flask, jsonify, render_template, request

from utils import create_hands_detector, extract_feature_vector, mp_drawing, mp_drawing_styles, mp_hands

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model", "sign_classifier.joblib")
LABELS_PATH = os.path.join(BASE_DIR, "model", "labels.joblib")

app = Flask(__name__, template_folder="web", static_folder="web", static_url_path="/static")
_model = None
_labels = []
_detector = None


def load_model():
    global _model, _labels
    if _model is not None:
        return _model, _labels
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("No trained model found. Run train_model.py first.")

    loaded = joblib.load(MODEL_PATH)
    if isinstance(loaded, dict):
        _model = loaded.get("model")
        _labels = list(loaded.get("labels", []))
    else:
        _model = loaded
        if os.path.exists(LABELS_PATH):
            _labels = list(joblib.load(LABELS_PATH))

    model_labels = list(getattr(_model, "classes_", []))
    _labels = model_labels or _labels
    if _model is None or not hasattr(_model, "predict_proba"):
        raise ValueError("The saved model is not a usable classifier.")
    return _model, _labels


def get_detector():
    global _detector
    if _detector is None:
        _detector = create_hands_detector(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
    return _detector


def recognize(image_bytes):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The uploaded file is not a readable image.")

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = get_detector().process(rgb_image)
    annotated = rgb_image.copy()
    if not result.multi_hand_landmarks:
        return annotated, None, 0.0

    for hand_landmarks in result.multi_hand_landmarks:
        mp_drawing.draw_landmarks(
            annotated,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style(),
        )

    model, labels = load_model()
    features = extract_feature_vector(result.multi_hand_landmarks, result.multi_handedness)
    probabilities = model.predict_proba([features])[0]
    best_index = int(np.argmax(probabilities))
    confidence = float(probabilities[best_index])
    label = str(model.classes_[best_index]) if hasattr(model, "classes_") else str(labels[best_index])
    return annotated, label, confidence


def encode_image(image):
    success, encoded = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not success:
        return None
    return base64.b64encode(encoded.tobytes()).decode("ascii")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/labels")
def labels():
    try:
        _, model_labels = load_model()
        return jsonify({"labels": [str(label) for label in model_labels]})
    except (FileNotFoundError, ValueError) as error:
        return jsonify({"error": str(error)}), 503


@app.post("/api/predict")
def predict():
    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Choose an image or capture a camera frame."}), 400
    try:
        image, label, confidence = recognize(uploaded.read())
        return jsonify({
            "label": label,
            "confidence": confidence,
            "image": encode_image(image),
        })
    except (FileNotFoundError, ValueError) as error:
        return jsonify({"error": str(error)}), 503
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed. Try a clearer image."}), 500


@app.post("/api/text-to-sign")
def text_to_sign_api():
    data = request.get_json() or {}
    sentence = data.get("sentence", "").strip()
    if not sentence:
        return jsonify({"error": "Please enter or speak a sentence."}), 400

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
            "spans": spans_list
        })
    except Exception as e:
        app.logger.exception("Text-to-sign generation failed")
@app.post("/api/gloss-to-sentence")
def gloss_to_sentence_api():
    data = request.get_json() or {}
    gloss = data.get("gloss", "")
    try:
        from grammar_engine import gloss_to_sentence, get_predictive_suggestions
        sentence = gloss_to_sentence(gloss)
        suggestions = get_predictive_suggestions(gloss)
        return jsonify({
            "gloss": gloss,
            "sentence": sentence,
            "suggestions": suggestions,
        })
    except Exception as e:
        app.logger.exception("Gloss to sentence conversion failed")
        return jsonify({"error": f"Grammar synthesis failed: {e}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

