"""One-time: register this app's webhook with Strava. Run: python -m app.subscribe"""
from dotenv import load_dotenv

load_dotenv()

from .main import BASE_URL, VERIFY_TOKEN  # noqa: E402
from .strava import subscribe_webhook  # noqa: E402

if __name__ == "__main__":
    print(subscribe_webhook(f"{BASE_URL}/strava/webhook", VERIFY_TOKEN))
