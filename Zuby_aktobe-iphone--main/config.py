import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    PORT: str = os.getenv("PORT", "8080")

    # PostgreSQL — Railway передаёт PG-переменные
    DB_HOST: str = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
    DB_PORT: int = int(os.getenv("PGPORT", os.getenv("DB_PORT", "5432")))
    DB_USER: str = os.getenv("PGUSER", os.getenv("DB_USER", "postgres"))
    DB_PASS: str = os.getenv("PGPASSWORD", os.getenv("DB_PASS", ""))
    DB_NAME: str = os.getenv("PGDATABASE", os.getenv("DB_NAME", "dentist_db"))

    # Redis — Railway даёт REDIS_URL
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_URL_RAW: str = os.getenv("REDIS_URL", "")

    ADMIN_IDS: str = os.getenv("ADMINS", os.getenv("ADMIN_IDS", ""))
    SUPERADMIN_IDS: str = os.getenv("SUPERADMINS", os.getenv("SUPERADMIN_IDS", ""))

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
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        # Если есть прямая ссылка от Railway — используем её
        if self.REDIS_URL_RAW:
            return self.REDIS_URL_RAW
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

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
