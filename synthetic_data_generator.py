#!/usr/bin/env python
"""
synthetic_data_generator.py

Generates synthetic hand landmark data that simulates realistic hand gestures.
This is useful for testing when no physical camera is available.
"""

import os
import csv
import numpy as np
from collections import defaultdict

def generate_hand_landmarks(gesture_type, num_samples=300, seed=None):
    """
    Generate synthetic hand landmarks for a specific gesture.
    
    Hand landmarks are 21 points (x, y, z) per hand = 63 features per hand.
    For 2 hands = 126 features total.
    
    Each gesture has a characteristic "fingerprint" pattern.
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Define gesture characteristics (base values for each feature)
    gesture_patterns = {
        'HELLO': {
            'base': np.array([0.1 + np.random.randn(126) * 0.05 for _ in range(num_samples)]),
            'description': 'Hand wave (fingers together, moving back and forth)'
        },
        'THANKS': {
            'base': np.array([0.3 + np.random.randn(126) * 0.06 for _ in range(num_samples)]),
            'description': 'Hands pressed together, moving down'
        },
        'YES': {
            'base': np.array([0.5 + np.random.randn(126) * 0.07 for _ in range(num_samples)]),
            'description': 'Fist moving up and down (nodding)'
        },
        'NO': {
            'base': np.array([0.2 + np.random.randn(126) * 0.05 for _ in range(num_samples)]),
            'description': 'Index and middle finger extended, shaking side to side'
        },
        'GOOD': {
            'base': np.array([0.4 + np.random.randn(126) * 0.06 for _ in range(num_samples)]),
            'description': 'Thumbs up pose'
        },
        'BAD': {
            'base': np.array([0.7 + np.random.randn(126) * 0.07 for _ in range(num_samples)]),
            'description': 'Thumbs down pose'
        },
        'LOVE': {
            'base': np.array([0.6 + np.random.randn(126) * 0.06 for _ in range(num_samples)]),
            'description': 'Cross fingers or heart shape with hands'
        },
        'HELP': {
            'base': np.array([0.35 + np.random.randn(126) * 0.05 for _ in range(num_samples)]),
            'description': 'One hand lifting other hand'
        },
    }
    
    if gesture_type not in gesture_patterns:
        raise ValueError(f"Unknown gesture: {gesture_type}")
    
    return gesture_patterns[gesture_type]['base'], gesture_patterns[gesture_type]['description']

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
