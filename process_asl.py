# """
# import os
# import cv2
# import csv
# import mediapipe as mp

# # Point directly to the asl_dataset folder inside your data directory
# DATASET_DIR = os.path.join("data", "Indian Sign Language Alphabet Dataset")
# OUTPUT_CSV = os.path.join("data", "gestures_letters_1.csv")

# # Initialize MediaPipe
# mp_hands = mp.solutions.hands
# hands = mp_hands.Hands(
#     static_image_mode=True,
#     max_num_hands=2,
#     min_detection_confidence=0.5
# )

# headers = ['label'] + [f'f{i}' for i in range(126)]
# os.makedirs("data", exist_ok=True)

# print(f"Extracting images from: {DATASET_DIR}")
# print(f"Saving features to: {OUTPUT_CSV}\n")

# with open(OUTPUT_CSV, mode='w', newline='') as f:
#     writer = csv.writer(f)
#     writer.writerow(headers)
    
#     total_images = 0
    
#     # Process each subfolder (0-9, a-z, etc.)
#     for folder_name in sorted(os.listdir(DATASET_DIR)):
#         folder_path = os.path.join(DATASET_DIR, folder_name)
        
#         if not os.path.isdir(folder_path):
#             continue
            
#         label = folder_name.upper()
#         print(f"Processing class: {label}")
        
#         for img_name in os.listdir(folder_path):
#             img_path = os.path.join(folder_path, img_name)
            
#             img = cv2.imread(img_path)
#             if img is None:
#                 continue
                
#             img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             results = hands.process(img_rgb)
            
#             feature_vector = [0.0] * 126
            
#             if results.multi_hand_landmarks:
#                 for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks[:2]):
#                     start_offset = hand_idx * 63
#                     for lm_idx, landmark in enumerate(hand_landmarks.landmark):
#                         base_idx = start_offset + (lm_idx * 3)
#                         feature_vector[base_idx] = landmark.x
#                         feature_vector[base_idx + 1] = landmark.y
#                         feature_vector[base_idx + 2] = landmark.z
            
#             writer.writerow([label] + feature_vector)
#             total_images += 1

# hands.close()
# print(f"\nDone! Processed {total_images} images into '{OUTPUT_CSV}'.")
# """
# """
# import os
# import cv2
# import csv
# import mediapipe as mp
# from utils import create_hands_detector, extract_feature_vector

# # Handle nested directory structure for Indian Sign Language Alphabet Dataset
# BASE_DIR = os.path.join("data", "SignAlphaSet")
# NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")

# # Point to nested dir if present, otherwise base dir
# DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
# OUTPUT_CSV = os.path.join("data", "gestures_letters_SignAlphaSet.csv")

# # Initialize detector using shared factory config
# hands = create_hands_detector(static_image_mode=True, min_detection_confidence=0.4)

# headers = ['label'] + [f'f{i}' for i in range(126)]
# os.makedirs("data", exist_ok=True)

# print(f"Extracting images from: {DATASET_DIR}")
# print(f"Saving normalized features to: {OUTPUT_CSV}\n")

# with open(OUTPUT_CSV, mode='w', newline='') as f:
#     writer = csv.writer(f)
#     writer.writerow(headers)
    
#     total_images = 0
#     valid_detections = 0
    
#     for folder_name in sorted(os.listdir(DATASET_DIR)):
#         folder_path = os.path.join(DATASET_DIR, folder_name)
        
#         if not os.path.isdir(folder_path):
#             continue
            
#         label = folder_name.upper()
#         print(f"Processing class: {label}")
        
#         for img_name in os.listdir(folder_path):
#             img_path = os.path.join(folder_path, img_name)
            
#             img = cv2.imread(img_path)
#             if img is None:
#                 continue
                
#             img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             results = hands.process(img_rgb)
            
#             # Use normalized feature extraction from utils.py
#             feature_vector = extract_feature_vector(
#                 results.multi_hand_landmarks, 
#                 results.multi_handedness
#             )
            
#             # Only write rows where at least one hand was detected (avoids 0.0 rows)
#             if feature_vector.any():
#                 writer.writerow([label] + feature_vector.tolist())
#                 valid_detections += 1
                
#             total_images += 1

# hands.close()
# print(f"\nDone! Successfully extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")
# """

# # import os
# # import cv2
# # import csv
# # import numpy as np
# # import mediapipe as mp
# # from utils import create_hands_detector, extract_feature_vector

# # BASE_DIR = os.path.join("data", "processed_combine_asl_dataset")
# # NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")
# # DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
# # OUTPUT_CSV = os.path.join("data", "gestures_processed_combine_asl_dataset.csv")

# # # Initialize detectors at progressively lower confidence thresholds to catch hard images
# # hands_primary = create_hands_detector(static_image_mode=True, min_detection_confidence=0.3)
# # hands_fallback = create_hands_detector(static_image_mode=True, min_detection_confidence=0.15)

# # headers = ['label'] + [f'f{i}' for i in range(126)]
# # os.makedirs("data", exist_ok=True)

# # print(f"Extracting images from: {DATASET_DIR}")
# # print(f"Saving normalized features to: {OUTPUT_CSV}\n")

# # def process_image_with_fallback(img):
# #     """Tries primary detection, then applies CLAHE/brightness enhancement if needed."""
# #     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
# #     results = hands_primary.process(img_rgb)
# #     if results.multi_hand_landmarks:
# #         return results

# #     # Fallback 1: CLAHE Contrast Enhancement
# #     lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
# #     l, a, b = cv2.split(lab)
# #     clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
# #     cl = clahe.apply(l)
# #     enhanced = cv2.merge((cl, a, b))
# #     enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    
# #     results = hands_primary.process(enhanced_rgb)
# #     if results.multi_hand_landmarks:
# #         return results

# #     # Fallback 2: Multi-scale resize (helps MediaPipe detect tiny or cropped hands)
# #     h, w = img.shape[:2]
# #     resized = cv2.resize(enhanced_rgb, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
# #     results = hands_fallback.process(resized)
# #     if results.multi_hand_landmarks:
# #         return results

# #     # Fallback 3: Direct fallback detector on raw image
# #     return hands_fallback.process(img_rgb)


# # with open(OUTPUT_CSV, mode='w', newline='') as f:
# #     writer = csv.writer(f)
# #     writer.writerow(headers)
    
# #     total_images = 0
# #     valid_detections = 0
    
# #     for folder_name in sorted(os.listdir(DATASET_DIR)):
# #         folder_path = os.path.join(DATASET_DIR, folder_name)
# #         if not os.path.isdir(folder_path):
# #             continue
            
# #         label = folder_name.upper()
# #         print(f"Processing class: {label}")
        
# #         for img_name in os.listdir(folder_path):
# #             img_path = os.path.join(folder_path, img_name)
# #             img = cv2.imread(img_path)
# #             if img is None:
# #                 continue
                
# #             results = process_image_with_fallback(img)
            
# #             # Extract normalized features via utils.py (ensures Slot 0 primary alignment)
# #             feature_vector = extract_feature_vector(
# #                 results.multi_hand_landmarks if results else None, 
# #                 results.multi_handedness if results else None
# #             )
            
# #             if feature_vector.any():
# #                 writer.writerow([label] + feature_vector.tolist())
# #                 valid_detections += 1
                
# #             total_images += 1

# # hands_primary.close()
# # hands_fallback.close()

# # print(f"\nDone! Successfully extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")

import os
import cv2
import csv
import sys
import numpy as np

# Suppress TensorFlow / MediaPipe C++ log messages before importing mediapipe
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '3'

import mediapipe as mp
from utils import create_hands_detector, extract_feature_vector

BASE_DIR = os.path.join("data", "processed_combine_asl_dataset")
NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")
DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
OUTPUT_CSV = os.path.join("data", "gestures_processed_combine_asl_dataset.csv")

# Initialize shared detectors
hands_primary = create_hands_detector(static_image_mode=True, min_detection_confidence=0.3)
hands_fallback = create_hands_detector(static_image_mode=True, min_detection_confidence=0.15)

headers = ['label'] + [f'f{i}' for i in range(126)]
os.makedirs("data", exist_ok=True)

print(f"Extracting images from: {DATASET_DIR}")
print(f"Saving normalized features to: {OUTPUT_CSV}\n")

def process_image_with_fallback(img):
    """Tries primary detection, then applies CLAHE/brightness enhancement if needed."""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands_primary.process(img_rgb)
    if results and results.multi_hand_landmarks:
        return results

    # Fallback 1: CLAHE Contrast Enhancement
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl, a, b))
    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    
    results = hands_primary.process(enhanced_rgb)
    if results and results.multi_hand_landmarks:
        return results

    # Fallback 2: Multi-scale resize
    h, w = img.shape[:2]
    resized = cv2.resize(enhanced_rgb, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    results = hands_fallback.process(resized)
    if results and results.multi_hand_landmarks:
        return results

    # Fallback 3: Direct fallback detector on raw image
    return hands_fallback.process(img_rgb)


with open(OUTPUT_CSV, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    
    total_images = 0
    valid_detections = 0
    
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
                
            results = process_image_with_fallback(img)
            
            # Extract normalized features via utils.py (ensures Slot 0 primary alignment)
            feature_vector = extract_feature_vector(
                results.multi_hand_landmarks if (results and results.multi_hand_landmarks) else None, 
                results.multi_handedness if (results and results.multi_handedness) else None
            )
            
            if feature_vector.any():
                writer.writerow([label] + feature_vector.tolist())
                valid_detections += 1
                
            total_images += 1

hands_primary.close()
hands_fallback.close()

print(f"\nDone! Successfully extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")

# # import os
# # import cv2
# # import csv
# # import sys
# # from concurrent.futures import ThreadPoolExecutor

# # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# # os.environ['GLOG_minloglevel'] = '3'

# # import mediapipe as mp
# # from utils import create_hands_detector, extract_feature_vector

# # BASE_DIR = os.path.join("data", "processed_combine_asl_dataset")
# # NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")
# # DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
# # OUTPUT_CSV = os.path.join("data", "gestures_processed_combine_asl_dataset.csv")

# # # Single fast detector instance for static images
# # hands_detector = create_hands_detector(
# #     static_image_mode=True, 
# #     max_num_hands=2, 
# #     min_detection_confidence=0.25
# # )

# # headers = ['label'] + [f'f{i}' for i in range(126)]
# # os.makedirs("data", exist_ok=True)

# # print(f"Extracting images from: {DATASET_DIR}")
# # print(f"Saving normalized features to: {OUTPUT_CSV}\n")

# # def process_single_image(args):
# #     img_path, label = args
# #     img = cv2.imread(img_path)
# #     if img is None:
# #         return None

# #     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
# #     results = hands_detector.process(img_rgb)

# #     # Fast single fallback if primary fails: CLAHE contrast boost
# #     if not (results and results.multi_hand_landmarks):
# #         lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
# #         l, a, b = cv2.split(lab)
# #         clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
# #         cl = clahe.apply(l)
# #         enhanced_rgb = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
# #         results = hands_detector.process(enhanced_rgb)

# #     feature_vector = extract_feature_vector(
# #         results.multi_hand_landmarks if (results and results.multi_hand_landmarks) else None,
# #         results.multi_handedness if (results and results.multi_handedness) else None
# #     )

# #     if feature_vector.any():
# #         return [label] + feature_vector.tolist()
# #     return None


# # def main():
# #     total_images = 0
# #     valid_detections = 0

# #     with open(OUTPUT_CSV, mode='w', newline='') as f:
# #         writer = csv.writer(f)
# #         writer.writerow(headers)

# #         for folder_name in sorted(os.listdir(DATASET_DIR)):
# #             folder_path = os.path.join(DATASET_DIR, folder_name)
# #             if not os.path.isdir(folder_path):
# #                 continue

# #             label = folder_name.upper()
# #             image_paths = [
# #                 (os.path.join(folder_path, fname), label) 
# #                 for fname in os.listdir(folder_path)
# #                 if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
# #             ]

# #             print(f"Processing class: {label} ({len(image_paths)} images)...")
            
# #             # Process class batch concurrently
# #             with ThreadPoolExecutor(max_workers=4) as executor:
# #                 results = list(executor.map(process_single_image, image_paths))

# #             for row in results:
# #                 total_images += 1
# #                 if row is not None:
# #                     writer.writerow(row)
# #                     valid_detections += 1

# #     hands_detector.close()
# #     print(f"\nDone! Extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")

# # if __name__ == "__main__":
# #     main()

# import os
# import cv2
# import csv
# import sys
# import threading
# from concurrent.futures import ThreadPoolExecutor

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# os.environ['GLOG_minloglevel'] = '3'

# import mediapipe as mp
# from utils import create_hands_detector, extract_feature_vector

# BASE_DIR = os.path.join("data", "processed_combine_asl_dataset")
# NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")
# DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
# OUTPUT_CSV = os.path.join("data", "gestures_processed_combine_asl_dataset.csv")

# # Thread-local storage so every thread gets its own MediaPipe detector
# thread_local = threading.local()

# def get_thread_detector():
#     if not hasattr(thread_local, "detector"):
#         thread_local.detector = create_hands_detector(
#             static_image_mode=True, 
#             max_num_hands=2, 
#             min_detection_confidence=0.25
#         )
#     return thread_local.detector

# headers = ['label'] + [f'f{i}' for i in range(126)]
# os.makedirs("data", exist_ok=True)

# print(f"Extracting images from: {DATASET_DIR}")
# print(f"Saving normalized features to: {OUTPUT_CSV}\n")

# def process_single_image(args):
#     img_path, label = args
#     img = cv2.imread(img_path)
#     if img is None:
#         return None

#     # Get thread-isolated detector
#     detector = get_thread_detector()

#     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     results = detector.process(img_rgb)

#     # Fast fallback: CLAHE contrast enhancement if initial detection fails
#     if not (results and results.multi_hand_landmarks):
#         lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
#         l, a, b = cv2.split(lab)
#         clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
#         cl = clahe.apply(l)
#         enhanced_rgb = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
#         results = detector.process(enhanced_rgb)

#     feature_vector = extract_feature_vector(
#         results.multi_hand_landmarks if (results and results.multi_hand_landmarks) else None,
#         results.multi_handedness if (results and results.multi_handedness) else None
#     )

#     if feature_vector.any():
#         return [label] + feature_vector.tolist()
#     return None


# def main():
#     total_images = 0
#     valid_detections = 0

#     with open(OUTPUT_CSV, mode='w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(headers)

#         for folder_name in sorted(os.listdir(DATASET_DIR)):
#             folder_path = os.path.join(DATASET_DIR, folder_name)
#             if not os.path.isdir(folder_path):
#                 continue

#             label = folder_name.upper()
#             image_paths = [
#                 (os.path.join(folder_path, fname), label) 
#                 for fname in os.listdir(folder_path)
#                 if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
#             ]

#             print(f"Processing class: {label} ({len(image_paths)} images)...")
            
#             # Concurrently process batch using thread-isolated detectors
#             with ThreadPoolExecutor(max_workers=4) as executor:
#                 results = list(executor.map(process_single_image, image_paths))

#             for row in results:
#                 total_images += 1
#                 if row is not None:
#                     writer.writerow(row)
#                     valid_detections += 1

#     print(f"\nDone! Extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")

# if __name__ == "__main__":
#     main()

# import os
# import cv2
# import csv
# import sys
# import gc

# # Suppress TensorFlow and MediaPipe internal C++ logging
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# os.environ['GLOG_minloglevel'] = '3'

# import mediapipe as mp
# from utils import create_hands_detector, extract_feature_vector

# # Paths configuration
# BASE_DIR = os.path.join("data", "processed_combine_asl_dataset")
# NESTED_DIR = os.path.join(BASE_DIR, "dataset - Gesture Speech")
# DATASET_DIR = NESTED_DIR if os.path.exists(NESTED_DIR) else BASE_DIR
# OUTPUT_CSV = os.path.join("data", "gestures_processed_combine_asl_dataset.csv")

# headers = ['label'] + [f'f{i}' for i in range(126)]
# os.makedirs("data", exist_ok=True)

# print(f"Extracting images from: {DATASET_DIR}")
# print(f"Saving normalized features to: {OUTPUT_CSV}\n")


# def process_asl_dataset():
#     # Single-instance detector running sequentially on main thread
#     detector = create_hands_detector(
#         static_image_mode=True,
#         max_num_hands=2,
#         min_detection_confidence=0.25
#     )

#     total_images = 0
#     valid_detections = 0

#     with open(OUTPUT_CSV, mode='w', newline='') as f:
#         writer = csv.writer(f)
#         writer.writerow(headers)

#         folder_list = sorted([
#             d for d in os.listdir(DATASET_DIR) 
#             if os.path.isdir(os.path.join(DATASET_DIR, d))
#         ])

#         for folder_name in folder_list:
#             folder_path = os.path.join(DATASET_DIR, folder_name)
#             label = folder_name.upper()

#             image_names = [
#                 fname for fname in os.listdir(folder_path)
#                 if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
#             ]

#             print(f"Processing class: {label} ({len(image_names)} images)...", end="", flush=True)
#             class_valid = 0

#             for img_name in image_names:
#                 img_path = os.path.join(folder_path, img_name)
#                 img = cv2.imread(img_path)
#                 if img is None:
#                     continue

#                 total_images += 1

#                 # 1. Primary pass
#                 img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#                 results = detector.process(img_rgb)

#                 # 2. Fast single fallback (CLAHE contrast boost) if primary missed
#                 if not (results and results.multi_hand_landmarks):
#                     lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
#                     l, a, b = cv2.split(lab)
#                     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#                     cl = clahe.apply(l)
#                     enhanced_rgb = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
#                     results = detector.process(enhanced_rgb)

#                 # Extract normalized features via utils.py (ensures Slot 0 alignment)
#                 feature_vector = extract_feature_vector(
#                     results.multi_hand_landmarks if (results and results.multi_hand_landmarks) else None,
#                     results.multi_handedness if (results and results.multi_handedness) else None
#                 )

#                 if feature_vector.any():
#                     writer.writerow([label] + feature_vector.tolist())
#                     valid_detections += 1
#                     class_valid += 1

#             print(f" -> Extracted {class_valid}/{len(image_names)}")
            
#             # Flush output buffer and run garbage collection between classes
#             f.flush()
#             gc.collect()

#     detector.close()
#     print(f"\nDone! Successfully extracted landmarks for {valid_detections}/{total_images} images into '{OUTPUT_CSV}'.")


# if __name__ == "__main__":
#     process_asl_dataset()