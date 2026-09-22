"""
extract_skeleton_image.py

Extracts landmark coordinates directly from pre-rendered skeleton images
using color-based segmentation (HSV thresholding) instead of MediaPipe.
"""

import os
import cv2
import csv
import numpy as np

# Define color ranges in HSV space for skeleton markers
COLOR_RANGES = {
    "wrist_red":    ((0, 100, 100), (10, 255, 255)),     # Red wrist / joint nodes
    "thumb_cream":  ((10, 30, 180), (30, 100, 255)),    # Cream/beige thumb
    "index_purple": ((130, 80, 80), (160, 255, 255)),   # Purple index finger
    "middle_yellow":((20, 150, 150), (35, 255, 255)),   # Yellow middle finger
    "ring_green":   ((35, 100, 100), (85, 255, 255)),    # Green ring finger
    "pinky_blue":   ((100, 150, 150), (130, 255, 255))  # Blue pinky finger
}

def extract_landmarks_from_skeleton_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w, _ = img.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    detected_points = []

    # Find color centroids for key joint groups
    for name, (lower, upper) in COLOR_RANGES.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort contours from bottom to top (y-axis) to preserve joint order
        sorted_contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1], reverse=True)
        
        for cnt in sorted_contours:
            if cv2.contourArea(cnt) > 5: # Ignore noise
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = (M["m10"] / M["m00"]) / w  # Normalize x to [0, 1]
                    cy = (M["m01"] / M["m00"]) / h  # Normalize y to [0, 1]
                    detected_points.append((cx, cy, 0.0)) # z = 0.0 for 2D images

    # Ensure vector matches MediaPipe's 126-feature format (63 per hand)
    feature_vector = np.zeros(126, dtype=np.float32)
    
    # Fill Slot 0 primary hand with extracted coordinate points
    flat_pts = np.array(detected_points, dtype=np.float32).flatten()
    n_copy = min(len(flat_pts), 63)
    feature_vector[:n_copy] = flat_pts[:n_copy]

    return feature_vector


def process_skeleton_folder(input_dir, output_csv):
    headers = ['label'] + [f'f{i}' for i in range(126)]
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    with open(output_csv, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        total = 0
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(root, file)
                    label = os.path.basename(os.path.dirname(img_path)).upper()
                    
                    feats = extract_landmarks_from_skeleton_image(img_path)
                    if feats is not None and feats.any():
                        writer.writerow([label] + feats.tolist())
                        total += 1

    print(f"Done! Saved {total} skeleton image features to '{output_csv}'.")

# Example Usage:
# process_skeleton_folder("data/skeleton_images", "data/gestures_from_skeletons.csv")

if __name__ == "__main__":
    process_skeleton_folder(
        input_dir=os.path.join("data", "processed_combine_asl_dataset"), 
        output_csv=os.path.join("data", "gestures_skeleton_converted.csv")
    )