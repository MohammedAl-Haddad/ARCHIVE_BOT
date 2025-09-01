BEGIN TRANSACTION;
ALTER TABLE term_resources RENAME TO term_resources_old;
CREATE TABLE term_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN (
        'attendance','study_plan','channels','outcomes','tips',
        'projects','programs','apps','skills','forums','sites'
    )),
    tg_storage_chat_id INTEGER NOT NULL,
    tg_storage_msg_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (level_id) REFERENCES levels(id),
    FOREIGN KEY (term_id) REFERENCES terms(id)
);
INSERT INTO term_resources (id, level_id, term_id, kind, tg_storage_chat_id, tg_storage_msg_id, created_at)
SELECT
    tr.id,
    COALESCE((SELECT level_id FROM groups WHERE term_id = tr.term_id AND level_id IS NOT NULL LIMIT 1), 1),
    tr.term_id,
    tr.kind,
    tr.tg_storage_chat_id,
    tr.tg_storage_msg_id,
    tr.created_at
FROM term_resources_old tr;
DROP TABLE term_resources_old;
DROP INDEX IF EXISTS idx_term_resources_term_kind;
CREATE INDEX idx_term_resources_level_term_kind
    ON term_resources(level_id, term_id, kind);
COMMIT;
