"""Configuration facade: provides `config` object and back-compat globals."""

from .config import Config
from .constants import ENV_FILE  # re-export if someone needs it

# Build a singleton config instance
config = Config.from_env()

# --- Backward compatibility exports (minimize breaking changes) ---
BOT_TOKEN = config.BOT_TOKEN
ARCHIVE_CHANNEL_ID = config.ARCHIVE_CHANNEL_ID
GROUP_ID = config.GROUP_ID
OWNER_TG_ID = config.OWNER_TG_ID
ADMIN_USER_IDS = config.ADMIN_USER_IDS
VERSION = config.VERSION
START_TIME = config.START_TIME

__all__ = [
    "config",
    "ENV_FILE",
    "BOT_TOKEN",
    "ARCHIVE_CHANNEL_ID",
    "GROUP_ID",
    "OWNER_TG_ID",
    "ADMIN_USER_IDS",
    "VERSION",
    "START_TIME",
]
