"""
server.py

SignBridge Root Server Entrypoint.
Initializes the modular backend app factory from backend/app.py.
"""

from backend.app import create_app
from backend.config import Config

app = create_app()

if __name__ == "__main__":
    print(f"🚀 SignBridge Server running on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
