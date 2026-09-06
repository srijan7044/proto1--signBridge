"""
realtime_translate.py

Real-time sign -> text -> speech translator.

Pipeline per frame:
    webcam frame -> MediaPipe hand landmarks -> normalized feature vector
    -> trained classifier -> predicted sign -> stability filter
    -> sentence builder -> (optional) text-to-speech

USAGE:
    python realtime_translate.py

Controls:
    SPACE -> add a space to the sentence
    b     -> backspace (delete last character/word)
    c     -> clear the sentence
    v     -> speak the current sentence out loud
    a     -> toggle auto-speak (speaks each new confirmed word automatically)
    f     -> toggle fullscreen mode
    q     -> quit
"""

import os
import threading
import time
from collections import deque, Counter

import cv2
import joblib
import numpy as np
import pyttsx3

from utils import create_hands_detector, extract_feature_vector, mp_drawing, mp_hands, mp_drawing_styles

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "sign_classifier.joblib")

# --- Model Detection & Stability Parameters ---
# How many recent predictions to look at when deciding a sign is "confirmed"
STABILITY_WINDOW = 8
# Fraction of the window that must agree for a sign to be confirmed
STABILITY_THRESHOLD = 0.70
# Minimum seconds between confirming the SAME sign twice in a row
REPEAT_COOLDOWN = 0.7
# Model confidence required to accept a prediction
MIN_CONFIDENCE = 0.85
# Required gap between the best and second-best class probabilities
MIN_MARGIN = 0.10


class TTSEngine:
    """Runs pyttsx3 in a background thread so speech never blocks the video loop."""

    def __init__(self):
        self._lock = threading.Lock()

    def speak(self, text):
        if not text.strip():
            return
        threading.Thread(target=self._speak_blocking, args=(text,), daemon=True).start()

    def _speak_blocking(self, text):
        with self._lock:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 165)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"TTS Engine warning: {e}")


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}.\n"
            "Run dataset processing, then train_model.py, before running this script."
        )
    # Load model and labels
    model = joblib.load(MODEL_PATH)
    labels_path = os.path.join(os.path.dirname(MODEL_PATH), "labels.joblib")
    
    labels = []
    try:
        if hasattr(model, 'classes_'):
            labels = list(model.classes_)
        elif os.path.exists(labels_path):
            labels = joblib.load(labels_path)
            if isinstance(labels, list):
                labels = sorted(list(set(labels)))
    except Exception as e:
        print(f"Warning: Could not load labels: {e}")
        labels = []
    
    return model, labels


def main():
    model, labels = load_model()
    tts = TTSEngine()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    hands = create_hands_detector(max_num_hands=2)

    recent_predictions = deque(maxlen=STABILITY_WINDOW)
    sentence = ""
    last_confirmed_sign = None
    last_confirmed_time = 0.0
    auto_speak = False
    last_display_prediction = ""
    fullscreen_enabled = True

    print("Real-time sign translator running. Press 'q' in the video window to quit.")

    window_name = "Sign Language Translator"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            predicted_label = None
            confidence = 0.0

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                feats = extract_feature_vector(result.multi_hand_landmarks, result.multi_handedness)
                
                # Never classify a zero-padded/no-hand vector
                if feats.any():
                    probs = model.predict_proba([feats])[0]
                    best_idx = probs.argmax()
                    confidence = probs[best_idx]
                    second_best = np.partition(probs, -2)[-2]
                else:
                    probs = []
                    confidence = 0.0
                    second_best = 1.0

                if confidence > MIN_CONFIDENCE and confidence - second_best >= MIN_MARGIN:
                    if hasattr(model, 'classes_'):
                        predicted_label = model.classes_[best_idx]
                    elif labels and best_idx < len(labels):
                        predicted_label = labels[best_idx]
                    else:
                        predicted_label = str(best_idx)

            recent_predictions.append(predicted_label)

            # Decide whether the recent window agrees strongly enough on one sign
            confirmed_sign = None
            valid = [p for p in recent_predictions if p is not None]
            if len(valid) >= STABILITY_WINDOW * 0.6:
                most_common, count = Counter(valid).most_common(1)[0]
                if count / len(recent_predictions) >= STABILITY_THRESHOLD:
                    confirmed_sign = most_common

            now = time.time()
            if confirmed_sign is not None:
                can_add = (
                    confirmed_sign != last_confirmed_sign
                    or (now - last_confirmed_time) >= REPEAT_COOLDOWN
                )
                if can_add:
                    # Single letters (A-Z) append directly to spell words
                    if len(confirmed_sign) == 1 and confirmed_sign.isalpha():
                        sentence += confirmed_sign
                    # Full word gestures append with a space
                    else:
                        sentence += (" " if sentence and not sentence.endswith(" ") else "") + confirmed_sign
                        
                    last_confirmed_sign = confirmed_sign
                    last_confirmed_time = now
                    
                    if auto_speak:
                        tts.speak(confirmed_sign)

            if predicted_label:
                last_display_prediction = f"{predicted_label} ({confidence:.2f})"
            elif result.multi_hand_landmarks:
                last_display_prediction = "low confidence..."
            else:
                last_display_prediction = "no hand detected"

            # --- HUD Overlay ---
            h, w, _ = frame.shape
            overlay_h = 110
            cv2.rectangle(frame, (0, h - overlay_h), (w, h), (30, 30, 30), -1)
            cv2.putText(frame, f"Sign: {last_display_prediction}", (10, h - overlay_h + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Text: {sentence}", (10, h - overlay_h + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"[SPACE] space  [b] backspace  [c] clear  [v] speak  "
                                f"[a] auto-speak: {'ON' if auto_speak else 'OFF'}  [f] fullscreen  [q] quit",
                        (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                sentence += " "
            elif key == ord('b'):
                # Deletes last character if string ends with letters, or last word if space separated
                sentence = sentence[:-1] if sentence else ""
            elif key == ord('c'):
                sentence = ""
                last_confirmed_sign = None
            elif key == ord('v'):
                tts.speak(sentence)
            elif key == ord('a'):
                auto_speak = not auto_speak
            elif key == ord('f'):
                fullscreen_enabled = not fullscreen_enabled
                prop = cv2.WINDOW_FULLSCREEN if fullscreen_enabled else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, prop)

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()