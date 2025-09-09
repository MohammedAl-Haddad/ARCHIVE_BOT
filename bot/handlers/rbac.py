"""Command handlers for RBAC management.

These handlers provide very small wrappers around repository functions to
manage roles and broadcast messages.  They are intentionally simple to keep the
focus on repository behaviour, which is where most logic resides."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.repo import rbac


async def create_role_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /role_create <name> [tag1,tag2]")
        return
    name = context.args[0]
    tags = context.args[1].split(",") if len(context.args) > 1 else []
    role = await rbac.create_role(name, tags)
    await update.effective_message.reply_text(f"Created role {role['id']}")


async def assign_role_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /role_assign <user_id> <role_id>")
        return
    user_id, role_id = map(int, context.args[:2])
    await rbac.assign_role(user_id, role_id)
    await update.effective_message.reply_text("Role assigned")


async def revoke_role_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /role_revoke <user_id> <role_id>")
        return
    user_id, role_id = map(int, context.args[:2])
    await rbac.revoke_role(user_id, role_id)
    await update.effective_message.reply_text("Role revoked")


async def set_perm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Usage: /role_perm <role_id> <permission_key> [scope_json]"
        )
        return
    role_id = int(context.args[0])
    permission_key = context.args[1]
    scope = None
    if len(context.args) > 2:
        try:
            import json

            scope = json.loads(" ".join(context.args[2:]))
        except Exception:
            await update.effective_message.reply_text("Invalid JSON scope")
            return
    await rbac.set_permission(role_id, permission_key, scope)
    await update.effective_message.reply_text("Permission set")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Usage: /role_broadcast <tag> <message>"
        )
        return
    tag = context.args[0]
    message = " ".join(context.args[1:])

    async def _send(uid: int, text: str) -> None:
        await context.bot.send_message(uid, text)

    count = await rbac.broadcast(tag, message, _send)
    await update.effective_message.reply_text(f"Broadcast sent to {count} users")


rbac_handlers = [
    CommandHandler("role_create", create_role_cmd),
    CommandHandler("role_assign", assign_role_cmd),
    CommandHandler("role_revoke", revoke_role_cmd),
    CommandHandler("role_perm", set_perm_cmd),
    CommandHandler("role_broadcast", broadcast_cmd),
]


__all__ = ["rbac_handlers"]
