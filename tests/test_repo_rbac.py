import asyncio
import pytest

from bot.repo import RepoNotFound, rbac


def test_roles_crud(repo_db):
    role = asyncio.run(rbac.create_role("mod", ["mods"]))
    disabled = asyncio.run(rbac.create_role("old", is_enabled=False))

    fetched = asyncio.run(rbac.get_role(role["id"]))
    assert fetched["name"] == "mod"

    with pytest.raises(RepoNotFound):
        asyncio.run(rbac.get_role(disabled["id"]))
    assert len(asyncio.run(rbac.list_roles())) == 1
    assert len(asyncio.run(rbac.list_roles(is_enabled=None))) == 2

    updated = asyncio.run(rbac.update_role(role["id"], name="moderator"))
    assert updated["name"] == "moderator"

    asyncio.run(rbac.delete_role(role["id"]))
    remaining = asyncio.run(rbac.list_roles(is_enabled=None))
    assert [r["id"] for r in remaining] == [disabled["id"]]


def test_user_roles_and_permissions(repo_db):
    role = asyncio.run(rbac.create_role("mod", ["mods"]))
    asyncio.run(rbac.assign_role(1, role["id"]))
    assert [r["id"] for r in asyncio.run(rbac.list_user_roles(1))] == [role["id"]]

    asyncio.run(rbac.set_permission(role["id"], "delete"))
    assert asyncio.run(rbac.has_permission(1, "delete")) is True
    perms = asyncio.run(rbac.list_role_permissions(role["id"]))
    assert perms == [{"role_id": role["id"], "permission_key": "delete", "scope": None}]

    sent: list[tuple[int, str]] = []

    async def _send(uid: int, msg: str) -> None:
        sent.append((uid, msg))

    asyncio.run(rbac.broadcast("mods", "hello", _send))
    assert sent == [(1, "hello")]

    asyncio.run(rbac.delete_permission(role["id"], "delete"))
    assert asyncio.run(rbac.has_permission(1, "delete")) is False

    asyncio.run(rbac.revoke_role(1, role["id"]))
    assert asyncio.run(rbac.list_user_roles(1)) == []

