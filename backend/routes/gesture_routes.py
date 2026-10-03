"""
backend/routes/gesture_routes.py

Gesture dataset management, MongoDB CSV bulk import/export,
and real-time letter-to-word construction endpoints.
"""

import os
from flask import Blueprint, request
from backend.config import Config
from backend.models.gesture_model import GestureModel
from backend.utils.word_engine import construct_word_from_letters, autocomplete_prefix, autocorrect_word
from backend.utils.helpers import api_response

gesture_bp = Blueprint("gestures", __name__, url_prefix="/api/gestures")


@gesture_bp.get("/stats")
def get_dataset_stats():
    """Returns dataset summary statistics from MongoDB."""
    stats = GestureModel.get_stats()
    return api_response(data=stats)


@gesture_bp.post("/import-csv")
def import_csv_endpoint():
    """
    Imports a CSV dataset file into MongoDB.
    Body: {"filename": "gestures.csv", "sign_system": "ASL"}
    """
    data = request.get_json() or {}
    filename = data.get("filename", "gestures.csv")
    sign_system = data.get("sign_system", "ASL")

    csv_path = filename if os.path.isabs(filename) else os.path.join(Config.DATA_DIR, filename)
    try:
        result = GestureModel.import_csv(csv_path, sign_system=sign_system)
        return api_response(data=result, message=f"Imported {result['imported_count']} samples into MongoDB.")
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=400)


@gesture_bp.post("/export-csv")
def export_csv_endpoint():
    """
    Exports MongoDB gesture samples to a CSV file for training.
    Body: {"filename": "gestures_exported.csv", "sign_system": "ASL"}
    """
    data = request.get_json() or {}
    filename = data.get("filename", "gestures_from_mongo.csv")
    sign_system = data.get("sign_system")

    output_path = filename if os.path.isabs(filename) else os.path.join(Config.DATA_DIR, filename)
    try:
        result = GestureModel.export_to_csv(output_path, sign_system=sign_system)
        return api_response(data=result, message=f"Exported {result['exported_count']} samples to {output_path}.")
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=400)


@gesture_bp.post("/word-construct")
def word_construct_endpoint():
    """
    Assembles a stream of fingerspelled letters into a clean dictionary word
    with autocomplete and spell autocorrect.
    Body: {"letters": ["H", "E", "L", "O"]}
    """
    data = request.get_json() or {}
    letters = data.get("letters", [])
    if isinstance(letters, str):
        letters = list(letters)

    result = construct_word_from_letters(letters)
    return api_response(data=result)


@gesture_bp.get("/autocomplete")
def autocomplete_endpoint():
    """
    Returns autocomplete suggestions for a given prefix.
    Query: ?prefix=HEL
    """
    prefix = request.args.get("prefix", "")
    suggestions = autocomplete_prefix(prefix, max_results=5)
    return api_response(data={"prefix": prefix, "suggestions": suggestions})
