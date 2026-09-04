#!/usr/bin/env python
"""
synthetic_data_generator.py

Generates synthetic hand landmark data that simulates realistic hand gestures.
This is useful for testing when no physical camera is available.
"""

import os
import sys
import csv
import numpy as np
from collections import defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def _create_hand_pose(pose_type):
    """
    Creates a base set of 21 (x, y, z) 3D landmark points relative to wrist (0,0,0).
    """
    pts = np.zeros((21, 3), dtype=np.float32)

    # Base palm landmarks
    pts[0] = [0.0, 0.0, 0.0]       # Wrist
    pts[1] = [-0.2, -0.2, 0.0]     # Thumb CMC
    pts[2] = [-0.35, -0.4, 0.0]    # Thumb MCP
    pts[3] = [-0.45, -0.55, 0.0]   # Thumb IP
    pts[4] = [-0.5, -0.7, 0.0]     # Thumb Tip

    pts[5] = [-0.15, -0.6, 0.0]    # Index MCP
    pts[6] = [-0.2, -0.85, 0.0]    # Index PIP
    pts[7] = [-0.22, -1.05, 0.0]   # Index DIP
    pts[8] = [-0.25, -1.25, 0.0]   # Index Tip

    pts[9] = [0.0, -0.65, 0.0]     # Middle MCP
    pts[10] = [0.0, -0.9, 0.0]     # Middle PIP
    pts[11] = [0.0, -1.15, 0.0]    # Middle DIP
    pts[12] = [0.0, -1.35, 0.0]    # Middle Tip

    pts[13] = [0.15, -0.6, 0.0]    # Ring MCP
    pts[14] = [0.2, -0.85, 0.0]    # Ring PIP
    pts[15] = [0.22, -1.05, 0.0]   # Ring DIP
    pts[16] = [0.25, -1.25, 0.0]   # Ring Tip

    pts[17] = [0.3, -0.5, 0.0]     # Pinky MCP
    pts[18] = [0.35, -0.7, 0.0]    # Pinky PIP
    pts[19] = [0.4, -0.85, 0.0]    # Pinky DIP
    pts[20] = [0.45, -1.0, 0.0]    # Pinky Tip

    if pose_type == 'fist':
        # Curl all fingers toward palm
        for base in [5, 9, 13, 17]:
            pts[base + 1][1] = -0.4
            pts[base + 2][1] = -0.2
            pts[base + 3][1] = -0.1
    elif pose_type == 'thumbs_up':
        # Curl index, middle, ring, pinky, extend thumb up
        for base in [5, 9, 13, 17]:
            pts[base + 1][1] = -0.4
            pts[base + 2][1] = -0.2
            pts[base + 3][1] = -0.1
        pts[4] = [-0.3, -1.1, 0.0]
    elif pose_type == 'thumbs_down':
        for base in [5, 9, 13, 17]:
            pts[base + 1][1] = -0.4
            pts[base + 2][1] = -0.2
            pts[base + 3][1] = -0.1
        pts[4] = [-0.3, 0.8, 0.0]
    elif pose_type == 'index_middle':
        # Extend index and middle, curl ring and pinky
        for base in [13, 17]:
            pts[base + 1][1] = -0.4
            pts[base + 2][1] = -0.2
            pts[base + 3][1] = -0.1

    return pts


def generate_hand_landmarks(gesture_type, num_samples=300, seed=None):
    """
    Generate synthetic hand landmarks adhering to physical skeletal structure.
    Strict slot assignment: Slot 0 (0..62) = Left, Slot 1 (63..125) = Right.
    """
    if seed is not None:
        np.random.seed(seed)

    from utils import normalize_landmarks

    samples = []
    description = ""

    for _ in range(num_samples):
        vec = np.zeros(126, dtype=np.float32)

        if gesture_type == 'HELLO':
            pose = _create_hand_pose('open')
            description = 'Open hand wave (Right hand)'
            noise = np.random.normal(0, 0.03, pose.shape)
            norm = normalize_landmarks(pose + noise)
            vec[63:126] = norm  # Right hand in Slot 1

        elif gesture_type == 'YES':
            pose = _create_hand_pose('fist')
            description = 'Fist nod (Right hand)'
            noise = np.random.normal(0, 0.03, pose.shape)
            norm = normalize_landmarks(pose + noise)
            vec[63:126] = norm

        elif gesture_type == 'NO':
            pose = _create_hand_pose('index_middle')
            description = 'Index & middle extended (Right hand)'
            noise = np.random.normal(0, 0.03, pose.shape)
            norm = normalize_landmarks(pose + noise)
            vec[63:126] = norm

        elif gesture_type == 'GOOD':
            pose = _create_hand_pose('thumbs_up')
            description = 'Thumbs up (Right hand)'
            noise = np.random.normal(0, 0.03, pose.shape)
            norm = normalize_landmarks(pose + noise)
            vec[63:126] = norm

        elif gesture_type == 'BAD':
            pose = _create_hand_pose('thumbs_down')
            description = 'Thumbs down (Right hand)'
            noise = np.random.normal(0, 0.03, pose.shape)
            norm = normalize_landmarks(pose + noise)
            vec[63:126] = norm

        elif gesture_type == 'THANKS':
            pose_l = _create_hand_pose('open')
            pose_r = _create_hand_pose('open')
            description = 'Both hands open pressed/moving'
            noise_l = np.random.normal(0, 0.03, pose_l.shape)
            noise_r = np.random.normal(0, 0.03, pose_r.shape)
            vec[0:63] = normalize_landmarks(pose_l + noise_l)   # Left hand
            vec[63:126] = normalize_landmarks(pose_r + noise_r)  # Right hand

        elif gesture_type == 'HELP':
            pose_l = _create_hand_pose('fist')
            pose_r = _create_hand_pose('thumbs_up')
            description = 'Left fist supporting Right thumbs up'
            noise_l = np.random.normal(0, 0.03, pose_l.shape)
            noise_r = np.random.normal(0, 0.03, pose_r.shape)
            vec[0:63] = normalize_landmarks(pose_l + noise_l)
            vec[63:126] = normalize_landmarks(pose_r + noise_r)

        elif gesture_type == 'LOVE':
            pose_l = _create_hand_pose('thumbs_up')
            pose_r = _create_hand_pose('thumbs_up')
            description = 'Both hands forming love symbol'
            noise_l = np.random.normal(0, 0.03, pose_l.shape)
            noise_r = np.random.normal(0, 0.03, pose_r.shape)
            vec[0:63] = normalize_landmarks(pose_l + noise_l)
            vec[63:126] = normalize_landmarks(pose_r + noise_r)

        else:
            raise ValueError(f"Unknown gesture: {gesture_type}")

        samples.append(vec)

    return np.array(samples, dtype=np.float32), description


def create_synthetic_dataset(output_csv, gestures=None, samples_per_gesture=300):
    """Create synthetic hand landmark dataset"""
    
    if gestures is None:
        gestures = ['HELLO', 'THANKS', 'YES', 'NO', 'GOOD', 'BAD', 'LOVE', 'HELP']
    
    print("=" * 70)
    print("GENERATING SYNTHETIC HAND GESTURE DATA")
    print("=" * 70)
    
    os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        header = ['label'] + [f'f{i}' for i in range(126)]
        writer.writerow(header)
        
        # Generate data for each gesture
        total_samples = 0
        for gesture in gestures:
            landmarks, description = generate_hand_landmarks(
                gesture, 
                num_samples=samples_per_gesture,
                seed=hash(gesture) % 10000
            )
            
            # Write samples
            for sample in landmarks:
                row = [gesture] + sample.tolist()
                writer.writerow(row)
                total_samples += 1
            
            print(f"✓ {gesture:10s} - {samples_per_gesture} samples | {description}")
    
    print("\n" + "=" * 70)
    print(f"✓ Dataset created: {output_csv}")
    print(f"✓ Total samples: {total_samples}")
    print(f"✓ Gestures: {', '.join(gestures)}")
    print("=" * 70)
    
    return total_samples

if __name__ == "__main__":
    output_csv = os.path.join(os.path.dirname(__file__), "data", "gestures_synthetic.csv")
    create_synthetic_dataset(output_csv, samples_per_gesture=300)
    
    print("\nNext steps:")
    print("1. Copy this data to data/gestures.csv to use it:")
    print(f"   cp data/gestures_synthetic.csv data/gestures.csv")
    print("2. Re-train the model:")
    print("   python train_model.py")
    print("3. Test with:")
    print("   python quick_test.py")
