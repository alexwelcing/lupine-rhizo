"""Test bootstrap for the lupine_distill package tests.

Ensures ``python/`` (the package parent) is importable regardless of the
pytest invocation directory (`cd python && python -m pytest -m unit -q` per
the justfile, or `python -m pytest python/tests` from the repo root).
"""

from __future__ import annotations

import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PYTHON_DIR.parent

for _path in (_REPO_ROOT, _PYTHON_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
