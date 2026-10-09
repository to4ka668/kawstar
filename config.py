import os
from pathlib import Path

# Load environment variables from .env file if available
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")

raw_admin_id = os.getenv("ADMIN_ID", "0")
try:
    ADMIN_ID = int(raw_admin_id)
except ValueError:
    ADMIN_ID = 0

DB_NAME = os.getenv("DB_NAME", "kaw_star.db")

DEFAULT_PRICE = 220
DEFAULT_STAR_COST_PRICE = 180
DEFAULT_MIN_STARS = 50
DEFAULT_MAX_STARS = 20000
