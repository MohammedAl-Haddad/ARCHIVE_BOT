from __future__ import annotations

from typing import Dict, List, Tuple, Optional

# Key used to store the navigation stack in ``context.user_data``
NAV_STACK_KEY = "nav_stack"

# Node representation: (kind, id, title)
Node = Tuple[str, Optional[int | str], str]


class NavStack:
    """Simple navigation stack backed by ``context.user_data``.

    The stack is stored under :data:`NAV_STACK_KEY` in ``user_data`` and uses a
    list of tuples ``(kind, id, title)`` to ease serialization.
    """

    def __init__(self, user_data: Dict) -> None:
        stack = user_data.get(NAV_STACK_KEY)
        if not isinstance(stack, list):
            stack = []
            user_data[NAV_STACK_KEY] = stack
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

    # ------------------------------------------------------------------
    def path_text(self) -> str:
        """Return a textual representation of the current path."""
        return " / ".join(title for _, _, title in self._stack if title)
