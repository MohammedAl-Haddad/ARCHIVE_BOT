-- 002_backfill_taxonomy.sql — populate taxonomy tables and link old data
-- Goal: migrate existing textual section/category values to the new
--       sections/cards/item_types tables and set foreign keys.

PRAGMA foreign_keys=ON;
BEGIN;

-- 1) Sections from legacy materials.section values
INSERT INTO sections (key, label_ar, label_en, is_enabled, sort_order)
SELECT DISTINCT m.section, m.section, m.section, 1, 0
FROM materials m
WHERE m.section IS NOT NULL
  AND m.section NOT IN (SELECT key FROM sections);

-- 2) Cards from legacy materials.category values
INSERT INTO cards (key, label_ar, label_en, section_id, show_when_empty, is_enabled, sort_order)
SELECT DISTINCT m.category, m.category, m.category, NULL, 0, 1, 0
FROM materials m
WHERE m.category IS NOT NULL
  AND m.category NOT IN (SELECT key FROM cards);

-- 3) Item types mirror legacy categories
INSERT INTO item_types (key, label_ar, label_en, requires_lecture, allows_year, allows_lecturer, is_enabled, sort_order)
SELECT DISTINCT m.category, m.category, m.category, 0, 1, 1, 1, 0
FROM materials m
WHERE m.category IS NOT NULL
  AND m.category NOT IN (SELECT key FROM item_types);

-- 4) Backfill materials with FK references
UPDATE materials
SET section_id = (SELECT id FROM sections s WHERE s.key = materials.section),
    category_id = (SELECT id FROM cards c WHERE c.key = materials.category),
    item_type_id = (SELECT id FROM item_types i WHERE i.key = materials.category)
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
