"""
train_model.py

Trains a classifier on the landmark samples in data/gestures.csv and saves
it to model/sign_classifier.joblib along with the label list.

USAGE:
    python train_model.py
"""

import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from sklearn.ensemble import RandomForestClassifier

# Configure Random Forest to balance class weights automatically
clf = RandomForestClassifier(
    n_estimators=300,
    class_weight="balanced",  # Equalizes weights between 60-sample words & 14-sample letters
    max_depth=25,
    random_state=42,
    n_jobs=-1
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "gestures_letters_1.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "sign_classifier.joblib")


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"No data found at {CSV_PATH}. Run collect_data.py first for each sign you want to recognize."
        )

    df = pd.read_csv(CSV_PATH)
    if df["label"].nunique() < 2:
        raise ValueError("You need at least 2 different signs recorded before training. "
                          "Run collect_data.py with different --label values.")

    X = df.drop(columns=["label"]).values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("=== Evaluation on held-out test set ===")
    print(classification_report(y_test, y_pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    labels_path = os.path.join(MODEL_DIR, "labels.joblib")
    joblib.dump(list(clf.classes_), labels_path)
    print(f"Model saved to {MODEL_PATH}")
    print(f"Labels saved to {labels_path}")


if __name__ == "__main__":
    main()
