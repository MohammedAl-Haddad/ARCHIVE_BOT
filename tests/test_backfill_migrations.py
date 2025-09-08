import sqlite3
from pathlib import Path

MIGRATION_SQL = Path('database/migrations/001_dynamic_taxonomy.sql').read_text().replace(
    "ADD COLUMN IF NOT EXISTS", "ADD COLUMN",
)
BACKFILL_A_SQL = Path('database/migrations/002_backfill_A.sql').read_text()
BACKFILL_B_SQL = Path('database/migrations/002_backfill_B.sql').read_text()


def _ensure_key_columns(conn: sqlite3.Connection) -> None:
    for tbl in ('sections', 'cards', 'item_types'):
        cols = {r[1] for r in conn.execute(f'PRAGMA table_info({tbl})')}
        if 'key' not in cols:
            conn.execute(f'ALTER TABLE {tbl} ADD COLUMN key TEXT')
        conn.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ux_{tbl}_key ON {tbl}(key)')
    conn.commit()


def _init_legacy_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE subjects (id INTEGER PRIMARY KEY);
        CREATE TABLE materials (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            year_id INTEGER,
            lecturer_id INTEGER,
            section TEXT,
            category TEXT,
            source_chat_id INTEGER,
            source_topic_id INTEGER,
            source_message_id INTEGER
        );
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY,
            tg_chat_id INTEGER NOT NULL
        );
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            group_id INTEGER NOT NULL,
            tg_topic_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            section TEXT,
            UNIQUE(group_id, tg_topic_id)
        );
        """
    )
    conn.commit()


def _init_cold_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE subjects (id INTEGER PRIMARY KEY);
        CREATE TABLE materials (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            year_id INTEGER,
            lecturer_id INTEGER,
            source_chat_id INTEGER,
            source_topic_id INTEGER,
            source_message_id INTEGER
        );
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY,
            tg_chat_id INTEGER NOT NULL
        );
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            group_id INTEGER NOT NULL,
            tg_topic_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            UNIQUE(group_id, tg_topic_id)
        );
        """
    )
    conn.commit()


def test_legacy_scenario():
    db = sqlite3.connect(':memory:')
    _init_legacy_schema(db)
    assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1

    sid = db.execute('INSERT INTO subjects DEFAULT VALUES').lastrowid
    gid = db.execute('INSERT INTO groups (tg_chat_id) VALUES (10)').lastrowid
    db.execute(
        'INSERT INTO materials (subject_id, section, category, source_chat_id, source_topic_id, source_message_id) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (sid, 'legacy_section', 'legacy_category', 10, 100, 1),
    )
    db.execute(
        'INSERT INTO topics (group_id, tg_topic_id, subject_id, section) VALUES (?, ?, ?, ?)',
        (gid, 100, sid, None),
    )
    db.commit()

    db.executescript(MIGRATION_SQL)
    _ensure_key_columns(db)
    db.executescript(BACKFILL_A_SQL)

    section_id = db.execute(
        "SELECT id FROM sections WHERE key='legacy_section'"
    ).fetchone()[0]
    card_id = db.execute(
        "SELECT id FROM cards WHERE key='legacy_category'"
    ).fetchone()[0]
    item_type_id = db.execute(
        "SELECT id FROM item_types WHERE key='legacy_category'"
    ).fetchone()[0]

    assert db.execute('SELECT section_id, category_id, item_type_id FROM materials').fetchone() == (
        section_id,
        card_id,
        item_type_id,
    )
    assert db.execute('SELECT section_id FROM topics').fetchone()[0] == section_id

    snapshot = {
        'sections': db.execute('SELECT * FROM sections ORDER BY id').fetchall(),
        'cards': db.execute('SELECT * FROM cards ORDER BY id').fetchall(),
        'item_types': db.execute('SELECT * FROM item_types ORDER BY id').fetchall(),
        'materials': db.execute('SELECT section_id, category_id, item_type_id FROM materials').fetchall(),
        'topics': db.execute('SELECT section_id FROM topics').fetchall(),
    }

    db.executescript(BACKFILL_A_SQL)

    assert snapshot['sections'] == db.execute('SELECT * FROM sections ORDER BY id').fetchall()
    assert snapshot['cards'] == db.execute('SELECT * FROM cards ORDER BY id').fetchall()
    assert snapshot['item_types'] == db.execute('SELECT * FROM item_types ORDER BY id').fetchall()
    assert snapshot['materials'] == db.execute('SELECT section_id, category_id, item_type_id FROM materials').fetchall()
    assert snapshot['topics'] == db.execute('SELECT section_id FROM topics').fetchall()


def test_cold_start_scenario():
    db = sqlite3.connect(':memory:')
    _init_cold_schema(db)
    assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1

    db.executescript(MIGRATION_SQL)
    _ensure_key_columns(db)

    before = set(db.execute('SELECT type, name, sql FROM sqlite_master').fetchall())
    db.executescript(BACKFILL_B_SQL)
    after = set(db.execute('SELECT type, name, sql FROM sqlite_master').fetchall())
    assert before == after
