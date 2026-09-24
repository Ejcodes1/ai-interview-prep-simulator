"""Development entry point: `python run.py` or `flask --app run run`."""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Default to 5050, not 5000: on macOS, port 5000 is claimed by the
    # AirPlay Receiver (Control Center), which will otherwise grab it back
    # out from under the dev server. Override with the PORT env var.
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=app.config.get("DEBUG", False), port=port)
