"""
Configuration — loads from environment variables.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # Discord
    discord_token: str = field(default_factory=lambda: os.environ["DISCORD_BOT_TOKEN"])
    alert_channel_id: int = field(
        default_factory=lambda: int(os.environ.get("ALERT_CHANNEL_ID", "0"))
    )

    # Database (Supabase PostgreSQL — async driver)
    database_url: str = field(
        default_factory=lambda: os.environ["DATABASE_URL"]
    )

    # Timezone for daily task scheduling
    timezone: str = field(
        default_factory=lambda: os.environ.get("TIMEZONE", "America/Bogota")
    )

    # Hour to run the daily check (0-23, default 7 AM)
    check_hour: int = field(
        default_factory=lambda: int(os.environ.get("CHECK_HOUR", "7"))
    )

    # Alert thresholds (days before due date)
    alert_thresholds: tuple[int, ...] = (90, 30, 15, 3)


config = Config()
