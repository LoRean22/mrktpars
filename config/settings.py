from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "mrktpars_bot")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    bot_token: str | None = os.getenv("BOT_TOKEN")

    default_check_interval: int = int(os.getenv("DEFAULT_CHECK_INTERVAL", 600))
    max_tasks_per_user: int = int(os.getenv("MAX_TASKS_PER_USER", 3))

    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", 3306))
    db_name: str = os.getenv("DB_NAME")
    db_user: str = os.getenv("DB_USER")
    db_password: str = os.getenv("DB_PASSWORD")



settings = Settings()
