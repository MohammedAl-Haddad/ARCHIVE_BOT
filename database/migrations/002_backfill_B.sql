-- 002_backfill_B.sql — Cold start no-op migration
-- Use this when there is NO legacy textual schema to backfill from.
PRAGMA foreign_keys=ON;
BEGIN;
-- No-op
COMMIT;
