# Systems Overview

This document summarizes the main subsystems of the Archive Bot and links each one to the relevant source files, database tables, and flow documentation.

## System-A: Group/Topic Linking

**Relevant files / functions**
- `bot/handlers/topics.py` – binds Telegram topics to subjects (`insert_sub_start`, `insert_sub_received`, `bind` calls)
- `bot/db/topics.py` – `get_binding`, `bind`, `get_group_id_by_chat`
- `bot/db/groups.py` – group registry (`get_group_info`, `upsert_group`)

**Database tables**
- `groups`, `topics`, `subjects`

**Flow**
1. Admin issues `/insert_sub` in a topic.
2. Handler checks permissions and collects subject/section input.
3. Binding is saved in `topics` and group info updated.

**Flow docs**
- [FLOW_GROUP_LINKING.md](FLOW_GROUP_LINKING.md)
- [group-linking.md](group-linking.md)

## System-B: Navigation & Buttons

**Relevant files / functions**
- `bot/navigation/nav_stack.py` – manages navigation history (`NavStack`)
- `bot/navigation/tree.py` – loads child nodes from the database (`get_children`, caching)
- `bot/keyboards/builders/main_menu.py` & `paginated.py` – build inline keyboards
- `bot/handlers/navigation_tree.py` – drives navigation callbacks

**Database tables**
- `levels`, `terms`, `subjects`, `lecturers`, `years`, `materials`, `term_resources`

**Flow**
1. User opens the main menu and selects a level/term.
2. Navigation tree fetches available children and builds paginated keyboards.
3. Selections push/pop `NavStack` entries and progressively narrow down to materials or resources.

**Flow docs**
- [FLOW_NAVIGATION.md](FLOW_NAVIGATION.md)
- [navigation_tree_usage.md](navigation_tree_usage.md)

## System-C: Upload/Ingestion

**Relevant files / functions**
- `bot/handlers/ingestion.py` – processes uploads and parses hashtags
- `bot/parser/hashtags.py` – hashtag parsing utilities
- `bot/db/ingestions.py`, `bot/db/materials.py` – persist pending items and materials
- `bot/db/term_resources.py` – stores term-level resources when tagged

**Database tables**
- `ingestions`, `materials`, `term_resources`, `admins`, `groups`, `topics`

**Flow**
1. Admin sends content with hashtags.
2. `ingestion_handler` parses tags, resolves context (group, binding, year, lecturer).
3. Material/term resource is stored; an ingestion record is created for approval.

**Flow docs**
- [FLOW_INGESTION.md](FLOW_INGESTION.md)
- [content-upload.md](content-upload.md)

## System-D: Retrieval & Display

**Relevant files / functions**
- `bot/handlers/navigation_tree.py` – fetches materials/resources and copies them to the chat
- `bot/navigation/tree.py` – helpers such as `get_latest_material_by_category` and `get_latest_term_resource`
- `bot/utils/telegram.py` – message helpers (`send_ephemeral`, copy utilities)

**Database tables**
- `materials`, `term_resources`, `lectures`, `years`, `lecturers`

**Flow**
1. Navigation callback requests a leaf node.
2. Handler retrieves the latest material or resource from storage.
3. File or link is delivered to the user; failures are reported via ephemeral messages.

**Flow docs**
- [FLOW_NAVIGATION.md](FLOW_NAVIGATION.md)
- [navigation_tree_usage.md](navigation_tree_usage.md)

## System-E: Term-Level Resources

**Relevant files / functions**
- `bot/db/term_resources.py` – `insert_term_resource`, `get_latest_term_resource`, `list_term_resource_kinds`
- `bot/handlers/ingestion.py` – handles tagged term resource uploads
- `docs/term-resources.md` – tagging reference

**Database tables**
- `term_resources`

**Flow**
1. Admin posts a message with a term resource hashtag.
2. Ingestion stores the message ID in `term_resources`.
3. Navigation retrieves and serves the latest resource for each kind.

**Flow docs**
- [term-resources.md](term-resources.md)

## System-F: Permissions (Owner/Admins)

**Relevant files / functions**
- `bot/db/admins.py` – permission flags (`MANAGE_GROUPS`, `UPLOAD_CONTENT`, `APPROVE_CONTENT`, `MANAGE_ADMINS`), checks and CRUD
- `bot/handlers/admins.py` – conversation for listing and editing admins
- `bot/db/rbac.py` – `can_view` helper for read access

**Database tables**
- `admins`

**Flow**
1. Owner is ensured at startup and granted full permissions.
2. Admins manage others via `/admins` menu (list/add/update/remove).
3. Permission checks guard sensitive operations like linking or ingestion.

**Flow docs**
- [owner-guide.md](owner-guide.md)
- [moderators_guide_ar.md](moderators_guide_ar.md)

## System-G: Configuration & Environment

**Relevant files / functions**
- `bot/config/config.py` – loads environment variables into a `Config` dataclass
- `bot/config/__init__.py` – exposes the singleton `config` and legacy globals
- `.env` (via `ENV_FILE`) for runtime settings

**Database tables**
- (none)

**Flow**
1. On startup, `Config.from_env()` reads `.env` values (token, channel IDs, features).
2. The resulting `config` object is imported across modules for consistent settings.

**Flow docs**
- [README.md](README.md)

## System-H: Logging & Errors

**Relevant files / functions**
- `bot/utils/logging.py` – `setup_logging` configures global logging format/level
- `bot/utils/retry.py` – retry helper with warning logs
- Handlers throughout the project obtain named loggers for contextual messages

**Database tables**
- (none)

**Flow**
1. `main.py` calls `setup_logging()` at startup.
2. Modules log to namespaced loggers; `retry` emits warnings on transient failures.
3. Critical errors are caught and logged; users may receive ephemeral failure messages.

**Flow docs**
- (none)

