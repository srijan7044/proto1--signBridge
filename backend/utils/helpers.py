"""
backend/utils/helpers.py

Helper utilities for JSON responses, BSON serialization, and data normalization.
"""

from bson import ObjectId
from datetime import datetime
from flask import jsonify

def serialize_doc(doc):
    """Recursively converts BSON ObjectId and datetime objects to JSON serializable types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        res = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                res[k] = str(v)
            elif isinstance(v, datetime):
                res[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                res[k] = serialize_doc(v)
            else:
                res[k] = v
        return res
    return doc


def api_response(success=True, data=None, message="", error=None, status_code=200):
    """Standardized API response envelope."""
    payload = {
        "success": success,
        "message": message,
    }
    if data is not None:
        payload["data"] = serialize_doc(data)
    if error is not None:
        payload["error"] = error

    return jsonify(payload), status_code
