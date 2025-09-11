from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from ..repo import taxonomy, materials
from ..config import PER_PAGE as CONFIG_PER_PAGE

# Expose a default ``PER_PAGE`` similar to other modules.  The value is
# sourced from configuration but can be overridden when calling
# :func:`build_menu`.
PER_PAGE = CONFIG_PER_PAGE

# ``Button`` representation used by :class:`Menu`.  Each entry is a tuple of
# ``(kind, identifier, label)`` mirroring the node structure used by the
# navigation tree.
Button = Tuple[str, str, str]


@dataclass
class Menu:
    """Simple container for navigation buttons.

    Attributes
    ----------
    children:
        Sequence of button tuples ``(kind, identifier, label)`` that can be
        fed directly into the keyboard builders.
    """

    children: List[Button]


async def build_menu(
    subject_id: int,
    *,
    lang: str = "ar",
) -> Menu:
    """Return navigation buttons available for ``subject_id``.

    The function gathers sections, cards and item types from the taxonomy
    repository.  It verifies that content exists for each element using the
    lightweight counting helpers from :mod:`bot.repo.materials` before adding
    a corresponding button.  Buttons are represented as tuples
    ``(kind, identifier, label)``.
    """

    # Bail out quickly if the subject itself has no materials.
    if await materials.count_by_subject(subject_id) == 0:
        return Menu(children=[])

    buttons: List[Button] = []

    # Fetch sections enabled for the subject.
    sections = await taxonomy.get_sections_for_subject(subject_id, lang=lang)
    for section in sections:
        section_id = section["id"]
        if await materials.count_by_section(subject_id, section_id) == 0:
            continue
        buttons.append(("section", str(section_id), section["label"]))

        # Card buttons for this section ("cards" are material categories).
        cards = await taxonomy.get_cards(section_id=section_id, lang=lang)
        if cards:
            mats = await materials.get_materials(subject_id, section_id=section_id)
            for card in cards:
                if card["show_when_empty"] or any(
                    m["category_id"] == card["id"] for m in mats
                ):
                    buttons.append(("card", str(card["id"]), card["label"]))

        # Item type buttons linked to this section.
        item_types = await taxonomy.get_item_types_for_section(
            section_id, lang=lang
        )
        for item_type in item_types:
            if await materials.count_by_item_type(
                subject_id, section_id, item_type["id"]
            ):
                ident = f"{section_id}-{item_type['id']}"
                buttons.append(("item_type", ident, item_type["label"]))

    return Menu(children=buttons)
