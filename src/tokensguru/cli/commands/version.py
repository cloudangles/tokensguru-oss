"""`tokensguru version`: show the version and the runtime it is running on."""

import platform
import sys

from tokensguru import __version__


def run() -> int:
    print(f"tokensguru {__version__}")
    print(
        f"Python {sys.version.split()[0]} on {platform.system()} {platform.machine()}"
    )
    return 0
