#!/usr/bin/env python
"""
camera_diagnostic.py

Diagnoses camera availability and helps find the correct camera index.
"""

import cv2
import sys

def find_available_cameras(max_index=10):
    """Try to open cameras with indices 0 to max_index-1"""
    available = []
    
    print("=" * 60)
    print("CAMERA DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"\nScanning for cameras (indices 0-{max_index-1})...\n")
    
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"✓ Camera {i}: AVAILABLE - Resolution: {w}x{h}")
                available.append(i)
            else:
                print(f"✗ Camera {i}: Found but failed to read frame")
            cap.release()
        else:
            print(f"✗ Camera {i}: Not available")
    
    print("\n" + "=" * 60)
    
    if available:
        print(f"\n✓ Found {len(available)} working camera(s): {available}")
        print(f"\nTo use a specific camera, run:")
        for cam_idx in available:
            print(f"  python collect_data.py --label HELLO --samples 300 --camera {cam_idx}")
    else:
        print("\n✗ No cameras found!")
        print("\nPossible causes:")
        print("  1. No camera connected to your system")
        print("  2. Camera driver not installed")
        print("  3. Camera is being used by another application (close it first)")
        print("  4. Camera permissions not granted")
        print("\nSolutions:")
        print("  • Check that your camera is plugged in")
        print("  • Close any other apps using the camera (Zoom, Teams, etc.)")
        print("  • Try restarting your computer")
        print("  • Check Device Manager for camera drivers")
    
    print("=" * 60)
    
    return available

if __name__ == "__main__":
    available_cameras = find_available_cameras(10)
    sys.exit(0 if available_cameras else 1)
