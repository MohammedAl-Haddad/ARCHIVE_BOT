import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# ensure required environment variables for importing bot modules
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("ARCHIVE_CHANNEL_ID", "1")
os.environ.setdefault("OWNER_TG_ID", "1")

from bot.navigation import NavigationState
from bot.handlers.navigation import render_state, echo_handler


class DummyMessage:
    def __init__(self):
        self.sent = []

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


def test_subject_with_single_section_skips_selection_and_on_back():
    user_data = {
        "nav": {
            "stack": [("level", "L"), ("term", "T"), ("subject_list", ""), ("subject", "S")],
            "data": {"level_id": 1, "term_id": 1, "subject_id": 10},
        }
    }
    context = SimpleNamespace(user_data=user_data)
    update = SimpleNamespace(
        message=DummyMessage(), effective_chat=SimpleNamespace(type="private")
    )

    async def run():
        with patch(
            "bot.handlers.navigation.get_available_sections_for_subject",
            AsyncMock(return_value=["theory"]),
        ), patch(
            "bot.handlers.navigation.get_years_for_subject_section",
            AsyncMock(return_value=[(1, "2023")]),
        ), patch(
            "bot.handlers.navigation.get_lecturers_for_subject_section",
            AsyncMock(return_value=[(1, "Dr A")]),
        ), patch(
            "bot.handlers.navigation.has_lecture_category",
            AsyncMock(return_value=True),
        ), patch(
            "bot.handlers.navigation.generate_section_filters_keyboard_dynamic",
            return_value="keyboard",
        ) as gen_filters, patch(
            "bot.handlers.navigation.generate_subject_sections_keyboard_dynamic"
        ) as gen_sections, patch(
            "bot.handlers.navigation.get_subjects_by_level_and_term",
            AsyncMock(return_value=[("S",)]),
        ), patch(
            "bot.handlers.navigation.generate_subjects_keyboard",
            return_value="subjects_keyboard",
        ):
            # first render: should skip section selection
            await render_state(update, context)
            assert update.message.sent[-1] == ("اختر طريقة التصفية:", "keyboard")
            gen_sections.assert_not_called()
            nav = NavigationState(context.user_data)
            assert nav.data["section"] == "theory"
            assert nav.stack[-1][0] == "section"
            gen_filters.assert_called_with(True, True, True)

            # simulate user pressing back
            update.message.text = "🔙 العودة"
            await echo_handler(update, context)
            assert update.message.sent[-1] == ("اختر المادة:", "subjects_keyboard")
            nav = NavigationState(context.user_data)
            assert nav.stack[-1][0] == "subject_list"
            assert "section" not in nav.data
            assert "subject_id" not in nav.data
            gen_sections.assert_not_called()

    asyncio.run(run())
