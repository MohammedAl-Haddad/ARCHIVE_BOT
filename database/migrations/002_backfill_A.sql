-- 002_backfill_A.sql — Backfill from legacy textual columns (run ONLY if legacy columns exist)
-- Assumptions:
--  - materials has legacy columns: section TEXT, category TEXT (nullable)
--  - topics has legacy column: section TEXT (nullable)
--  - cards/item_types/sections already exist (from 001_dynamic_taxonomy.sql)
-- WARNING: Run this ONLY if those legacy columns actually exist. Otherwise it will fail.

PRAGMA foreign_keys=ON;
BEGIN;

-- Seed canonical legacy sections if not present (you can delete any you don't want later)
INSERT OR IGNORE INTO sections (key, label_ar, label_en, is_enabled, sort_order)
VALUES 
  ('theory','نظري','Theory',1,0),
  ('lab','عملي','Lab',1,1),
  ('discussion','مناقشة','Discussion',1,2),
  ('field_trip','ميداني','Field Trip',1,3);

-- Backfill topics.section_id from topics.section (legacy)
-- NOTE: will fail if topics.section does not exist; only run when legacy column exists.
UPDATE topics
SET section_id = (
  SELECT s.id FROM sections s 
  WHERE LOWER(s.key) = LOWER(topics.section)
)
WHERE section_id IS NULL
  AND topics.section IS NOT NULL
  AND TRIM(topics.section) <> '';

-- Backfill materials.section_id from materials.section (legacy)
UPDATE materials
SET section_id = (
  SELECT s.id FROM sections s
  WHERE LOWER(s.key) = LOWER(materials.section)
)
WHERE section_id IS NULL
  AND materials.section IS NOT NULL
  AND TRIM(materials.section) <> '';

-- Backfill materials.category_id from materials.category matching cards.key
UPDATE materials
SET category_id = (
  SELECT c.id FROM cards c
  WHERE LOWER(c.key) = LOWER(materials.category)
)
WHERE category_id IS NULL
  AND materials.category IS NOT NULL
  AND TRIM(materials.category) <> '';

-- Backfill materials.item_type_id from materials.category matching item_types.key (if it was used for lecture content)
UPDATE materials
SET item_type_id = (
  SELECT it.id FROM item_types it
  WHERE LOWER(it.key) = LOWER(materials.category)
)
WHERE item_type_id IS NULL
  AND materials.category IS NOT NULL
  AND TRIM(materials.category) <> '';

COMMIT;
