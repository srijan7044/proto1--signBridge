"""
utils.py
Shared helpers for hand-landmark extraction and normalization.

Every script (collect_data.py, train_model.py, realtime_translate.py) uses
the SAME normalization function, which is critical -- if training and
inference normalize landmarks differently, the classifier will perform
poorly no matter how good the model is.
"""

import numpy as np
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Number of (x, y, z) landmarks MediaPipe returns per hand
NUM_LANDMARKS = 21
# Features per hand after normalization (x, y, z -> 63)
FEATURES_PER_HAND = NUM_LANDMARKS * 3
# Support up to 2 hands -> fixed-length feature vector (126)
MAX_HANDS = 2
FEATURE_VECTOR_LENGTH = FEATURES_PER_HAND * MAX_HANDS


def create_hands_detector(static_image_mode=False, max_num_hands=2,
                          min_detection_confidence=0.6, min_tracking_confidence=0.5):
    """Factory so every script configures MediaPipe Hands identically."""
    return mp_hands.Hands(
        static_image_mode=static_image_mode,
        max_num_hands=max_num_hands,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )


def normalize_landmarks(landmark_list):
    """
    Takes a list of 21 (x, y, z) tuples for ONE hand and returns a 
    translation- and scale-invariant flat numpy array of length 63.

    Steps:
      1. Translate so the wrist (landmark 0) is the origin.
      2. Scale by palm length (wrist 0 -> middle finger MCP 9).
    """
    pts = np.array(landmark_list, dtype=np.float32)  # shape (21, 3)
    wrist = pts[0].copy()
    pts -= wrist  # translation invariance

    # Palm size reference: distance from wrist (0) to middle finger base (9)
    palm_size = np.linalg.norm(pts[9])
    if palm_size > 1e-6:
        pts /= palm_size
    else:
        max_dist = np.max(np.linalg.norm(pts, axis=1))
        if max_dist > 1e-6:
            pts /= max_dist

    return pts.flatten()  # length 63


def extract_feature_vector(multi_hand_landmarks, multi_handedness=None):
    """
    Builds a FIXED-LENGTH feature vector (length 126) from MediaPipe's
    detection result for a single frame.

    Strict Hand Slot Assignment:
      - Slot 0 (features 0..62): Left hand
      - Slot 1 (features 63..125): Right hand
    """
    vector = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)

    if not multi_hand_landmarks:
        return vector

    for idx, hand_landmarks in enumerate(multi_hand_landmarks):
        label = None
        if multi_handedness is not None and idx < len(multi_handedness):
            label = multi_handedness[idx].classification[0].label  # "Left" or "Right"

        coords = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
        norm = normalize_landmarks(coords)

        if label == "Left":
            slot = 0
        elif label == "Right":
            slot = 1
        else:
            wrist_x = coords[0][0]
            slot = 0 if wrist_x < 0.5 else 1

        start = slot * FEATURES_PER_HAND
        vector[start:start + FEATURES_PER_HAND] = norm

    return vector


def draw_skeleton(canvas, feature_vector, scale=110, color=(0, 255, 255), thickness=2):
    """
    Draws hand skeleton(s) from a normalized 126-length feature vector onto
    an existing image canvas IN PLACE.
    """
    import cv2

    h, w = canvas.shape[:2]
    wrist_y = int(h * 0.72)

    has_left = np.any(feature_vector[0:63])
    has_right = np.any(feature_vector[63:126])

    offsets = [(-w // 6, 0), (w // 6, 0)]
    if not has_left and has_right:
        offsets[1] = (0, 0)
    elif has_left and not has_right:
        offsets[0] = (0, 0)

    for slot in range(MAX_HANDS):
        start = slot * FEATURES_PER_HAND
        chunk = feature_vector[start:start + FEATURES_PER_HAND]
        if not np.any(chunk):
            continue

        pts = chunk.reshape(NUM_LANDMARKS, 3)
        ox, oy = offsets[slot]
        pixel_pts = [
            (int(w // 2 + ox + x * scale), int(wrist_y + oy + y * scale))
            for x, y, _ in pts
        ]

        for a, b in mp_hands.HAND_CONNECTIONS:
            cv2.line(canvas, pixel_pts[a], pixel_pts[b], color, thickness)
        for x, y in pixel_pts:
            cv2.circle(canvas, (x, y), 3, (255, 255, 255), -1)

    return canvas