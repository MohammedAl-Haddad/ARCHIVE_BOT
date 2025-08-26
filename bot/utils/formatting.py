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


def format_lecturer_name(name: str, title: str = "الدكتور") -> str:
    """Return *name* prefixed with *title* if not already titled.

    The input is first normalized using :func:`to_display_name`.  If the
    resulting name already starts with a common academic title (e.g. ``"د."``
    or ``"الدكتور"``/``"الدكتورة"``), it is returned unchanged.  Otherwise
    the provided *title* is prepended.
    """

    display = to_display_name(name)
    if not display:
        return ""

    prefixes = ("د.", "دكتور", "الدكتور", "دكتورة", "الدكتورة")
    if any(display.startswith(p) for p in prefixes):
        return display
    return f"{title} {display}"


__all__ = ["arabic_ordinal", "to_display_name", "format_lecturer_name"]
