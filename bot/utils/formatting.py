import re

ARABIC_ORDINALS = {
    1: "الأولى",
    2: "الثانية",
    3: "الثالثة",
    4: "الرابعة",
    5: "الخامسة",
    6: "السادسة",
    7: "السابعة",
    8: "الثامنة",
    9: "التاسعة",
    10: "العاشرة",
}


def arabic_ordinal(n: int) -> str:
    """Return Arabic ordinal word for *n* if known."""
    return ARABIC_ORDINALS.get(n, str(n))


def to_display_name(value: str) -> str:
    """Normalize *value* by removing direction markers and underscores."""
    if not value:
        return ""
    cleaned = re.sub(r"[‎‏]", "", value)
    return cleaned.replace("_", " ").strip()


_TITLE_PREFIXES = (
    "الدكتور",
    "دكتور",
    "الدكتورة",
    "دكتورة",
    "أ.د",
    "الأستاذ",
    "الأستاذة",
    "المهندس",
    "المهندسة",
    "م.",
    "م ",
)
_TITLE_RE = re.compile(rf"^({'|'.join(re.escape(p) for p in _TITLE_PREFIXES)})\b")


def add_lecturer_title(name: str, title: str = "الدكتور") -> str:
    """Prefix *name* with *title* unless it already has one."""
    if not name:
        return ""
    cleaned = to_display_name(name)
    if _TITLE_RE.match(cleaned):
        return cleaned
    return f"{title} {cleaned}"


__all__ = ["arabic_ordinal", "to_display_name", "add_lecturer_title"]
