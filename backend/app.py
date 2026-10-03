"""
backend/app.py

Flask Application Factory for SignBridge.
Registers API blueprints, connects MongoDB, and serves the frontend web portal.
"""

import os
from flask import Flask, send_from_directory
from backend.config import Config
from backend.db import db_manager
from backend.routes.auth_routes import auth_bp
from backend.routes.payment_routes import payment_bp
from backend.routes.gesture_routes import gesture_bp
from backend.routes.translate_routes import translate_bp


def create_app():
    app = Flask(
        __name__,
        static_folder=Config.WEB_DIR,
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(gesture_bp)
    app.register_blueprint(translate_bp)

    # Serve Root Index
    @app.route("/")
    def serve_index():
        return send_from_directory(Config.WEB_DIR, "index.html")

    # Serve direct web files (/style.css, /app.js, /favicon.ico)
    @app.route("/<path:path>")
    def serve_direct_static(path):
        full_path = os.path.join(Config.WEB_DIR, path)
        if os.path.exists(full_path):
            return send_from_directory(Config.WEB_DIR, path)
        return send_from_directory(Config.WEB_DIR, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"SignBridge Server starting on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
