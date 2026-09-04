"""
text_to_sign.py

Converts a text sentence into a rendered sign-language animation by:
  1. Reducing the sentence to a simplified "gloss" (key content words,
     stopwords removed).
  2. Looking up each gloss word's recorded motion clip in sign_clips/.
  3. Concatenating clips with smooth interpolated transitions.
  4. Rendering the full landmark sequence as a stick-figure video.

USAGE:
    python text_to_sign.py --sentence "Hello, thank you" --output out.mp4

Requires clips recorded with record_sign_clip.py for every word you want
to sign (missing words are skipped with a warning -- see README for how
to handle that, e.g. fingerspelling fallback).
"""

import argparse
import os
import re

import cv2
import numpy as np

from utils import draw_skeleton, FEATURE_VECTOR_LENGTH

CLIPS_DIR = os.path.join(os.path.dirname(__file__), "sign_clips")

# Small hardcoded stopword list -- words typically dropped when converting
# spoken/written grammar into sign gloss order. Not exhaustive; edit freely.
STOPWORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been", "being",
    "to", "of", "do", "does", "did", "will", "would", "shall", "should",
    "can", "could", "may", "might", "must", "and", "but", "or", "so",
}

TRANSITION_FRAMES = 6  # interpolated frames inserted between consecutive signs


def sentence_to_gloss(sentence):
    """Lowercase, tokenize, and drop stopwords -> list of gloss words in order."""
    words = re.findall(r"[a-zA-Z']+", sentence.lower())
    return [w.upper() for w in words if w not in STOPWORDS]


def load_clip(word):
    path = os.path.join(CLIPS_DIR, f"{word}.npy")
    if not os.path.exists(path):
        return None
    return np.load(path)


def generate_synthetic_letter_clip(letter, num_frames=10):
    """Generates a 10-frame static landmark clip for fingerspelling a single letter."""
    try:
        from synthetic_data_generator import _create_hand_pose
        from utils import normalize_landmarks
        char_code = ord(letter.upper()) % 4
        pose_types = ['open', 'fist', 'index_middle', 'thumbs_up']
        base_pose = _create_hand_pose(pose_types[char_code])
        vec = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
        vec[63:126] = normalize_landmarks(base_pose)  # Right hand slot
        return np.tile(vec, (num_frames, 1))
    except Exception:
        vec = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
        return np.tile(vec, (num_frames, 1))


def interpolate(frame_a, frame_b, steps):
    """Interpolates `steps` frames between frame_a and frame_b with hand awareness."""
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
    Concatenates each word's clip (with interpolated transitions) into one
    continuous sequence. Performs fingerspelling fallback for words missing recorded clips.
    """
    all_frames = []
    spans = []
    prev_last_frame = None

    for word in gloss_words:
        clip = load_clip(word)
        if clip is None:
            # Fingerspelling fallback
            print(f"Notice: No pre-recorded clip for '{word}'. Using fingerspelling fallback...")
            letter_frames = []
            for char in word:
                c_clip = load_clip(char)
                if c_clip is None:
                    c_clip = generate_synthetic_letter_clip(char)
                letter_frames.extend(list(c_clip))
            clip = np.array(letter_frames, dtype=np.float32)

        if prev_last_frame is not None and len(clip) > 0:
            all_frames.extend(interpolate(prev_last_frame, clip[0], TRANSITION_FRAMES))

        start_idx = len(all_frames)
        all_frames.extend(list(clip))
        end_idx = len(all_frames)  # exclusive
        spans.append((word, start_idx, end_idx))

        if len(clip) > 0:
            prev_last_frame = clip[-1]

    if not all_frames:
        return np.zeros((0, FEATURE_VECTOR_LENGTH), dtype=np.float32), []

    return np.array(all_frames, dtype=np.float32), spans



def render_video(frames, spans, output_path, fps=20, size=(640, 480)):
    """Renders the landmark sequence as a stick-figure video with word captions."""
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)

    # Build a quick frame_idx -> current word lookup for captioning
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
    parser.add_argument("--sentence", required=True, help="Sentence to translate into sign language")
    parser.add_argument("--output", default="output_sign.mp4", help="Output video path")
    parser.add_argument("--fps", type=int, default=20)
    args = parser.parse_args()

    gloss = sentence_to_gloss(args.sentence)
    print(f"Gloss: {gloss}")

    frames, spans = build_sequence(gloss)
    if len(frames) == 0:
        print("No clips available for any word in this sentence -- nothing to render.")
        return

    render_video(frames, spans, args.output, fps=args.fps)
    print(f"Rendered {len(frames)} frames -> {args.output}")

    # Save spans alongside the video so verify_generation.py can reuse them
    # without re-running gloss/clip lookup.
    np.save(args.output + ".spans.npy", np.array(spans, dtype=object))
    np.save(args.output + ".frames.npy", frames)


if __name__ == "__main__":
    main()
