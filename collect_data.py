"""
collect_data.py

Records hand-landmark samples from your webcam for the signs you want to
recognize, and appends them to data/gestures.csv.

USAGE:
    python collect_data.py --label HELLO
    python collect_data.py --label THANKS --samples 300

Controls while running:
    's'  -> start/stop recording samples for the current label
    'q'  -> quit

Tip: record 200-400 samples per sign, moving your hand slightly (angle,
distance, position) each time so the classifier generalizes instead of
memorizing one exact pose.
"""

import argparse
import csv
import os
import time

import cv2

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from utils import create_hands_detector, extract_feature_vector, mp_drawing, mp_hands, mp_drawing_styles

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def ensure_csv_header(csv_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["label"] + [f"f{i}" for i in range(126)]
            writer.writerow(header)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Name of the sign, e.g. A or HELLO")
    parser.add_argument("--samples", type=int, default=250, help="Target number of samples to record")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index")
    parser.add_argument(
        "--output",
        default=None,
        help="Target CSV file name (e.g., gestures.csv or Y.csv). Defaults to gestures.csv",
    )
    parser.add_argument(
        "--hands",
        type=int,
        default=1,
        choices=[1, 2],
        help="Number of hands to detect (default: 1 for ASL alphabet, 2 for 2-handed signs)",
    )
    args = parser.parse_args()

    target_filename = args.output if args.output else "gestures.csv"
    csv_path = target_filename if os.path.isabs(target_filename) else os.path.join(DATA_DIR, target_filename)

    ensure_csv_header(csv_path)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam at index {args.camera}. Try a different --camera index.")

    hands = create_hands_detector(max_num_hands=args.hands)

    recording = False
    collected = 0
    csv_file = open(csv_path, "a", newline="")
    writer = csv.writer(csv_file)

    print(f"Ready to record for label '{args.label}'. Press 's' to start/stop, 'q' to quit.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from webcam.")
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

            if recording and result.multi_hand_landmarks:
                feats = extract_feature_vector(result.multi_hand_landmarks, result.multi_handedness)
                writer.writerow([args.label] + feats.tolist())
                collected += 1
                time.sleep(0.03)  # slight delay so samples aren't near-duplicates every frame

            status = f"REC ({collected}/{args.samples})" if recording else "PAUSED"
            color = (0, 0, 255) if recording else (0, 255, 0)
            cv2.putText(frame, f"Label: {args.label}  |  {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, "Press 's' to start/stop, 'q' to quit", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            cv2.imshow("Collect Sign Data", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                recording = not recording
            elif key == ord('q') or collected >= args.samples:
                break

    finally:
        csv_file.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"Done. Collected {collected} samples for '{args.label}'. Saved to {csv_path}")


if __name__ == "__main__":
    main()
