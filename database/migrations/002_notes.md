# 002_backfill_A.sql and 002_backfill_B.sql notes

Provides two code paths for taxonomy backfill depending on deployment state:

- `002_backfill_A.sql` runs when legacy columns (`materials.section`, `materials.category`, `topics.section`) exist. It seeds baseline sections and populates foreign keys, leaving unmatched rows `NULL`.
- `002_backfill_B.sql` is for cold-start deployments where no backfill is required.

Both scripts enable `PRAGMA foreign_keys` and wrap operations in a transaction.
