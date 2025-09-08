"""Database repository layer.

This package contains thin wrappers around the raw SQL queries used in the
bot. Handlers interact with the database exclusively through these functions
which keeps the higher level logic independent from the underlying storage
implementation.

It also exposes a :func:`connect` helper and a small set of exceptions that
provide a unified error handling surface for all repository modules.
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncIterator, Awaitable, Callable, ParamSpec, TypeVar

import aiosqlite

from bot.db import base


class RepoError(Exception):
    """Base error for repository operations."""


class RepoNotFound(RepoError):
    """Raised when a requested record is missing."""


class RepoConflict(RepoError):
    """Raised when an operation encounters a conflict."""


class RepoConstraintError(RepoError):
    """Raised when database constraints are violated."""


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    """Create a new DB connection with foreign keys enabled.

    ينشئ اتصالاً جديداً بقاعدة البيانات مع تفعيل قيود العلاقات.
    """

    async with aiosqlite.connect(base.DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


P = ParamSpec("P")
T = TypeVar("T")


def translate_errors(
    func: Callable[P, Awaitable[T]]
) -> Callable[P, Awaitable[T]]:
    """Translate low-level DB errors to repository exceptions.

    غلاف لترجمة أخطاء قاعدة البيانات إلى استثناءات المخرن.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except sqlite3.IntegrityError as exc:  # pragma: no cover - exercised via wrapper
            raise RepoConstraintError(str(exc)) from exc
        except aiosqlite.Error as exc:  # pragma: no cover
            raise RepoError(str(exc)) from exc

    return wrapper


__all__ = [
    "taxonomy",
    "hashtags",
    "materials",
    "linking",
    "rbac",
    "connect",
    "translate_errors",
    "RepoError",
    "RepoNotFound",
    "RepoConflict",
    "RepoConstraintError",
]

