-- 001_fix.sql — complementary constraints & indices for P0.1
-- Goal: tighten uniqueness and add read indices without table rebuilds.

PRAGMA foreign_keys=ON;

BEGIN;

-- 1) hashtag_mappings: prevent multiple targets per alias
CREATE UNIQUE INDEX IF NOT EXISTS ux_hashtag_mappings_alias
ON hashtag_mappings(alias_id);

-- helpful read pattern for lookups by target and content-type filter
CREATE INDEX IF NOT EXISTS idx_hashtag_mappings_target
ON hashtag_mappings(target_kind, target_id, is_content_tag);

-- 2) hashtag_aliases: normalized uniqueness (case-insensitive)
-- SQLite hint: COLLATE NOCASE on index to avoid duplicates like 'Slides'/'slides'
CREATE UNIQUE INDEX IF NOT EXISTS ux_hashtag_aliases_normalized
ON hashtag_aliases(normalized COLLATE NOCASE);

-- 3) cards: speed up section-level filtering
CREATE INDEX IF NOT EXISTS idx_cards_section
ON cards(section_id);

-- 4) subject_section_enable & section_item_types: common read paths
CREATE INDEX IF NOT EXISTS idx_subject_section_enable_subject
ON subject_section_enable(subject_id);

CREATE INDEX IF NOT EXISTS idx_section_item_types_item
ON section_item_types(item_type_id);

COMMIT;
