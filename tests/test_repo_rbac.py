import asyncio

from bot.repo import rbac


def test_rbac(repo_db):
    aid = asyncio.run(rbac.create_admin(1, "Admin", "owner", 0b11))
    row = asyncio.run(rbac.get_admin_by_user_id(1))
    assert row[0] == aid
    assert asyncio.run(rbac.has_permissions(1, 0b01)) is True
    asyncio.run(rbac.update_permissions(1, 0b10))
    assert asyncio.run(rbac.has_permissions(1, 0b01)) is False
    asyncio.run(rbac.set_admin_active(1, False))
    assert asyncio.run(rbac.has_permissions(1, 0b10)) is False
