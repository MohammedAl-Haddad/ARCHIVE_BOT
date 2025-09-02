import asyncio
from importlib import import_module
import os

os.environ.setdefault("BOT_TOKEN", "1")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")


def test_material_tags_hidden_in_term(monkeypatch):
    async def _inner():
        tree_module = import_module("bot.navigation.tree")
        excluded = [
            "glossary",
            "practical",
            "references",
            "skills",
            "open_source_projects",
            "syllabus",
            "study_plan",
        ]

        async def fake_list_term_resource_kinds(level_id, term_id):
            return excluded + ["attendance"]

        async def fake_has_materials_by_category(subject_id, section, cat):
            return cat in excluded

        monkeypatch.setattr(tree_module, "list_term_resource_kinds", fake_list_term_resource_kinds)
        monkeypatch.setattr(tree_module, "has_materials_by_category", fake_has_materials_by_category)
        tree_module.invalidate()

        term_items = await tree_module.get_term_menu_items(1, 2)
        term_ids = [k for k, _ in term_items]
        assert "subjects" in term_ids and "attendance" in term_ids
        for k in excluded:
            assert k not in term_ids

        section_items = await tree_module.get_section_menu_items(1, "theory")
        section_ids = [k for k, _ in section_items]
        for k in excluded:
            assert k in section_ids

    asyncio.run(_inner())
