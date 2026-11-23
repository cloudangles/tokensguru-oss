"""Keeps track of the text ranges already claimed, so no two findings overlap."""

from __future__ import annotations

from bisect import bisect_left


class SpanSet:
    def __init__(self) -> None:
        self._starts: list[int] = []
        self._ends: list[int] = []

    def add(self, start: int, end: int) -> bool:
        index = bisect_left(self._starts, start)
        if index > 0 and self._ends[index - 1] > start:
            return False
        if index < len(self._starts) and self._starts[index] < end:
            return False
        self._starts.insert(index, start)
        self._ends.insert(index, end)
        return True
