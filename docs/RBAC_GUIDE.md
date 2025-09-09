# RBAC Guide

The bot uses role‑based access control to manage permissions.

## Concepts
- **Role**: named collection of permissions.
- **Permission**: action that can be granted, e.g. `upload`, `delete`,
  `manage_group`.
- **Scope**: optional context like a specific group or topic.

## Basic operations
```python
import asyncio
from bot.repo import rbac

# create a role and give it a permission
role = asyncio.run(rbac.create_role("mod"))
asyncio.run(rbac.set_permission(role["id"], "upload"))

# assign the role to a user
asyncio.run(rbac.assign_role(1234, role["id"]))

# check a permission
assert asyncio.run(rbac.has_permission(1234, "upload"))
```

Roles can also be tagged for broadcasting:
```python
async def _send(uid: int, msg: str) -> None:
    print(uid, msg)

asyncio.run(rbac.broadcast("mods", "hello", _send))
```
