"""Database repository layer.

This package contains thin wrappers around the raw SQL queries used
in the bot.  Handlers interact with the database exclusively through
these functions which keeps the higher level logic independent from
the underlying storage implementation.
"""

__all__ = [
    "taxonomy",
    "hashtags",
    "materials",
    "linking",
    "rbac",
]
