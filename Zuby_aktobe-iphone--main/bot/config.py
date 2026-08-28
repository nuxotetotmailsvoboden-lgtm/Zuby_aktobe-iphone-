import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.up.railway.app")
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")
INSTAGRAM_VERIFICATION_ENABLED = os.getenv("INSTAGRAM_VERIFICATION_ENABLED", "False") == "True"
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
