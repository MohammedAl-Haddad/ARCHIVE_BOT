import asyncio
from pathlib import Path
import sys
import os

import aiosqlite
import pytest

# Ensure repository root is on the import path so ``bot`` package is found
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Provide dummy environment variables required by bot.config when importing
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")
os.environ.setdefault("ADMIN_USER_IDS", "1")
os.environ.setdefault("GROUP_ID", "1")

from bot.db import base

@pytest.fixture()
def repo_db(tmp_path, monkeypatch):
    """Create a temporary sqlite database for repository tests."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(base, "DB_PATH", str(db_path))

    async def setup() -> None:
        async with aiosqlite.connect(str(db_path)) as db:
            await db.executescript(
                """
                CREATE TABLE sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label_ar TEXT,
                    label_en TEXT,
                    is_enabled INTEGER,
                    sort_order INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER,
                    label_ar TEXT,
                    label_en TEXT,
                    show_when_empty INTEGER,
                    is_enabled INTEGER,
                    sort_order INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE item_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label_ar TEXT,
                    label_en TEXT,
                    requires_lecture INTEGER,
                    allows_year INTEGER,
                    allows_lecturer INTEGER,
                    is_enabled INTEGER,
                    sort_order INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE section_item_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL,
                    item_type_id INTEGER NOT NULL,
                    is_enabled INTEGER,
                    sort_order INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(section_id, item_type_id)
                );
                CREATE TABLE subject_section_enable (
                    subject_id INTEGER,
                    section_id INTEGER,
                    is_enabled INTEGER,
                    sort_order INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(subject_id, section_id)
                );
                CREATE TABLE hashtag_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias TEXT UNIQUE,
                    normalized TEXT,
                    lang TEXT
                );
                CREATE UNIQUE INDEX ux_hashtag_aliases_normalized
                    ON hashtag_aliases(normalized COLLATE NOCASE);
                CREATE TABLE hashtag_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias_id INTEGER,
                    target_kind TEXT,
                    target_id INTEGER,
                    is_content_tag INTEGER,
                    overrides TEXT
                );
                CREATE UNIQUE INDEX ux_hashtag_mappings_alias
                    ON hashtag_mappings(alias_id);
                CREATE TABLE materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    section_id INTEGER,
                    category_id INTEGER,
                    item_type_id INTEGER,
                    title TEXT NOT NULL,
                    url TEXT,
                    year_id INTEGER,
                    lecturer_id INTEGER,
                    lecture_no INTEGER,
                    content_hash TEXT,
                    tg_storage_chat_id INTEGER,
                    tg_storage_msg_id INTEGER,
                    file_unique_id TEXT,
                    source_chat_id INTEGER,
                    source_topic_id INTEGER,
                    source_message_id INTEGER,
                    created_by_admin_id INTEGER
                );
                CREATE TABLE groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_chat_id INTEGER UNIQUE NOT NULL,
                    title TEXT,
                    level_id INTEGER,
                    term_id INTEGER,
                    section_id INTEGER
                );
                CREATE TABLE topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    tg_topic_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    section_id INTEGER,
                    UNIQUE(group_id, tg_topic_id)
                );
                CREATE TABLE admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER UNIQUE,
                    name TEXT,
                    role TEXT,
                    permissions_mask INTEGER,
                    level_scope TEXT,
                    is_active INTEGER
                );
                CREATE TABLE roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    tags TEXT,
                    is_enabled INTEGER
                );
                CREATE TABLE role_permissions (
                    role_id INTEGER,
                    permission_key TEXT,
                    scope TEXT,
                    PRIMARY KEY(role_id, permission_key)
                );
                CREATE TABLE user_roles (
                    user_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY(user_id, role_id)
                );
                """
            )
            await db.commit()

    asyncio.run(setup())
    return str(db_path)


@pytest.fixture
def anyio_backend():
    """Force anyio tests to use the asyncio backend."""
    return "asyncio"
