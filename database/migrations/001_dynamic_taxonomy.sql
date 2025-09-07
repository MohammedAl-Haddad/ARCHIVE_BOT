-- Migration: dynamic taxonomy tables and schema updates
-- Creates sections/cards/item types/hashtag aliasing and mappings
-- Adds section_id/category_id/item_type_id/lecture_no/content_hash to materials
-- Replaces textual section with section_id in topics and groups

-- sections
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

-- cards (material categories/cards)
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    section_id INTEGER,
    show_when_empty INTEGER NOT NULL DEFAULT 0,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (section_id) REFERENCES sections(id)
);

-- item types
CREATE TABLE IF NOT EXISTS item_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    label_ar TEXT NOT NULL,
    label_en TEXT NOT NULL,
    requires_lecture INTEGER NOT NULL DEFAULT 0,
    allows_year INTEGER NOT NULL DEFAULT 1,
    allows_lecturer INTEGER NOT NULL DEFAULT 1,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);

-- hashtag aliases
CREATE TABLE IF NOT EXISTS hashtag_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias TEXT NOT NULL UNIQUE,
    normalized TEXT NOT NULL,
    lang TEXT
);

-- hashtag mappings
CREATE TABLE IF NOT EXISTS hashtag_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_id INTEGER NOT NULL,
    target_kind TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    is_content_tag INTEGER NOT NULL DEFAULT 0,
    overrides TEXT,
    FOREIGN KEY (alias_id) REFERENCES hashtag_aliases(id)
);

-- subject section enablement
CREATE TABLE IF NOT EXISTS subject_section_enable (
    subject_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (subject_id, section_id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (section_id) REFERENCES sections(id)
);

-- optional: section rules
CREATE TABLE IF NOT EXISTS section_rules (
    section_id INTEGER PRIMARY KEY,
    requires_lecture INTEGER NOT NULL DEFAULT 0,
    allows_year INTEGER NOT NULL DEFAULT 1,
    allows_lecturer INTEGER NOT NULL DEFAULT 1,
    extra TEXT,
    FOREIGN KEY (section_id) REFERENCES sections(id)
);

-- optional: link allowed item types per section
CREATE TABLE IF NOT EXISTS section_item_types (
    section_id INTEGER NOT NULL,
    item_type_id INTEGER NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (section_id, item_type_id),
    FOREIGN KEY (section_id) REFERENCES sections(id),
    FOREIGN KEY (item_type_id) REFERENCES item_types(id)
);

-- augment materials table
ALTER TABLE materials ADD COLUMN section_id INTEGER;
ALTER TABLE materials ADD COLUMN category_id INTEGER;
ALTER TABLE materials ADD COLUMN item_type_id INTEGER;
ALTER TABLE materials ADD COLUMN lecture_no INTEGER;
ALTER TABLE materials ADD COLUMN content_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_materials_subj_section_year_lect_cat
ON materials(subject_id, section_id, year_id, lecturer_id, category_id);

CREATE INDEX IF NOT EXISTS idx_materials_subj_section_year_lect_itemtype_lectno
ON materials(subject_id, section_id, year_id, lecturer_id, item_type_id, lecture_no);

-- topics: replace section text with section_id
ALTER TABLE topics RENAME TO topics_old;
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    tg_topic_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    section_id INTEGER,
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    UNIQUE (group_id, tg_topic_id)
);
INSERT INTO topics (id, group_id, tg_topic_id, subject_id, section_id)
SELECT id, group_id, tg_topic_id, subject_id, NULL FROM topics_old;
DROP TABLE topics_old;

-- groups: add section_id column
ALTER TABLE groups ADD COLUMN section_id INTEGER REFERENCES sections(id);
