BEGIN;

-- sections
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS trg_sections_updated_at
AFTER UPDATE ON sections
FOR EACH ROW
BEGIN
    UPDATE sections SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- cards
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY,
    section_id INTEGER REFERENCES sections(id) ON DELETE CASCADE,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    show_when_empty INTEGER NOT NULL DEFAULT 0
);

CREATE TRIGGER IF NOT EXISTS trg_cards_updated_at
AFTER UPDATE ON cards
FOR EACH ROW
BEGIN
    UPDATE cards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_cards_section ON cards(section_id);

-- item types
CREATE TABLE IF NOT EXISTS item_types (
    id INTEGER PRIMARY KEY,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    requires_lecture INTEGER NOT NULL DEFAULT 0,
    allows_year INTEGER NOT NULL DEFAULT 1,
    allows_lecturer INTEGER NOT NULL DEFAULT 1
);

CREATE TRIGGER IF NOT EXISTS trg_item_types_updated_at
AFTER UPDATE ON item_types
FOR EACH ROW
BEGIN
    UPDATE item_types SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- hashtag aliases
CREATE TABLE IF NOT EXISTS hashtag_aliases (
    id INTEGER PRIMARY KEY,
    alias TEXT NOT NULL UNIQUE,
    normalized TEXT NOT NULL,
    lang TEXT,
    label_ar TEXT,
    label_en TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS trg_hashtag_aliases_updated_at
AFTER UPDATE ON hashtag_aliases
FOR EACH ROW
BEGIN
    UPDATE hashtag_aliases SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE UNIQUE INDEX IF NOT EXISTS ux_hashtag_aliases_normalized
ON hashtag_aliases(normalized COLLATE NOCASE);

-- hashtag mappings
CREATE TABLE IF NOT EXISTS hashtag_mappings (
    id INTEGER PRIMARY KEY,
    alias_id INTEGER NOT NULL REFERENCES hashtag_aliases(id) ON DELETE CASCADE,
    target_kind TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    is_content_tag INTEGER NOT NULL DEFAULT 0,
    overrides TEXT,
    label_ar TEXT,
    label_en TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS trg_hashtag_mappings_updated_at
AFTER UPDATE ON hashtag_mappings
FOR EACH ROW
BEGIN
    UPDATE hashtag_mappings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE UNIQUE INDEX IF NOT EXISTS ux_hashtag_mappings_alias
ON hashtag_mappings(alias_id);

CREATE INDEX IF NOT EXISTS idx_hashtag_mappings_target
ON hashtag_mappings(target_kind, target_id, is_content_tag);

-- subject section enablement
CREATE TABLE IF NOT EXISTS subject_section_enable (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, section_id)
);

CREATE TRIGGER IF NOT EXISTS trg_subject_section_enable_updated_at
AFTER UPDATE ON subject_section_enable
FOR EACH ROW
BEGIN
    UPDATE subject_section_enable SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_subject_section_enable_subject
ON subject_section_enable(subject_id);

-- section item types link
CREATE TABLE IF NOT EXISTS section_item_types (
    id INTEGER PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    item_type_id INTEGER NOT NULL REFERENCES item_types(id) ON DELETE CASCADE,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section_id, item_type_id)
);

CREATE TRIGGER IF NOT EXISTS trg_section_item_types_updated_at
AFTER UPDATE ON section_item_types
FOR EACH ROW
BEGIN
    UPDATE section_item_types SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_section_item_types_item
ON section_item_types(item_type_id);

-- augment materials table
ALTER TABLE materials ADD COLUMN IF NOT EXISTS section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES cards(id) ON DELETE SET NULL;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS item_type_id INTEGER REFERENCES item_types(id) ON DELETE SET NULL;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS lecture_no INTEGER;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS content_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_materials_subj_section_year_lect_cat
ON materials(subject_id, section_id, year_id, lecturer_id, category_id);

CREATE INDEX IF NOT EXISTS idx_materials_subj_section_year_lect_itemtype_lectno
ON materials(subject_id, section_id, year_id, lecturer_id, item_type_id, lecture_no);

-- recreate topics with section_id reference
ALTER TABLE topics RENAME TO topics_old;

CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    tg_topic_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL,
    UNIQUE(group_id, tg_topic_id)
);

INSERT INTO topics (id, group_id, tg_topic_id, subject_id, section_id)
SELECT id, group_id, tg_topic_id, subject_id, NULL
FROM topics_old;

DROP TABLE topics_old;

-- groups: add section_id column
ALTER TABLE groups ADD COLUMN IF NOT EXISTS section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL;

COMMIT;
