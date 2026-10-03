"""
backend/models/gesture_model.py

Gesture dataset model for MongoDB.
Stores 126-D landmark vectors and handles high-performance CSV bulk import and export.
"""

import os
import csv
from datetime import datetime
import pandas as pd
from backend.db import db_manager

class GestureModel:
    @staticmethod
    def add_sample(label, features, sign_system="ASL", is_two_handed=False, user_id=None):
        """Inserts a single landmark feature vector."""
        doc = {
            "label": label.strip().upper(),
            "sign_system": sign_system.upper(),
            "is_two_handed": is_two_handed,
            "features": list(features),
            "user_id": user_id,
            "created_at": datetime.utcnow(),
        }
        res = db_manager.gestures.insert_one(doc)
        return str(res.inserted_id)

    @staticmethod
    def import_csv(csv_path, sign_system="ASL", batch_size=5000, replace=False):
        """
        High-performance bulk import of large landmark CSV files into MongoDB.
        Uses vectorized extraction and batched insert_many operations.
        If replace=True, removes prior samples for this source file before inserting.
        """
        from backend.config import Config
        resolved_path = csv_path if os.path.isabs(csv_path) else (
            csv_path if os.path.exists(csv_path) else os.path.join(Config.DATA_DIR, os.path.basename(csv_path))
        )
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"CSV not found at: {csv_path} or {resolved_path}")

        df = pd.read_csv(resolved_path)
        if "label" not in df.columns:
            raise ValueError("CSV must contain a 'label' column.")

        source_name = os.path.basename(resolved_path)
        system_clean = str(sign_system).strip().upper()

        if replace:
            db_manager.gestures.delete_many({
                "$or": [
                    {"source_file": source_name},
                    {"sign_system": system_clean, "source_file": {"$exists": False}}
                ]
            })

        feature_cols = [c for c in df.columns if c != "label"]
        num_features = len(feature_cols)
        now = datetime.utcnow()

        labels = df["label"].astype(str).str.strip().str.upper().values
        feature_matrix = df[feature_cols].values.astype(float)

        total_rows = len(df)
        total_inserted = 0

        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_docs = []
            for i in range(start_idx, end_idx):
                feats = feature_matrix[i].tolist()
                is_two_handed = (num_features >= 126 and any(abs(f) > 1e-5 for f in feats[63:126]))
                batch_docs.append({
                    "label": labels[i],
                    "sign_system": system_clean,
                    "source_file": source_name,
                    "is_two_handed": is_two_handed,
                    "features": feats,
                    "created_at": now,
                })
            
            if batch_docs:
                db_manager.gestures.insert_many(batch_docs, ordered=False)
                total_inserted += len(batch_docs)

        return {
            "imported_count": total_inserted,
            "unique_labels": list(df["label"].unique()),
            "sign_system": system_clean,
        }

    @staticmethod
    def export_to_csv(output_path, sign_system=None):
        """
        Exports gesture samples from MongoDB into a standard training CSV file.
        """
        query = {}
        if sign_system:
            query["sign_system"] = sign_system.upper()

        samples = list(db_manager.gestures.find(query))
        if not samples:
            raise ValueError("No gesture samples found in MongoDB to export.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        rows = []
        for s in samples:
            feats = s.get("features", [])
            # Pad or slice to 126
            if len(feats) < 126:
                feats = feats + [0.0] * (126 - len(feats))
            elif len(feats) > 126:
                feats = feats[:126]
            rows.append([s.get("label")] + feats)

        header = ["label"] + [f"f{i}" for i in range(126)]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        return {"exported_count": len(rows), "output_path": output_path}

    @staticmethod
    def get_stats():
        """Returns statistics on the gesture dataset stored in MongoDB."""
        all_samples = list(db_manager.gestures.find({}, {"label": 1, "sign_system": 1, "_id": 0}))
        total = len(all_samples)
        if total == 0:
            return {
                "total_samples": 0,
                "unique_signs": 0,
                "distribution": {},
                "systems": {},
            }

        distribution = {}
        systems = {}
        for s in all_samples:
            lbl = s.get("label", "UNKNOWN")
            sys_name = s.get("sign_system", "ASL")
            distribution[lbl] = distribution.get(lbl, 0) + 1
            systems[sys_name] = systems.get(sys_name, 0) + 1

        return {
            "total_samples": total,
            "unique_signs": len(distribution),
            "distribution": distribution,
            "systems": systems,
        }
