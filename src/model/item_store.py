"""Qt-free list of items with an undo history (replaces ItemList<T>).

Every mutation saves and then notifies listeners, so the UI never has to
guess at state. Fixes Java bug #3: the Undo button's visibility is read from
``has_history`` after every change instead of being inferred from a return
value (the To-Do tab compared it against 1, the others against 0).
"""
from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar("T")
Listener = Callable[[], None]


class ItemStore(Generic[T]):
    def __init__(self, active: list[T] | None = None, history: list[T] | None = None,
                 save: Callable[["ItemStore[T]"], None] | None = None) -> None:
        self.active: list[T] = list(active or [])
        self.history: list[T] = list(history or [])
        self._save = save
        self._listeners: list[Listener] = []

    # ------------------------------------------------------------------ queries
    @property
    def has_history(self) -> bool:
        return bool(self.history)

    def __len__(self) -> int:
        return len(self.active)

    def __getitem__(self, row: int) -> T:
        return self.active[row]

    # ---------------------------------------------------------------- mutations
    def add(self, item: T) -> None:
        self.active.append(item)
        self._changed()

    def replace(self, row: int, item: T) -> None:
        self.active[row] = item
        self._changed()

    def touch(self) -> None:
        """Call after mutating an item in place (e.g. toggling a to-do's done flag)."""
        self._changed()

    def move_to_history(self, row: int) -> T:
        item = self.active.pop(row)
        self.history.append(item)
        self._changed()
        return item

    def remove_where(self, predicate: Callable[[T], bool]) -> int:
        """Move every matching item to history (used by 'Delete Checked'). Returns count."""
        keep, gone = [], []
        for item in self.active:
            (gone if predicate(item) else keep).append(item)
        if gone:
            self.active = keep
            self.history.extend(gone)
            self._changed()
        return len(gone)

    def restore_last(self) -> T | None:
        """Undo the most recent delete; the item goes back to the end of the list."""
        if not self.history:
            return None
        item = self.history.pop()
        self.active.append(item)
        self._changed()
        return item

    def move(self, src: int, dest: int) -> None:
        """Move the row at ``src`` so it ends up at index ``dest`` (Qt-style insert, not swap)."""
        if src == dest:
            return
        item = self.active.pop(src)
        self.active.insert(dest, item)
        self._changed()

    # ---------------------------------------------------------------- listeners
    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _changed(self) -> None:
        if self._save:
            self._save(self)
        for listener in self._listeners:
            listener()
