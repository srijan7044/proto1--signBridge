#!/usr/bin/env python
import argparse
import sys
import time
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.config import Config
from backend.db import db_manager
from backend.models.gesture_model import GestureModel

def main():
    parser = argparse.ArgumentParser(description="Import gesture CSV dataset into MongoDB.")
    parser.add_argument("--file", "-f", required=True, help="Path to CSV file")
    parser.add_argument("--system", "-s", default="ASL", help="Sign system (default: ASL)")
    parser.add_argument("--batch-size", "-b", type=int, default=5000, help="Batch size")
    parser.add_argument(
        "--replace", "-r",
        action="store_true",
        help="Replace existing samples for this file in MongoDB instead of appending duplicates"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" SIGNBRIDGE MONGODB DATASET IMPORTER")
    print("=" * 60)
    print(f"File: {args.file}")
    print(f"System: {args.system}")
    print(f"Database: {Config.MONGO_DB_NAME}")

    health = db_manager.health_check()
    if health["status"] == "connected":
        print("✓ Connected to MongoDB!")
    else:
        print(f"[NOTE] MongoDB status: {health.get('message', 'fallback mode')}")

    print("\nStarting batched import...")
    t1 = time.time()
    try:
        res = GestureModel.import_csv(
            args.file,
            sign_system=args.system,
            batch_size=args.batch_size,
            replace=args.replace
        )
        dur = time.time() - t1
        print("\n" + "=" * 60)
        print("✓ IMPORT SUCCESSFUL!")
        print("=" * 60)
        print(f"Samples Imported: {res['imported_count']:,}")
        print(f"Unique Labels:    {len(res['unique_labels'])}")
        print(f"Time Taken:       {dur:.2f} s")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
