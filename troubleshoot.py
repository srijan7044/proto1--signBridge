#!/usr/bin/env python
"""
troubleshoot.py

Comprehensive troubleshooting script to diagnose attribute errors and configuration issues.
"""

import os
import sys

def check_imports():
    """Check if all required packages can be imported"""
    print("=" * 70)
    print("CHECKING IMPORTS")
    print("=" * 70)
    
    packages = {
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'sklearn': 'Scikit-learn',
        'mediapipe': 'MediaPipe',
        'joblib': 'Joblib',
        'pyttsx3': 'pyttsx3',
    }
    
    all_ok = True
    for pkg, name in packages.items():
        try:
            __import__(pkg)
            print(f"✓ {name:20s} - OK")
        except ImportError as e:
            print(f"✗ {name:20s} - FAILED: {e}")
            all_ok = False
    
    print()
    return all_ok

def check_model_files():
    """Check if model files exist and are valid"""
    print("=" * 70)
    print("CHECKING MODEL FILES")
    print("=" * 70)
    
    model_path = "model/sign_classifier.joblib"
    labels_path = "model/labels.joblib"
    data_path = "data/gestures.csv"
    
    checks = {
        'Model': model_path,
        'Labels': labels_path,
        'Training Data': data_path,
    }
    
    all_ok = True
    for name, path in checks.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✓ {name:20s} - Found ({size:,} bytes)")
        else:
            print(f"✗ {name:20s} - NOT FOUND: {path}")
            all_ok = False
    
    print()
    return all_ok

def check_model_attributes():
    """Check if the trained model has required attributes"""
    print("=" * 70)
    print("CHECKING MODEL ATTRIBUTES")
    print("=" * 70)
    
    try:
        import joblib
        
        model_path = "model/sign_classifier.joblib"
        if not os.path.exists(model_path):
            print(f"✗ Model file not found at {model_path}")
            return False
        
        print(f"Loading model from {model_path}...")
        model = joblib.load(model_path)
        print(f"✓ Model loaded: {type(model).__name__}")
        
        # Check critical attributes
        attributes = [
            'predict',
            'predict_proba',
            'classes_',
            'n_estimators',
            'fit',
        ]
        
        all_ok = True
        for attr in attributes:
            if hasattr(model, attr):
                value = getattr(model, attr)
                if attr == 'classes_':
                    print(f"✓ {attr:20s} - {list(value)}")
                elif attr == 'n_estimators':
                    print(f"✓ {attr:20s} - {value}")
                else:
                    print(f"✓ {attr:20s} - Available")
            else:
                print(f"✗ {attr:20s} - MISSING!")
                all_ok = False
        
        print()
        return all_ok
        
    except Exception as e:
        print(f"✗ Error checking model: {e}")
        print()
        return False

def check_mediapipe():
    """Check MediaPipe configuration"""
    print("=" * 70)
    print("CHECKING MEDIAPIPE")
    print("=" * 70)
    
    try:
        import mediapipe as mp
        
        print(f"✓ MediaPipe version: {mp.__version__}")
        
        # Check if we can create a Hands detector
        mp_hands = mp.solutions.hands
        detector = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        print(f"✓ Hands detector created successfully")
        
        # Check drawing utilities
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        print(f"✓ Drawing utilities available")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ MediaPipe error: {e}")
        print()
        return False

def check_camera():
    """Check if camera is available"""
    print("=" * 70)
    print("CHECKING CAMERA")
    print("=" * 70)
    
    try:
        import cv2
        
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                print(f"✓ Camera 0 detected - Resolution: {w}x{h}")
                cap.release()
                print()
                return True
            else:
                print(f"✗ Camera 0 found but cannot read frames")
                cap.release()
        else:
            print(f"✗ Camera 0 not available")
            print("   Try: python camera_diagnostic.py")
        
        print()
        return False
        
    except Exception as e:
        print(f"✗ Camera error: {e}")
        print()
        return False

def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  SIGN LANGUAGE TRANSLATOR - TROUBLESHOOTING".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    checks = [
        ("Imports", check_imports),
        ("Model Files", check_model_files),
        ("Model Attributes", check_model_attributes),
        ("MediaPipe", check_mediapipe),
        ("Camera", check_camera),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ {name} check failed: {e}\n")
            results[name] = False
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} - {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All checks passed! You can run:")
        print("  python realtime_translate.py")
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
    
    print()

if __name__ == "__main__":
    main()
