from __future__ import annotations

import re

_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e]")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_YEAR_RE = re.compile(r"(?:^|\D)((?:13|14|15)\d{2})(?:هـ|ه)?(?:\D|$)")

def extract_hijri_year(text: str | None) -> int | None:
    """Return the Hijri year found in *text* or ``None`` if absent.

    The parser normalises Arabic digits and ignores direction markers.
    Only years in the range 1300–1600 are considered valid.
    """
    if not text:
        return None
    cleaned = _BIDI_RE.sub("", text).translate(_ARABIC_DIGITS)
    m = _YEAR_RE.search(cleaned)
    if m:
        year = int(m.group(1))
        if 1300 <= year <= 1600:
            return year
    return None

__all__ = ["extract_hijri_year"]
