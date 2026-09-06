import os
import cv2
import csv
import mediapipe as mp

# Point directly to the asl_dataset folder inside your data directory
DATASET_DIR = os.path.join("data", "asl_dataset")
OUTPUT_CSV = os.path.join("data", "gestures_letters.csv")

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=2,
    min_detection_confidence=0.5
)

headers = ['label'] + [f'f{i}' for i in range(126)]
os.makedirs("data", exist_ok=True)

print(f"Extracting images from: {DATASET_DIR}")
print(f"Saving features to: {OUTPUT_CSV}\n")

with open(OUTPUT_CSV, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    
    total_images = 0
    
    # Process each subfolder (0-9, a-z, etc.)
    for folder_name in sorted(os.listdir(DATASET_DIR)):
        folder_path = os.path.join(DATASET_DIR, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
            
        label = folder_name.upper()
        print(f"Processing class: {label}")
        
        for img_name in os.listdir(folder_path):
            img_path = os.path.join(folder_path, img_name)
            
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            
            feature_vector = [0.0] * 126
            
            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks[:2]):
                    start_offset = hand_idx * 63
                    for lm_idx, landmark in enumerate(hand_landmarks.landmark):
                        base_idx = start_offset + (lm_idx * 3)
                        feature_vector[base_idx] = landmark.x
                        feature_vector[base_idx + 1] = landmark.y
                        feature_vector[base_idx + 2] = landmark.z
            
            writer.writerow([label] + feature_vector)
            total_images += 1

hands.close()
print(f"\nDone! Processed {total_images} images into '{OUTPUT_CSV}'.")