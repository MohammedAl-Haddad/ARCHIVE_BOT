import aiosqlite
from typing import Any

from .base import DB_PATH


async def can_view(user_id: int | None, kind: str, id: Any) -> bool:
    """Return True if ``user_id`` may view the item ``kind``/``id``.

    The check is performed against the ``admins`` table using the
    ``tg_user_id`` index.  Currently this function simply verifies that the
    user exists and is active in the table; callers should handle any further
    permission logic.
    """

    if user_id is None:
        return True

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM admins WHERE tg_user_id=? AND is_active=1",
            (user_id,),
        )
        return await cur.fetchone() is not None


__all__ = ["can_view"]
