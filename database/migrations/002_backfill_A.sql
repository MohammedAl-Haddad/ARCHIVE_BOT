-- 002_backfill_A.sql — populate taxonomy tables and link old data
-- Run only when legacy columns (materials.section, materials.category, topics.section) are present; leaves unmatched rows NULL.
-- Goal: migrate existing textual section/category values to the new
--       sections/cards/item_types tables and set foreign keys.

PRAGMA foreign_keys=ON;
BEGIN;

-- 0) Baseline sections for mapping
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
VALUES ('theory', 'theory', 'theory', 1, 0);
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
VALUES ('lab', 'lab', 'lab', 1, 0);
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
VALUES ('discussion', 'discussion', 'discussion', 1, 0);
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
VALUES ('field_trip', 'field_trip', 'field_trip', 1, 0);

-- 1) Sections from legacy materials.section values
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
SELECT DISTINCT m.section, m.section, m.section, 1, 0
FROM materials m
WHERE m.section IS NOT NULL;

-- 2) Cards from legacy materials.category values
INSERT OR IGNORE INTO cards (key, label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order)
SELECT DISTINCT m.category, m.category, m.category, NULL, 0, 1, 0
FROM materials m
WHERE m.category IS NOT NULL;

-- 3) Item types mirror legacy categories
INSERT OR IGNORE INTO item_types (key, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
SELECT DISTINCT m.category, m.category, m.category, 0, 1, 1, 1, 0
FROM materials m
WHERE m.category IS NOT NULL;

-- 4) Backfill materials with FK references
UPDATE materials
SET section_id = COALESCE(section_id, (SELECT id FROM sections s WHERE s.key = materials.section)),
    category_id = COALESCE(category_id, (SELECT id FROM cards c WHERE c.key = materials.category)),
    item_type_id = COALESCE(item_type_id, (SELECT id FROM item_types i WHERE i.key = materials.category))
WHERE section_id IS NULL
   OR category_id IS NULL
   OR item_type_id IS NULL;

-- 5) Populate topics.section_id using matching source topics
UPDATE topics
SET section_id = (
    SELECT m.section_id
    FROM materials m
    JOIN groups g ON g.id = topics.group_id
    WHERE m.source_chat_id = g.tg_chat_id
      AND m.source_topic_id = topics.tg_topic_id
    ORDER BY m.id
    LIMIT 1
)
WHERE section_id IS NULL;

-- 6) Populate groups.section_id from their topics
UPDATE groups
SET section_id = (
    SELECT t.section_id
    FROM topics t
    WHERE t.group_id = groups.id
      AND t.section_id IS NOT NULL
    ORDER BY t.id
    LIMIT 1
)
WHERE section_id IS NULL;

COMMIT;
