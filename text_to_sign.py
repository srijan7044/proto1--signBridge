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


def interpolate(frame_a, frame_b, steps):
    """Linearly interpolate `steps` frames between frame_a and frame_b (exclusive of endpoints)."""
    return [
        frame_a + (frame_b - frame_a) * (i / (steps + 1))
        for i in range(1, steps + 1)
    ]


def build_sequence(gloss_words):
    """
    Concatenates each word's clip (with interpolated transitions) into one
    continuous sequence. Returns (all_frames: np.ndarray[N,126], spans: list
    of (word, start_idx, end_idx) marking which frames belong to which word
    -- excluding transition frames -- for captioning and later verification.
    """
    all_frames = []
    spans = []
    missing = []
    prev_last_frame = None

    for word in gloss_words:
        clip = load_clip(word)
        if clip is None:
            missing.append(word)
            continue

        if prev_last_frame is not None:
            all_frames.extend(interpolate(prev_last_frame, clip[0], TRANSITION_FRAMES))

        start_idx = len(all_frames)
        all_frames.extend(list(clip))
        end_idx = len(all_frames)  # exclusive
        spans.append((word, start_idx, end_idx))

        prev_last_frame = clip[-1]

    if missing:
        print(f"WARNING: no recorded clip for: {', '.join(missing)} "
              f"(record with record_sign_clip.py --word {missing[0]}). Skipping these.")

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
