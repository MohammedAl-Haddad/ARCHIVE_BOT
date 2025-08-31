"""Verify that important queries make use of database indexes.

This script creates an in-memory SQLite database using the schema from
``database/init.sql`` and runs ``EXPLAIN QUERY PLAN`` on a few typical
queries.  The output should reference the indexes defined in the schema,
confirming they will be used by SQLite.
"""

from pathlib import Path
import sqlite3


def explain(cursor: sqlite3.Cursor, query: str, params: tuple = ()) -> None:
    """Print the query plan for ``query`` with ``params``."""

    print(query)
    for row in cursor.execute(f"EXPLAIN QUERY PLAN {query}", params):
        print(row)
    print()


def main() -> None:
    db = sqlite3.connect(":memory:")
    sql_path = Path(__file__).resolve().parent.parent / "database" / "init.sql"
    db.executescript(sql_path.read_text(encoding="utf-8"))

    # Minimal rows to allow index lookups.
    db.execute(
        "INSERT INTO admins(tg_user_id, name, role, permissions_mask) VALUES (?,?,?,?)",
        (1, "admin", "root", 0),
    )
    db.execute(
        "INSERT INTO subjects(code, name, level_id, term_id) VALUES (?,?,?,?)",
        ("s", "subject", 1, 1),
    )
    db.execute(
        """
        INSERT INTO materials(subject_id, section, category, title, url, created_by_admin_id)
        VALUES (1, 'theory', 'lecture', 't', 'u', 1)
        """
    )

    cur = db.cursor()
    explain(cur, "SELECT * FROM admins WHERE tg_user_id > ?", (0,))
    explain(cur, "SELECT * FROM subjects WHERE term_id = ?", (1,))
    explain(
        cur,
        "SELECT created_at FROM materials WHERE section = ? ORDER BY created_at",
        ("theory",),
    )


if __name__ == "__main__":
    main()

