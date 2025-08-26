# bot/config/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
from .constants import ENV_FILE  # ".env"

@dataclass(frozen=True)
class Config:
    # required
    BOT_TOKEN: str
    ARCHIVE_CHANNEL_ID: int
    OWNER_TG_ID: int

    # optional
    GROUP_ID: Optional[int]
    ADMIN_USER_IDS: List[int]
    VERSION: str
    START_TIME: datetime

    @staticmethod
    def _to_int(key: str, *, required: bool = False) -> Optional[int]:
        val = os.getenv(key)
        if val is None or not str(val).strip():
            if required:
                raise RuntimeError(f"{key} is missing in .env")
            return None
        try:
            return int(str(val).strip())
        except ValueError as e:
            raise RuntimeError(f"{key} must be an integer, got: {val!r}") from e

    @classmethod
    def from_env(cls) -> "Config":
        # load .env once
        load_dotenv(ENV_FILE)

        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is missing in .env")

        archive_channel_id = cls._to_int("ARCHIVE_CHANNEL_ID", required=True)
        owner_tg_id = cls._to_int("OWNER_TG_ID", required=True)
        group_id = cls._to_int("GROUP_ID", required=False)

        # comma-separated admin list
        _admins = os.getenv("ADMIN_USER_IDS", "")
        admin_user_ids = [int(x) for x in _admins.split(",") if x.strip().isdigit()]

        version = os.getenv("COMMIT_SHA", "dev")
        start_time = datetime.now()

        return cls(
            BOT_TOKEN=bot_token,
            ARCHIVE_CHANNEL_ID=archive_channel_id,  # type: ignore[arg-type]
            OWNER_TG_ID=owner_tg_id,                # type: ignore[arg-type]
            GROUP_ID=group_id,
            ADMIN_USER_IDS=admin_user_ids,
            VERSION=version,
            START_TIME=start_time,
        )
