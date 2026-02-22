"""Configuration and shared constants."""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {MINIMAX_API_KEY}",
    "Content-Type": "application/json",
}

# Shared HTTP session with default timeout
api_session = requests.Session()
api_session.headers.update(HEADERS)
api_session.timeout = 120


def validate_config():
    """Validate required configuration at startup."""
    if not MINIMAX_API_KEY:
        print("ERROR: MINIMAX_API_KEY not set. Copy .env.example to .env and add your key.", file=sys.stderr)
        sys.exit(1)
