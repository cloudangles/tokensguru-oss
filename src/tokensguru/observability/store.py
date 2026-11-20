"""Where the observability screens get traces from.

No data source is connected yet, so this returns an empty list and the screens
show "No traces yet.". When the real API exists, change only this module.
"""

from __future__ import annotations

from tokensguru.observability.models import Trace


def list_traces() -> list[Trace]:
    return []
