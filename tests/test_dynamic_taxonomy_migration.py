import sqlite3
import time
from pathlib import Path

MIGRATION_SQL = Path('database/migrations/001_dynamic_taxonomy.sql').read_text().replace(
    "ADD COLUMN IF NOT EXISTS", "ADD COLUMN"
)


def _init_pre_migration(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE subjects (id INTEGER PRIMARY KEY);
        CREATE TABLE materials (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            year_id INTEGER,
            lecturer_id INTEGER
        );
        CREATE TABLE groups (id INTEGER PRIMARY KEY, tg_chat_id INTEGER NOT NULL);
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


def _run_migration(conn: sqlite3.Connection, *, skip_add_columns: bool = False) -> None:
    sql = MIGRATION_SQL
    if skip_add_columns:
        sql = "\n".join(
            line for line in sql.splitlines() if "ADD COLUMN" not in line
        )
    conn.executescript(sql)
    conn.commit()


def test_migration_creates_schema(tmp_path):
    db = sqlite3.connect(tmp_path / 'db.sqlite')
    _init_pre_migration(db)
    _run_migration(db)

    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert {'sections', 'cards', 'item_types', 'hashtag_aliases', 'hashtag_mappings',
            'subject_section_enable', 'section_item_types', 'materials', 'topics', 'groups'} <= tables

    cur = db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    triggers = {r[0] for r in cur.fetchall()}
    assert {'trg_sections_updated_at', 'trg_cards_updated_at', 'trg_item_types_updated_at',
            'trg_hashtag_aliases_updated_at', 'trg_hashtag_mappings_updated_at',
            'trg_subject_section_enable_updated_at', 'trg_section_item_types_updated_at'} <= triggers

    cur = db.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {r[0] for r in cur.fetchall()}
    assert {'idx_cards_section', 'ux_hashtag_aliases_normalized', 'ux_hashtag_mappings_alias',
            'idx_hashtag_mappings_target', 'idx_subject_section_enable_subject',
            'idx_section_item_types_item', 'idx_materials_subj_section_year_lect_cat',
            'idx_materials_subj_section_year_lect_itemtype_lectno'} <= indexes


def test_foreign_keys_cascade(tmp_path):
    db = sqlite3.connect(tmp_path / 'db.sqlite')
    _init_pre_migration(db)
    _run_migration(db)
    db.execute('PRAGMA foreign_keys=ON')

    sid = db.execute("INSERT INTO sections (label_ar, label_en) VALUES ('a','b')").lastrowid
    iid = db.execute("INSERT INTO item_types (label_ar, label_en) VALUES ('x','y')").lastrowid
    db.execute("INSERT INTO section_item_types (section_id, item_type_id) VALUES (?, ?)", (sid, iid))
    db.commit()

    db.execute("DELETE FROM sections WHERE id=?", (sid,))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM section_item_types").fetchone()[0] == 0


def test_updated_at_changes(tmp_path):
    db = sqlite3.connect(tmp_path / 'db.sqlite')
    _init_pre_migration(db)
    _run_migration(db)

    sid = db.execute("INSERT INTO sections (label_ar, label_en) VALUES ('a','b')").lastrowid
    before = db.execute("SELECT updated_at FROM sections WHERE id=?", (sid,)).fetchone()[0]
    time.sleep(1)
    db.execute("UPDATE sections SET label_en='c' WHERE id=?", (sid,))
    after = db.execute("SELECT updated_at FROM sections WHERE id=?", (sid,)).fetchone()[0]
    assert after > before


def test_migration_idempotent(tmp_path):
    db = sqlite3.connect(tmp_path / 'db.sqlite')
    _init_pre_migration(db)
    _run_migration(db)
    first = set(db.execute("SELECT type, name FROM sqlite_master").fetchall())
    _run_migration(db, skip_add_columns=True)
    second = set(db.execute("SELECT type, name FROM sqlite_master").fetchall())
    assert first == second
