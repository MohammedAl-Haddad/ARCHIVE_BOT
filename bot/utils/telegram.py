import asyncio
import logging
from telegram import Message
from telegram.error import TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def build_archive_link(archive_chat_id: int, message_id: int, username: str | None = None) -> str | None:
    """Return a link to a message in the archive channel.

    If a public ``username`` is provided, build a public t.me link.
    Otherwise, fall back to the private ``t.me/c`` format using the
    internal channel ID. If ``archive_chat_id`` is falsy, ``None`` is
    returned.
    """
    if not archive_chat_id or not message_id:
        return None
    if username:
        return f"https://t.me/{username}/{message_id}"
    internal_id = str(archive_chat_id).replace("-100", "", 1)
    return f"https://t.me/c/{internal_id}/{message_id}"


def get_file_unique_id_from_message(msg: Message | None) -> str | None:
    """Extract ``file_unique_id`` from *msg* if present.

    The helper gracefully handles ``None`` and different media types supported by
    Telegram. ``None`` is returned when no file-based media is found.
    """
    if not msg:
        return None
    if msg.document:
        return msg.document.file_unique_id
    if msg.photo:
        return msg.photo[-1].file_unique_id
    if msg.video:
        return msg.video.file_unique_id
    if msg.audio:
        return msg.audio.file_unique_id
    if msg.voice:
        return msg.voice.file_unique_id
    if msg.animation:
        return msg.animation.file_unique_id
    return None


async def send_ephemeral(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    seconds: int = 10,
    reply_to_message_id: int | None = None,
):
    """Send a message that auto-deletes after ``seconds`` seconds.

    The bot must possess the ``Delete messages`` right in group chats.
    """
    msg = await context.bot.send_message(
        chat_id, text, reply_to_message_id=reply_to_message_id
    )

    async def delete_later() -> None:
        await asyncio.sleep(seconds)
        try:
            await context.bot.delete_message(chat_id, msg.message_id)
        except TelegramError as e:  # pragma: no cover
            logger.debug("delete failed: %s", e)

    if msg.chat.type in ("group", "supergroup"):
        try:
            member = await context.bot.get_chat_member(chat_id, context.bot.id)
        except TelegramError as e:  # pragma: no cover
            logger.debug("member check failed: %s", e)
            return msg
        if not getattr(member, "can_delete_messages", False) and getattr(
            member, "status", ""
        ) != "creator":
            logger.debug(
                "missing Delete messages permission in chat %s", chat_id
            )
            return msg

    context.application.create_task(delete_later())
    return msg


__all__ = [
    "build_archive_link",
    "send_ephemeral",
    "get_file_unique_id_from_message",
]
