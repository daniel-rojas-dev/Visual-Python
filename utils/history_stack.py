"""
history_stack.py — Undo / Redo support.
Stores lightweight JSON snapshots of the project state (max 10).
"""
import copy


class HistoryStack:
    """
    Manages undo/redo via a list of state snapshots.
    Each snapshot is a deep-copied dict of the entire project state.
    Limited to `max_size` entries to keep RAM usage minimal.
    """

    def __init__(self, max_size: int = 10):
        self._stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._max_size = max_size

    def push(self, state: dict) -> None:
        """Save a snapshot. Clears the redo stack (new branch)."""
        snapshot = copy.deepcopy(state)
        self._stack.append(snapshot)
        if len(self._stack) > self._max_size:
            self._stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> dict | None:
        """Pop the last state and push it to redo. Returns the previous state."""
        if len(self._stack) < 2:
            return None
        current = self._stack.pop()
        self._redo_stack.append(current)
        return copy.deepcopy(self._stack[-1])

    def redo(self) -> dict | None:
        """Restore the last undone state."""
        if not self._redo_stack:
            return None
        state = self._redo_stack.pop()
        self._stack.append(state)
        return copy.deepcopy(state)

    def can_undo(self) -> bool:
        return len(self._stack) >= 2

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        self._stack.clear()
        self._redo_stack.clear()
