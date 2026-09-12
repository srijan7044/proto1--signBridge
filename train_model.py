"""
train_model.py

Trains a classifier on merged landmark samples (words + letters) and saves
it to model/sign_classifier.joblib along with the label list.

USAGE:
    python train_model.py
"""

import os
import sys
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "sign_classifier.joblib")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.joblib")

#WORDS_CSV = os.path.join(DATA_DIR, "gestures.csv")
LETTERS_CSV = os.path.join(DATA_DIR, "gestures_letters_SignAlphaSet_O.csv")


def load_combined_dataset():
    dataframes = []

    # if os.path.exists(WORDS_CSV):
    #     print(f"Loading word dataset: {WORDS_CSV}")
    #     dataframes.append(pd.read_csv(WORDS_CSV))
    # else:
    #     print(f"Word dataset not found at {WORDS_CSV}")

    if os.path.exists(LETTERS_CSV):
        print(f"Loading letter dataset: {LETTERS_CSV}")
        dataframes.append(pd.read_csv(LETTERS_CSV))
    else:
        print(f"Letter dataset not found at {LETTERS_CSV}")

    if not dataframes:
        raise FileNotFoundError(f"No CSV datasets found in {DATA_DIR}.")

    combined_df = pd.concat(dataframes, ignore_index=True)
    print(f"Total samples loaded: {len(combined_df)} across {combined_df['label'].nunique()} classes.")
    return combined_df


def main():
    df = load_combined_dataset()

    if df["label"].nunique() < 2:
        raise ValueError("You need at least 2 different classes before training.")

    X = df.drop(columns=["label"]).values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=25,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print("Training Random Forest Classifier...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("\n=== Evaluation on held-out test set ===")
    print(classification_report(y_test, y_pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(list(clf.classes_), LABELS_PATH)

    print(f"\nModel saved to {MODEL_PATH}")
    print(f"Labels saved to {LABELS_PATH}")


if __name__ == "__main__":
    main()