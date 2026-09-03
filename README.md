<<<<<<< HEAD

# Real-Time Sign Language → Text/Speech Translator

A webcam-based system that recognizes hand signs in real time, builds them
into a sentence, and can speak the sentence aloud.

## How it works

There's no single "universal sign language" model you can just download and
trust — ASL/BSL/ISL etc. have huge vocabularies and heavy regional/personal
variation in hand shape. The practical, reliable approach (and what this
project does) is:

1. **You record your own gesture vocabulary** using your webcam (letters,
   words, whatever signs you need — e.g. A–Z, HELLO, THANKS, YES, NO...).
2. **MediaPipe Hands** extracts 21 3D landmarks per hand from each frame.
3. Landmarks are **normalized** (translated to the wrist, scaled by hand
   size) so the same sign looks the same in the data regardless of where
   your hand is in the frame or how close it is to the camera.
4. A **RandomForest classifier** learns to map normalized landmarks →
   sign label. This trains in seconds and runs fast enough for real-time
   use on a CPU (no GPU needed).
5. At inference time, predictions are **stability-filtered** (a sign must
   be the majority vote across recent frames before it's accepted) so
   flickery, noisy per-frame predictions don't spam the sentence.
6. Confirmed signs are appended to a running sentence, which you can speak
   aloud with `pyttsx3` (offline text-to-speech).

This same landmark→classifier pipeline is exactly what most real-time
"gesture recognition" production systems use — it's just a matter of how
much vocabulary you train it on.

## Project structure

```
sign_translator/
├── requirements.txt
├── utils.py                  # shared landmark extraction/normalization
├── collect_data.py           # record training samples from webcam
├── train_model.py            # train the classifier
├── realtime_translate.py     # the main app
├── data/gestures.csv         # your recorded samples (created by you)
└── model/sign_classifier.joblib  # trained model (created by you)
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **Important:** stick to `mediapipe==0.10.14` as pinned in
> requirements.txt. Newer mediapipe releases (0.10.2x+) removed the
> legacy `mp.solutions` API this project uses, and you'll get
> `AttributeError: module 'mediapipe' has no attribute 'solutions'`
> if you install an unpinned/newer version.

## Step 1 — Collect training data

Record samples for every sign you want the system to recognize. Vary hand
angle/distance/position slightly between samples so the model generalizes.

```bash
python collect_data.py --label HELLO --samples 300
python collect_data.py --label THANKS --samples 300
python collect_data.py --label YES --samples 300
python collect_data.py --label NO --samples 300
# ...repeat for every sign in your vocabulary
```

Controls: press `s` to start/stop recording, `q` to quit. All samples
append into `data/gestures.csv`.

**Tips for good accuracy:**

shapes will confuse a RandomForest more than they'd confuse a human.
data (it appends, doesn't overwrite).

## Step 2 — Train the model

```bash
python train_model.py
```

This prints a precision/recall report so you can see which signs the
model confuses, and saves `model/sign_classifier.joblib`. If accuracy is
poor for a specific sign, record more/cleaner samples for it and re-train.

## Step 3 — Run the real-time translator

```bash
python realtime_translate.py
```

Controls:
| Key | Action |
|---|---|
| `SPACE` | insert a space |
| `b` | backspace (delete last word) |
| `c` | clear the whole sentence |
| `v` | speak the current sentence out loud |
| `a` | toggle auto-speak (speaks each confirmed sign immediately) |
| `q` | quit |

The HUD at the bottom of the window shows the live predicted sign (with
confidence), the sentence built so far, and the key controls.

## Tuning

All the real-time behavior knobs are constants at the top of
`realtime_translate.py`:

agreement are needed before a sign counts as "confirmed". Raise these
for fewer false positives (but slower response); lower them for a
snappier but twitchier system.
added to the sentence twice in a row (stops "HELLO" from repeating
10 times while you hold the pose).
prediction.

## Extending this

already supports two hands (`utils.py` zero-pads a missing hand). For
signs that involve _movement_ (not just a static pose), you'd extend
`extract_feature_vector` to include a short temporal window of
landmarks (e.g. last 10–15 frames) and swap the classifier for an
LSTM/1D-CNN — happy to help build that next if you need it.
that, consider a small neural network on the same normalized landmarks.
pipeline — record A–Z once each with ~300 samples per letter.

# Part 2: Text → Sign Language Generation

The reverse direction: type/speak a sentence, and the system generates a
sign-language animation for it.

## How it works

1. **Gloss simplification** — the sentence is reduced to its key content
   words (stopwords like "a", "the", "is" dropped), since sign language
   grammar doesn't map 1:1 onto spoken/written grammar.
2. **Clip lookup** — each gloss word is looked up in `sign_clips/`, a
   library of pre-recorded _motion_ sequences (not static poses — a sign
   is a short movement, so each clip is ~20-40 frames).
3. **Concatenation with smoothing** — clips are joined in gloss order,
   with a handful of linearly-interpolated frames inserted between them
   so the transition from one sign's ending pose to the next sign's
   starting pose doesn't jump/snap.
4. **Rendering** — the full landmark sequence is drawn as a stick-figure
   skeleton video (`cv2.VideoWriter`), with the current word captioned
   on-screen.
5. **Round-trip verification** — the generated frames are fed back
   through the Part 1 recognition model, segment by segment, and each
   segment's predicted word is compared against the word it was meant to
   represent. This is an automated, repeatable way to sanity-check that
   a generated sign is recognizable/self-consistent — not a linguistic
   correctness guarantee, but a solid practical check that reuses infra
   you already built.

## New files

```
sign_translator/
├── record_sign_clip.py       # record a motion clip for one word
├── text_to_sign.py           # sentence -> gloss -> rendered video
├── verify_generation.py      # round-trip check via the recognition model
└── sign_clips/<WORD>.npy     # your recorded clips (created by you)
```

## Step 1 — Record word clips

For every word you want to be able to _generate_, record a short motion
clip (this is separate from the static-pose data used for recognition):

```bash
python record_sign_clip.py --word HELLO
python record_sign_clip.py --word THANKS --seconds 1.5
```

Controls: `s` start/stop recording, `r` discard & re-record, `q` quit.
The clip auto-stops after `--seconds` and saves to
`sign_clips/<WORD>.npy`.

## Step 2 — Generate a sign video from text

```bash
python text_to_sign.py --sentence "Hello, thanks" --output out.mp4
```

This prints the simplified gloss, warns about any words with no recorded
clip (they're skipped, not guessed), and renders `out.mp4`. It also saves
`out.mp4.frames.npy` and `out.mp4.spans.npy` alongside the video — these
are needed by the verification step.

## Step 3 — Verify the generated signs

Requires a trained recognition model from Part 1 (`model/sign_classifier.joblib`):

```bash
python verify_generation.py --output out.mp4
```

This prints a table of intended vs. recognized word per segment, an
agreement percentage, and an overall round-trip accuracy score. Words
that don't round-trip cleanly are candidates for re-recording.

## Notes & limitations

friend" but never recorded a FRIEND clip, it's dropped with a warning
rather than silently producing something wrong. A natural fallback
(not yet implemented) is spelling out missing words letter-by-letter
using single-letter clips, if you've recorded a fingerspelling
alphabet.
tune it for your use case (e.g. keep "not" since it changes meaning).
static poses (Part 1's model). This works well as a sanity check but
is an approximation for true motion-based signs — for higher-fidelity
verification, train a sequence-based recognition model (see the LSTM
suggestion above) and adapt `verify_generation.py` to use it.
