from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Key used to store the navigation stack in ``context.user_data``
NAV_STACK_KEY = "nav_stack"

@dataclass
class Node:
    """Represents a single entry on the navigation stack."""

    kind: str
    ident: Optional[Any]
    title: str = ""


class NavStack:
    """Simple navigation stack backed by ``context.user_data``.

    The stack is stored under :data:`NAV_STACK_KEY` in ``user_data`` and uses
    :class:`Node` instances to ease serialization.
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

    def clear(self) -> None:
        """Remove all nodes from the stack."""
        self._stack.clear()

    # ------------------------------------------------------------------
    def path_text(self) -> str:
        """Return a textual representation of the current path."""
        return " / ".join(node.title for node in self._stack if node.title)

    # ------------------------------------------------------------------
    def state(self) -> List[Node]:
        """Return a copy of the current navigation stack."""
        return list(self._stack)
