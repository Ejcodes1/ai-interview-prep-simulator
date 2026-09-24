"""Development entry point: `python run.py` or `flask --app run run`."""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Default to 5050, not 5000: on macOS, port 5000 is claimed by the
    # AirPlay Receiver (Control Center), which will otherwise grab it back
    # out from under the dev server. Override with the PORT env var.
    port = int(os.environ.get("PORT", 5050))
    # 0.0.0.0 so the app is reachable from outside a Docker container via
    # its port mapping; Flask's own default (127.0.0.1) would only be
    # reachable from inside the container itself. Override with HOST.
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
