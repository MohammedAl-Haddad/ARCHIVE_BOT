from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional, Tuple

from .caption_parser import ParseError
from ..repo import taxonomy
from ..utils.formatting import ARABIC_ORDINALS

_DIGIT_TRANS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ORDINAL_WORDS = {v: k for k, v in ARABIC_ORDINALS.items()}


@dataclass
class SessionInfo:
    """Information extracted from a session tag."""

    number: Optional[int]
    title: Optional[str]
    entity_label: str


async def parse_session(
    item_type_id: int,
    text: str,
    *,
    lang: str = "ar",
) -> Tuple[SessionInfo, Optional[ParseError]]:
    """Parse *text* using the item type label from taxonomy.

    The expected format is ``#<label>_<number>: <title>`` where ``<label>`` is
    the normalised item type label.  ``text`` may omit the leading ``#``.  If
    the associated item type requires a session number but none is found, a
    ``ParseError('E-NO-SESSION')`` is returned.
    """

    item = await taxonomy.get_item_type(item_type_id, lang=lang, include_disabled=True)
    entity_label = item["label"] if item else ""

    base = entity_label[2:] if entity_label.startswith("ال") else entity_label
    token = re.escape(base.replace(" ", "_"))
    pattern = re.compile(rf"^#?(?:{token}|ال{token})_(.+?)(?::\s*(.+))?$")

    m = pattern.match(text.strip())
    number: Optional[int] = None
    title: Optional[str] = None
    if m:
        ident, title = m.groups()
        ident = ident.strip().translate(_DIGIT_TRANS)
        if ident.isdigit():
            number = int(ident)
        else:
            number = ORDINAL_WORDS.get(ident)
        if title:
            title = title.strip()
    else:
        stripped = text.strip().lstrip("#")
        title = stripped or None

    requires = bool(item and item.get("requires_lecture"))
    if requires and not number:
        return SessionInfo(number=None, title=title, entity_label=entity_label), ParseError("E-NO-SESSION")

    return SessionInfo(number=number, title=title, entity_label=entity_label), None


__all__ = ["parse_session", "SessionInfo", "ParseError"]
