import os

from app import create_app

app = create_app()

# Render par gunicorn "run:app" chalata hai, ye block sirf local run ke liye hai.
# Local par auto-reload/debug chahiye to .env mein FLASK_DEBUG=1 likh dein.
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )