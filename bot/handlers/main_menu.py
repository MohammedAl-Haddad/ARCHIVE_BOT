from telegram import Update
from telegram.ext import ContextTypes

from .navigation_tree import navtree_start
from .admins import admins_start


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle presses on the main inline menu."""
    query = update.callback_query
    if not query:
        return
    data = query.data
    await query.answer()

    if data == "menu:levels":
        await navtree_start(update, context)
    elif data == "menu:plan":
        await query.edit_message_text("الخطة الدراسية غير متاحة بعد.")
    elif data == "menu:programs":
        await query.edit_message_text("البرامج الهندسية غير متاحة بعد.")
    elif data == "menu:search":
        await query.edit_message_text("ميزة البحث قيد التطوير.")
    elif data == "menu:channels":
        await query.edit_message_text("القنوات والمجموعات ستتوفر قريبًا.")
    elif data == "menu:help":
        await query.edit_message_text("للمساعدة يمكنك الرجوع إلى التوثيق أو التواصل مع الدعم.")
    elif data == "menu:contact":
        await query.edit_message_text("للتواصل معنا راسل @mechatronics_support.")
    elif data == "menu:admins":
        await admins_start(update, context)

