from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

async def setup_wizard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🛠️ أوامر الإعداد التفاعلي غير متوفرة بعد.\n"
        "سيتم تطوير واجهة المعالج لاحقًا."
    )

async def add_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ لم يتم تنفيذ إضافة قسم بعد.")

async def add_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ لم يتم تنفيذ إضافة بطاقة بعد.")

async def add_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ لم يتم تنفيذ إضافة نوع بعد.")

async def add_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ لم يتم تنفيذ إضافة مرادف بعد.")

async def undo_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ التراجع غير متاح حاليًا.")

async def show_audit_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚠️ سجل التدقيق غير متاح بعد.")
