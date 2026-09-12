"""
normalization.py

Reusable utility to normalize any CSV hand landmark dataset to match
the coordinate frame and scale used by SignBridge / utils.py.

What it does:
  1. Translates wrist (landmark 0) to origin (0, 0, 0).
  2. Scales landmarks by palm length (wrist 0 -> middle finger MCP 9).
  3. Handles both single-hand (63 features) and two-hand (126 features) datasets.
  4. Automatically backs up the original file if overwriting in-place.

USAGE:
    # Overwrite in-place (creates a .bak backup automatically):
    python normalization.py --input data/gestures_skeleton_converted.csv

    # Save to a new file:
    python normalization.py --input data/raw.csv --output data/normalized.csv
"""

import argparse
import os
import shutil
import sys
import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def normalize_hand_batch(hand_data):
    """
    Normalizes a batch of hand landmarks.
    hand_data: NumPy array of shape (N, 63) representing 21 3D points per sample.
    Returns: NumPy array of shape (N, 63) normalized.
    """
    num_samples = len(hand_data)
    if num_samples == 0:
        return hand_data

    pts = hand_data.reshape(num_samples, 21, 3).copy()

    # Determine which samples have active hand data (not all zeros)
    active_mask = np.any(np.abs(pts) > 1e-5, axis=(1, 2))
    if not np.any(active_mask):
        return hand_data

    # Translate so wrist (index 0) is at (0, 0, 0)
    wrists = pts[:, 0:1, :]  # shape (N, 1, 3)
    pts_centered = pts - wrists

    # Palm size: Euclidean distance from wrist (0) to middle finger base (index 9)
    middle_mcp = pts_centered[:, 9, :]  # shape (N, 3)
    palm_size = np.linalg.norm(middle_mcp, axis=1, keepdims=True)  # shape (N, 1)

    # Fallback to max distance from wrist if palm size is near zero
    max_dist = np.max(np.linalg.norm(pts_centered, axis=2), axis=1, keepdims=True)  # shape (N, 1)
    scale = np.where(palm_size > 1e-6, palm_size, np.where(max_dist > 1e-6, max_dist, 1.0))

    # Apply scaling
    pts_normalized = pts_centered / scale[:, :, np.newaxis]

    # Zero out non-active samples
    pts_normalized[~active_mask] = 0.0

    return pts_normalized.reshape(num_samples, 63)


def normalize_csv(input_path, output_path=None, backup=True):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    target_output = output_path if output_path else input_path
    print(f"Reading: {input_path}")
    df = pd.read_csv(input_path)

    if "label" not in df.columns:
        raise ValueError("CSV must contain a 'label' column.")

    feature_cols = [c for c in df.columns if c != "label"]
    num_features = len(feature_cols)

    if num_features not in (63, 126):
        print(f"Warning: Expected 63 or 126 feature columns, found {num_features}.")

    labels = df["label"].values
    features = df[feature_cols].values.astype(np.float32)

    # Hand 1 features (0..62)
    h1 = features[:, :63]
    h1_normalized = normalize_hand_batch(h1)

    # Hand 2 features (63..125) if present
    if num_features >= 126:
        h2 = features[:, 63:126]
        h2_normalized = normalize_hand_batch(h2)
        final_features = np.hstack([h1_normalized, h2_normalized])
    else:
        final_features = h1_normalized

    # Create backup if overwriting in place
    if backup and os.path.abspath(target_output) == os.path.abspath(input_path):
        bak_path = input_path + ".bak"
        if not os.path.exists(bak_path):
            print(f"Creating backup: {bak_path}")
            shutil.copyfile(input_path, bak_path)

    # Reconstruct dataframe
    norm_df = pd.DataFrame(final_features, columns=feature_cols[: final_features.shape[1]])
    norm_df.insert(0, "label", labels)

    print(f"Saving {len(norm_df)} normalized samples to: {target_output}")
    norm_df.to_csv(target_output, index=False)
    print("Done! Dataset normalized successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize any hand gesture landmark CSV dataset for SignBridge."
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input CSV file")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to output CSV file (default: overwrites input with backup)",
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Do not create a .bak file when overwriting"
    )

    args = parser.parse_args()
    normalize_csv(args.input, args.output, backup=not args.no_backup)


if __name__ == "__main__":
    main()
