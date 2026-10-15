"""Per-run memoization for tool functions explicitly declared read-only."""

from collections import OrderedDict
from copy import deepcopy
import json
import threading
from typing import Any, Callable, Iterable


class ReadOnlyToolCache:
    """Cache repeat calls to explicitly allow-listed, deterministic read-only tools.

    Create one cache per agent run and call ``cache.call(name, arguments, fn)``
    where ``fn`` executes the tool. Calls outside ``read_only_tools`` always run.
    Exceptions and values that cannot be copied are never cached.
    """

    def __init__(self, read_only_tools: Iterable[str], max_entries: int = 128):
        self._read_only_tools = frozenset(read_only_tools)
        self._max_entries = max(1, int(max_entries))
        self._values: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self.cache_hits = 0

    def call(self, name: str, arguments: Any, fn: Callable[[], Any]) -> Any:
        """Return a cached value for an identical read-only call, or execute ``fn``."""
        if name not in self._read_only_tools:
            return fn()

        try:
            key = json.dumps([name, arguments], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            return fn()

        with self._lock:
            if key in self._values:
                self._values.move_to_end(key)
                self.cache_hits += 1
                try:
                    return deepcopy(self._values[key])
                except Exception:
                    del self._values[key]

        result = fn()
        try:
            cached = deepcopy(result)
        except Exception:
            return result

        with self._lock:
            self._values[key] = cached
            self._values.move_to_end(key)
            while len(self._values) > self._max_entries:
                self._values.popitem(last=False)
        return result

    def clear(self) -> None:
        """Discard cached results between agent runs or after relevant state changes."""
        with self._lock:
            self._values.clear()
            self.cache_hits = 0
