import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    PORT: str = os.getenv("PORT", "8080")

    DATABASE_URL_RAW: str = os.getenv("DATABASE_URL", "")
    REDIS_URL_RAW: str = os.getenv("REDIS_URL", "")

    ADMIN_IDS: str = os.getenv("ADMIN_IDS", "")
    SUPERADMIN_IDS: str = os.getenv("SUPERADMIN_IDS", "")

    @property
    def SUPERADMINS(self) -> list[int]:
        return self._parse_ids(self.SUPERADMIN_IDS)
    
    @property
    def ADMINS(self) -> list[int]:
        return self._parse_ids(self.ADMIN_IDS)
    
    def _parse_ids(self, ids_str: str) -> list[int]:
        if not ids_str.strip():
            return []
        return [int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()]

    @property
    def DATABASE_URL(self) -> str:
        # Берём сырой URL из Railway
        url = self.DATABASE_URL_RAW
        if url:
            # Преобразуем в asyncpg
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        # fallback (если нет DATABASE_URL)
        return (
            f"postgresql+asyncpg://{os.getenv('PGUSER', 'postgres')}:"
            f"{os.getenv('PGPASSWORD', '')}@{os.getenv('PGHOST', 'localhost')}:"
            f"{os.getenv('PGPORT', '5432')}/{os.getenv('PGDATABASE', 'railway')}"
        )

    @property
    def REDIS_URL(self) -> str:
        return self.REDIS_URL_RAW or f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB', '0')}"

    # Константы
    MAX_TOTAL_DISCOUNT: float = 40.0
    MAX_DISCOUNT_WITHOUT_VISIT: float = 15.0
    MAX_REFERRAL_DISCOUNT: float = 15.0
    MAX_CONTENT_DISCOUNT: float = 10.0
    MAX_CASHBACK_DISCOUNT: float = 15.0
    DISCOUNT_LIFETIME_DAYS: int = 40
    REFERRAL_REWARD_PERCENT: float = 1.0
    CASHBACK_BASE_PERCENT: float = 3.0
    CASHBACK_VIP_PERCENT: float = 10.0
    WHEEL_COOLDOWN_HOURS: int = 24

settings = Settings()
