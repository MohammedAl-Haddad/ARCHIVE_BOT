from __future__ import annotations

from typing import Dict, List, Tuple, Optional

# Key used to store the navigation stack in ``context.user_data``
NAV_STACK_KEY = "nav_stack"

# Key used to track the global bump value that invalidates the stack.
_BUMP_KEY = "nav_stack_bump"

# Node representation: (kind, id, title)
Node = Tuple[str, Optional[int | str | tuple[int, int]], str]


class NavStack:
    """Simple navigation stack backed by ``context.user_data``.

    Parameters
    ----------
    user_data:
        The ``context.user_data`` mapping in which the stack is stored.
    bump:
        Optional global bump value.  When supplied and different from the
        previously stored value the stack is cleared.  This allows external
        configuration changes to immediately invalidate the user's navigation
        path.

    The stack itself is stored under :data:`NAV_STACK_KEY` in ``user_data`` and
    uses a list of tuples ``(kind, id, title)`` to ease serialization.
    """

    def __init__(self, user_data: Dict, *, bump: Optional[int] = None) -> None:
        stack = user_data.get(NAV_STACK_KEY)
        if not isinstance(stack, list):
            stack = []
            user_data[NAV_STACK_KEY] = stack

        # If a bump value is provided and differs from what we have stored,
        # reset the stack so that navigation reflects the latest configuration.
        if bump is not None:
            stored = user_data.get(_BUMP_KEY)
            if stored != bump:
                stack.clear()
                user_data[_BUMP_KEY] = bump

        self._user_data = user_data
        self._stack: List[Node] = stack

    # ------------------------------------------------------------------
    # Basic stack operations
    def push(self, node: Node) -> None:
        """Push ``node`` onto the stack."""
        self._stack.append(node)

    def pop(self) -> Optional[Node]:
        """Pop and return the top node if present."""
        if self._stack:
            return self._stack.pop()
        return None

    def peek(self) -> Optional[Node]:
        """Return the top node without removing it."""
        if self._stack:
            return self._stack[-1]
        return None

    def clear(self) -> None:
        """Remove all nodes from the stack."""
        self._stack.clear()

    # ------------------------------------------------------------------
    def path_text(self) -> str:
        """Return a textual representation of the current path."""
        return " / ".join(title for _, _, title in self._stack if title)
