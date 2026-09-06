"""
text_to_sign.py

Converts a text sentence into a rendered sign-language animation.
Falls back to gestures_letters_1.csv landmark data for fingerspelling letters.
"""

import argparse
import os
import re

import cv2
import numpy as np
import pandas as pd

from utils import draw_skeleton, FEATURE_VECTOR_LENGTH

BASE_DIR = os.path.dirname(__file__)
CLIPS_DIR = os.path.join(BASE_DIR, "sign_clips")
CSV_LETTERS_PATH = os.path.join(BASE_DIR, "data", "gestures_letters_1.csv")

TRANSITION_FRAMES = 6  # Interpolated frames between consecutive letters
_letter_data_cache = None


def get_letter_landmarks_from_csv(letter):
    """Retrieves real MediaPipe landmark frames for a letter from gestures_letters_1.csv."""
    global _letter_data_cache
    if not os.path.exists(CSV_LETTERS_PATH):
        return None
        
    if _letter_data_cache is None:
        try:
            _letter_data_cache = pd.read_csv(CSV_LETTERS_PATH)
        except Exception:
            return None

    # Filter rows matching the target letter
    df_char = _letter_data_cache[_letter_data_cache['label'] == letter.upper()]
    if df_char.empty:
        return None

    # Pull sample landmark vector (126 features) and repeat for 10 frames
    sample_vector = df_char.iloc[0].drop('label').values.astype(np.float32)
    return np.tile(sample_vector, (10, 1))


def load_clip(word_or_char):
    """Attempts to load a .npy motion clip first; falls back to CSV landmarks for letters."""
    # 1. Try loading pre-recorded motion clip from sign_clips/
    path = os.path.join(CLIPS_DIR, f"{word_or_char}.npy")
    if os.path.exists(path):
        return np.load(path)

    # 2. If it's a single letter, attempt retrieval from the letter CSV dataset
    if len(word_or_char) == 1 and word_or_char.isalpha():
        csv_clip = get_letter_landmarks_from_csv(word_or_char)
        if csv_clip is not None:
            return csv_clip

    return None


def sentence_to_gloss(sentence):
    """Tokenize words and preserve the entire sentence for fingerspelling/rendering."""
    words = re.findall(r"[a-zA-Z']+", sentence.lower())
    return [w.upper() for w in words]


def generate_synthetic_letter_clip(letter, num_frames=10):
    """Generates a static landmark clip fallback."""
    try:
        from synthetic_data_generator import _create_hand_pose
        from utils import normalize_landmarks
        char_code = ord(letter.upper()) % 4
        pose_types = ['open', 'fist', 'index_middle', 'thumbs_up']
        base_pose = _create_hand_pose(pose_types[char_code])
        vec = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
        vec[63:126] = normalize_landmarks(base_pose)
        return np.tile(vec, (num_frames, 1))
    except Exception:
        vec = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
        return np.tile(vec, (num_frames, 1))


def interpolate(frame_a, frame_b, steps):
    """Interpolates `steps` frames between frame_a and frame_b."""
    interpolated = []
    for i in range(1, steps + 1):
        alpha = i / (steps + 1)
        f = np.zeros_like(frame_a)
        for slot in range(2):
            start = slot * 63
            end = start + 63
            chunk_a = frame_a[start:end]
            chunk_b = frame_b[start:end]
            has_a = np.any(chunk_a)
            has_b = np.any(chunk_b)
            if has_a and has_b:
                f[start:end] = chunk_a + (chunk_b - chunk_a) * alpha
            elif has_a:
                f[start:end] = chunk_a
            elif has_b:
                f[start:end] = chunk_b
        interpolated.append(f)
    return interpolated


def build_sequence(gloss_words):
    """
    Renders every word strictly LETTER-BY-LETTER (fingerspelling)
    with smooth interpolated transitions.
    """
    all_frames = []
    spans = []
    prev_last_frame = None

    for word in gloss_words:
        word_start_idx = len(all_frames)
        
        for char in word:
            if not char.isalpha():
                continue
                
            c_clip = load_clip(char)
            if c_clip is None:
                c_clip = generate_synthetic_letter_clip(char)

            if prev_last_frame is not None and len(c_clip) > 0:
                all_frames.extend(interpolate(prev_last_frame, c_clip[0], TRANSITION_FRAMES))

            all_frames.extend(list(c_clip))

            if len(c_clip) > 0:
                prev_last_frame = c_clip[-1]

        word_end_idx = len(all_frames)
        
        if word_end_idx > word_start_idx:
            spans.append((word, word_start_idx, word_end_idx))

    if not all_frames:
        return np.zeros((0, FEATURE_VECTOR_LENGTH), dtype=np.float32), []

    return np.array(all_frames, dtype=np.float32), spans


def render_video(frames, spans, output_path, fps=20, size=(640, 480)):
    """Renders the landmark sequence as a video."""
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)

    caption_for_frame = {}
    for word, start, end in spans:
        for i in range(start, end):
            caption_for_frame[i] = word

    for i, feats in enumerate(frames):
        canvas = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        draw_skeleton(canvas, feats)
        caption = caption_for_frame.get(i, "")
        cv2.putText(canvas, caption, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        writer.write(canvas)

    writer.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentence", required=True)
    parser.add_argument("--output", default="output_sign.mp4")
    parser.add_argument("--fps", type=int, default=20)
    args = parser.parse_args()

    gloss = sentence_to_gloss(args.sentence)
    print(f"Gloss: {gloss}")

    frames, spans = build_sequence(gloss)
    if len(frames) == 0:
        print("No clips available.")
        return

    render_video(frames, spans, args.output, fps=args.fps)
    print(f"Rendered {len(frames)} frames -> {args.output}")


if __name__ == "__main__":
    main()