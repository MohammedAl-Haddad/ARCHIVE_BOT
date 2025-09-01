"""Shared helpers for test modules.

This module exposes :data:`TERM_RESOURCE_TAGS` which mirrors the
``TERM_RESOURCE_ALIASES`` mapping from ``bot.parser.hashtags`` but prefixes
each alias with ``#``.  Keeping the mapping in a single place ensures tests
remain in sync with the parser whenever new term resource tags are added.
"""

from __future__ import annotations

from bot.parser.hashtags import TERM_RESOURCE_ALIASES


# Map each term resource ``kind`` to the four accepted hashtag variants
# prefixed with ``#`` as they would appear in messages.
TERM_RESOURCE_TAGS = {
    kind: tuple(f"#{alias}" for alias in aliases)
    for kind, aliases in TERM_RESOURCE_ALIASES.items()
}

