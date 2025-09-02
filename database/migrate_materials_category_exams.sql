BEGIN TRANSACTION;
ALTER TABLE materials RENAME TO materials_old;
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    section TEXT NOT NULL CHECK(section IN (
        'theory','discussion','lab','field_trip','syllabus','apps',
        'vocabulary','references','skills','open_source_projects'
    )),
    category TEXT NOT NULL CHECK(category IN (
        'lecture','slides','audio','exam','exam_mid','exam_final','booklet','board_images','video','simulation',
        'summary','notes','external_link','mind_map','transcript','related','syllabus'
    )),
    title TEXT NOT NULL,
    url TEXT,
    year_id INTEGER,
    lecturer_id INTEGER,
    tg_storage_chat_id INTEGER,
    tg_storage_msg_id INTEGER,
    file_unique_id TEXT,
    source_chat_id INTEGER,
    source_topic_id INTEGER,
    source_message_id INTEGER,
    created_by_admin_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (year_id) REFERENCES years(id),
    FOREIGN KEY (lecturer_id) REFERENCES lecturers(id),
    FOREIGN KEY (created_by_admin_id) REFERENCES admins(id)
);
INSERT INTO materials (
    id, subject_id, section, category, title, url, year_id, lecturer_id,
    tg_storage_chat_id, tg_storage_msg_id, file_unique_id,
    source_chat_id, source_topic_id, source_message_id,
    created_by_admin_id, created_at
)
SELECT
    id, subject_id, section, category, title, url, year_id, lecturer_id,
    tg_storage_chat_id, tg_storage_msg_id, file_unique_id,
    source_chat_id, source_topic_id, source_message_id,
    created_by_admin_id, created_at
FROM materials_old;
DROP TABLE materials_old;
CREATE INDEX IF NOT EXISTS idx_materials_subject ON materials(subject_id);
CREATE INDEX IF NOT EXISTS idx_materials_year ON materials(year_id);
CREATE INDEX IF NOT EXISTS idx_materials_lecturer ON materials(lecturer_id);
CREATE INDEX IF NOT EXISTS idx_materials_admin ON materials(created_by_admin_id);
CREATE INDEX IF NOT EXISTS idx_materials_section_created_at ON materials(section, created_at);
COMMIT;
