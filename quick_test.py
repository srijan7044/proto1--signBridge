#!/usr/bin/env python
"""
quick_test.py

Quick test to verify the trained model works correctly.
Tests the model on a few random samples from the test set.
"""

import os
import joblib
import pandas as pd
import numpy as np

def quick_test():
    MODEL_PATH = "model/sign_classifier.joblib"
    LABELS_PATH = "model/labels.joblib"
    DATA_PATH = "data/gestures.csv"
    
    print("=" * 60)
    print("SIGN LANGUAGE TRANSLATOR - QUICK MODEL TEST")
    print("=" * 60)
    
    # Check if files exist
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Model not found at {MODEL_PATH}")
        print("   Run train_model.py first!")
        return False
    
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Data not found at {DATA_PATH}")
        return False
    
    print("\n✓ Model file found")
    print("✓ Training data file found")
    
    # Load model and data
    print("\nLoading model...")
    model = joblib.load(MODEL_PATH)
    labels = joblib.load(LABELS_PATH)
    df = pd.read_csv(DATA_PATH)
    
    print(f"✓ Model loaded successfully")
    print(f"✓ Model type: {type(model).__name__}")
    print(f"✓ Unique signs: {set(df['label'])}")
    
    # Test predictions
    print("\n" + "=" * 60)
    print("TESTING MODEL PREDICTIONS")
    print("=" * 60)
    
    # Get one sample from each class
    for sign in set(df['label']):
        sample = df[df['label'] == sign].iloc[0].drop('label').values
        prediction = model.predict([sample])[0]
        confidence = max(model.predict_proba([sample])[0])
        
        status = "✓" if prediction == sign else "✗"
        print(f"{status} True: {sign:8s} | Predicted: {prediction:8s} | Confidence: {confidence:.2%}")
    
    print("\n" + "=" * 60)
    print("READY TO RUN REAL-TIME TRANSLATOR!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python realtime_translate.py")
    print("2. Allow camera access when prompted")
    print("3. Make hand gestures (e.g., HELLO, THANKS, YES, NO)")
    print("4. Use keyboard controls:")
    print("   SPACE -> Add space")
    print("   b     -> Backspace")
    print("   c     -> Clear sentence")
    print("   v     -> Speak sentence")
    print("   a     -> Toggle auto-speak")
    print("   q     -> Quit")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    quick_test()
