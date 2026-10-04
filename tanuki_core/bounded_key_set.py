from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator


class BoundedKeySet:
    """Insertion-ordered membership set with deterministic oldest eviction."""

    def __init__(self, values: Iterable[str] = (), *, max_entries: int = 4096):
        self.max_entries = max(1, int(max_entries))
        self._keys: set[str] = set()
        self._order: deque[str] = deque()
        self.update(values)

    def __contains__(self, key: object) -> bool:
        return key in self._keys

    def __iter__(self) -> Iterator[str]:
        return iter(self._order)

    def __len__(self) -> int:
        return len(self._keys)

    def __repr__(self) -> str:
        return repr(self._keys)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BoundedKeySet):
            return self._keys == other._keys
        try:
            return self._keys == set(other)  # type: ignore[arg-type]
        except TypeError:
            return False

    def add(self, key: str) -> None:
        if key in self._keys:
            return
        self._keys.add(key)
        self._order.append(key)
        while len(self._order) > self.max_entries:
            self._keys.discard(self._order.popleft())

    def update(self, values: Iterable[str]) -> None:
        for value in values:
            self.add(value)

    def clear(self) -> None:
        self._keys.clear()
        self._order.clear()
