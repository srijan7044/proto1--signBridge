"""
verify_generation.py

Round-trip verification for generated sign sequences: feeds the frames
produced by text_to_sign.py back through the TRAINED RECOGNITION MODEL
(from train_model.py) and checks whether the model recognizes each
segment as the word it was supposed to represent.

This is an automated sanity check, not a linguistic-correctness
guarantee -- it tells you whether the generated motion is
self-consistent with your own recognizer, which is exactly the model
that will eventually be used to read signs back.

USAGE:
    python text_to_sign.py --sentence "Hello, thank you" --output out.mp4
    python verify_generation.py --output out.mp4
"""

import argparse
import os
from collections import Counter

import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "sign_classifier.joblib")


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No trained recognition model at {MODEL_PATH}. "
            "Run collect_data.py + train_model.py first (Part 1 of the project)."
        )
    loaded = joblib.load(MODEL_PATH)
    if isinstance(loaded, dict):
        return loaded["model"]
    return loaded



def verify(output_path):
    frames_path = output_path + ".frames.npy"
    spans_path = output_path + ".spans.npy"

    if not (os.path.exists(frames_path) and os.path.exists(spans_path)):
        raise FileNotFoundError(
            f"Missing {frames_path} or {spans_path}. Run text_to_sign.py first -- "
            "it saves these alongside the video for verification."
        )

    frames = np.load(frames_path)
    spans = np.load(spans_path, allow_pickle=True)

    model = load_model()

    results = []
    for word, start, end in spans:
        segment = frames[start:end]
        if len(segment) == 0:
            continue
        preds = model.predict(segment)
        winner, count = Counter(preds).most_common(1)[0]
        confidence = count / len(preds)
        match = winner.upper() == word.upper()
        results.append((word, winner, confidence, match))

    print(f"\n{'Intended':<12}{'Recognized':<12}{'Agreement':<12}{'Match'}")
    print("-" * 48)
    matches = 0
    for word, winner, confidence, match in results:
        print(f"{word:<12}{winner:<12}{confidence:<12.0%}{'YES' if match else 'NO'}")
        matches += match

    total = len(results)
    accuracy = matches / total if total else 0.0
    print("-" * 48)
    print(f"Round-trip accuracy: {matches}/{total} ({accuracy:.0%})")

    if accuracy < 1.0:
        print("\nWords that didn't round-trip cleanly may need to be re-recorded "
              "with record_sign_clip.py, or your recognition model may need more "
              "training samples for that sign (see README).")

    return accuracy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output_sign.mp4",
                         help="Path passed to text_to_sign.py's --output (used to find the .frames.npy/.spans.npy)")
    args = parser.parse_args()
    verify(args.output)


if __name__ == "__main__":
    main()
