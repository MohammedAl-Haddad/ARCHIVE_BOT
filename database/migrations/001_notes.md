# 001_fix.sql notes

Adds supporting constraints and indices for migration P0.1:

- Uniqueness on `hashtag_mappings.alias_id` to prevent multiple targets per alias.
- Read indices to speed up lookup queries on mappings, cards, and section relations.
- Case-insensitive normalized uniqueness for `hashtag_aliases`.
- All wrapped in a transaction with `PRAGMA foreign_keys` enabled.
