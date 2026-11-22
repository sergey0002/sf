"""Entry point for the arch CLI.

Works both as ``python -m arch`` (from doc/tools/) and as a direct script
``python doc/tools/arch/__main__.py``.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution: make the parent package importable as `arch`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from arch.cli.app import run
else:
    from .cli.app import run

if __name__ == "__main__":
    raise SystemExit(run())