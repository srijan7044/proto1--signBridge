"""
record_sign_clip.py

Records a SEQUENCE of hand-landmark frames (a short motion clip) for one
word, and saves it to sign_clips/<word>.npy. This is different from
collect_data.py: that script records many independent static poses for
CLASSIFICATION training; this script records one continuous motion for
GENERATION (playing the sign back later).

USAGE:
    python record_sign_clip.py --word HELLO
    python record_sign_clip.py --word THANKS --seconds 1.5

Controls:
    's' -> start recording (records continuously until it auto-stops
           after --seconds, or you press 's' again to stop early)
    'r' -> discard and re-record
    'q' -> quit without saving (if not yet saved)

The clip is saved as soon as recording stops, as a numpy array of shape
(num_frames, 126) using the same normalized feature format as utils.py.
"""

import argparse
import os
import time

import cv2
import numpy as np

from utils import create_hands_detector, extract_feature_vector, mp_drawing, mp_hands, mp_drawing_styles

CLIPS_DIR = os.path.join(os.path.dirname(__file__), "sign_clips")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True, help="The word this clip represents, e.g. HELLO")
    parser.add_argument("--seconds", type=float, default=1.5, help="Max clip duration in seconds")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    os.makedirs(CLIPS_DIR, exist_ok=True)
    out_path = os.path.join(CLIPS_DIR, f"{args.word.upper()}.npy")

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    hands = create_hands_detector(max_num_hands=2)

    recording = False
    frames = []
    record_start = None

    print(f"Ready to record the sign for '{args.word}'. Press 's' to start, 'q' to quit.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

            if recording:
                feats = extract_feature_vector(result.multi_hand_landmarks, result.multi_handedness)
                frames.append(feats)
                elapsed = time.time() - record_start
                if elapsed >= args.seconds:
                    recording = False
                    print(f"Auto-stopped after {elapsed:.1f}s, {len(frames)} frames captured.")

            status = f"RECORDING ({len(frames)} frames)" if recording else f"READY ({len(frames)} frames captured)"
            color = (0, 0, 255) if recording else (0, 255, 0)
            cv2.putText(frame, f"Word: {args.word}  |  {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, "'s' start/stop  'r' re-record  'q' quit", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            cv2.imshow("Record Sign Clip", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                if not recording:
                    frames = []
                    recording = True
                    record_start = time.time()
                else:
                    recording = False
            elif key == ord('r'):
                frames = []
                recording = False
            elif key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    if frames:
        clip = np.array(frames, dtype=np.float32)
        np.save(out_path, clip)
        print(f"Saved clip for '{args.word}': shape {clip.shape} -> {out_path}")
    else:
        print("No frames recorded, nothing saved.")


if __name__ == "__main__":
    main()
