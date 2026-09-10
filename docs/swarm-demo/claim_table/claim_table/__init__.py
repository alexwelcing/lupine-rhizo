"""claim_table — render the TMS 2027 proceedings canonical results object as markdown.

Canonical object: schema ``lupine.tms2027.proceedings.results.v1``, written by
``lupine-rhizo/paper/tms2027-proceedings/build_artifacts.py``.
"""

from .core import (
    ClaimTableError,
    HeadlineRow,
    MissingKeyError,
    SCHEMA,
    build_rows,
    load_results,
    render_markdown,
)

__all__ = [
    "SCHEMA",
    "ClaimTableError",
    "MissingKeyError",
    "HeadlineRow",
    "load_results",
    "build_rows",
    "render_markdown",
]
