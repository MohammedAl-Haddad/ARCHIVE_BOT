import asyncio

from bot.repo import rbac


def test_rbac_basic(repo_db):
    role_id = asyncio.run(rbac.create_role("mod", ["mods"]))
    asyncio.run(rbac.assign_role(1, role_id))
    asyncio.run(rbac.set_permission(role_id, "delete"))
    assert asyncio.run(rbac.has_permission(1, "delete")) is True

    sent: list[tuple[int, str]] = []

    async def _send(uid: int, msg: str) -> None:
        sent.append((uid, msg))

    asyncio.run(rbac.broadcast("mods", "hello", _send))
    assert sent == [(1, "hello")]


def test_rbac_context_scope(repo_db):
    role_id = asyncio.run(rbac.create_role("group_mod"))
    asyncio.run(rbac.assign_role(2, role_id))
    asyncio.run(rbac.set_permission(role_id, "manage_group", {"group_id": 5}))
    assert asyncio.run(rbac.has_permission(2, "manage_group", {"group_id": 5})) is True
    assert asyncio.run(rbac.has_permission(2, "manage_group", {"group_id": 6})) is False
