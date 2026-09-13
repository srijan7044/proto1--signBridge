"""
collect_data1.py

Records rapid, continuous landmark samples for dynamic sign language gestures
(such as 'J' and 'Z') from your webcam and appends them to data/gestures.csv or a custom CSV.

USAGE:
    python collect_data1.py --label J --samples 1300
    python collect_data1.py --label Z --samples 1300 --out data/Z.csv

Controls while running:
    's'  -> toggle continuous recording start / pause
    'q'  -> quit recording early
"""

import argparse
import csv
import os
import time
import cv2
import numpy as np

from utils import create_hands_detector, extract_feature_vector, mp_drawing, mp_hands, mp_drawing_styles


def ensure_csv_header(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["label"] + [f"f{i}" for i in range(126)]
            writer.writerow(header)


def main():
    parser = argparse.ArgumentParser(description="Continuous Dynamic Gesture Data Collector")
    parser.add_argument("--label", required=True, help="Gesture label to record (e.g., J, Z)")
    parser.add_argument("--samples", type=int, default=1300, help="Target number of samples to collect (e.g. 1300)")
    parser.add_argument("--out", type=str, default=os.path.join("data", "gestures.csv"), help="Output CSV path")
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index")
    args = parser.parse_args()

    ensure_csv_header(args.out)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Verify your camera index.")

    # High detection and tracking confidence for smooth motion tracking
    hands = create_hands_detector(
        static_image_mode=False, 
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    recording = False
    collected = 0
    
    csv_file = open(args.out, "a", newline="")
    writer = csv.writer(csv_file)

    print(f"\n=======================================================")
    print(f" Dynamic Data Collector Ready for Label: '{args.label}'")
    print(f" Target Samples: {args.samples}")
    print(f" Output File: {args.out}")
    print(f" Press 's' in video window to START/PAUSE recording")
    print(f" Press 'q' to QUIT early")
    print(f"=======================================================\n")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from webcam.")
                break

            # Mirror view for natural interaction
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            # Draw tracked skeleton landmarks on visual overlay
            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

            # Record features during continuous gesture movement
            if recording and result.multi_hand_landmarks:
                feats = extract_feature_vector(result.multi_hand_landmarks, result.multi_handedness)
                if feats.any():
                    writer.writerow([args.label] + feats.tolist())
                    collected += 1
                    # Minimal delay (10ms) allows capturing fluid movement trajectories (~30 FPS)
                    time.sleep(0.01)

            # Status Overlay HUD
            status = f"RECORDING ({collected}/{args.samples})" if recording else "PAUSED (Press 's')"
            color = (0, 0, 255) if recording else (0, 255, 0)
            
            # Progress bar visualization
            h, w, _ = frame.shape
            progress_w = int((collected / args.samples) * w)
            cv2.rectangle(frame, (0, h - 15), (progress_w, h), (0, 255, 255), -1)

            cv2.putText(frame, f"Label: {args.label} | Status: {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, f"Collected: {collected} / {args.samples}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("Dynamic Gesture Collector ('s' = record, 'q' = quit)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                recording = not recording
            elif key == ord('q') or collected >= args.samples:
                break

    finally:
        csv_file.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nRecording complete! Saved {collected} samples for '{args.label}' to '{args.out}'.")


if __name__ == "__main__":
    main()