"""Builders for the main menu keyboard.

This module previously returned a ``ReplyKeyboardMarkup`` but it now
provides an inline keyboard with callback data for every button. Each
button uses a ``menu:`` prefix so the callback handler can route the
queries appropriately.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Return the main menu inline keyboard.

    Parameters
    ----------
    is_admin:
        Whether to include admin-specific options.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📚 المستويات", callback_data="menu:levels"
            ),
            InlineKeyboardButton(
                "🗂 الخطة الدراسية", callback_data="menu:plan"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔧 البرامج الهندسية", callback_data="menu:programs"
            ),
            InlineKeyboardButton(" بحث", callback_data="menu:search"),
        ],
        [
            InlineKeyboardButton(
                "📡 القنوات والمجموعات", callback_data="menu:channels"
            ),
            InlineKeyboardButton("🆘 مساعدة", callback_data="menu:help"),
        ],
        [InlineKeyboardButton("📨 تواصل معنا", callback_data="menu:contact")],
    ]
    if is_admin:
        keyboard.append(
            [InlineKeyboardButton("👤 إدارة المشرفين", callback_data="menu:admins")]
        )
    return InlineKeyboardMarkup(keyboard)
