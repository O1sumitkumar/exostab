"""Where archive rows come from: the live archive, the on-disk cache, or the bundled offline snapshot.

Order of preference for ``load_rows()``:

1. ``offline=True`` (or the environment variable ``EXOSTAB_OFFLINE=1``): the bundled snapshot only.
2. ``refresh=True``: query the archive now and overwrite the cache (fails loudly if the archive cannot
   be reached, because the user explicitly asked for fresh data).
3. Otherwise: the cache if it exists; if not, query the archive and fill the cache; if the archive
   cannot be reached, fall back to the snapshot with a warning that is carried into the report.

The cache lives in the platform's user cache directory (``platformdirs``), or in ``EXOSTAB_CACHE_DIR``
if that is set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import platformdirs

from .. import __version__
from ..models import SourceKind
from .archive import (
    MULTI_PLANET_WHERE,
    TABLE,
    TAP_SERVICE,
    ArchiveError,
    Row,
    fetch_rows,
    read_csv,
    write_csv,
)

CACHE_TABLE = "pscomppars_multi.csv"
CACHE_META = "pscomppars_multi.json"
SNAPSHOT_TABLE = "pscomppars_snapshot.csv"
SNAPSHOT_META = "snapshot.json"


@dataclass(frozen=True)
class TableInfo:
    kind: SourceKind  # "archive", "archive-cache" or "snapshot"
    retrieved_utc: str | None
    path: str | None
    note: str | None = None


def cache_dir() -> Path:
    env = os.environ.get("EXOSTAB_CACHE_DIR")
    return Path(env) if env else platformdirs.user_cache_path("exostab")


def offline_requested() -> bool:
    return os.environ.get("EXOSTAB_OFFLINE", "").strip().lower() in ("1", "true", "yes")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_snapshot() -> tuple[list[Row], TableInfo]:
    pkg = resources.files("exostab.data.snapshot")
    rows = read_csv(pkg.joinpath(SNAPSHOT_TABLE).read_text(encoding="utf-8"))
    meta = json.loads(pkg.joinpath(SNAPSHOT_META).read_text(encoding="utf-8"))
    return rows, TableInfo(
        kind="snapshot",
        retrieved_utc=meta.get("retrieved_utc"),
        path=f"exostab/data/snapshot/{SNAPSHOT_TABLE}",
        note=f"offline snapshot of {meta.get('n_systems')} systems",
    )


def load_cache() -> tuple[list[Row], TableInfo] | None:
    d = cache_dir()
    table, meta = d / CACHE_TABLE, d / CACHE_META
    if not (table.exists() and meta.exists()):
        return None
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
        rows = read_csv(table)
    except (OSError, ValueError, ArchiveError):
        return None  # a damaged cache is ignored and rebuilt
    return rows, TableInfo(kind="archive-cache", retrieved_utc=info.get("retrieved_utc"), path=str(table))


def refresh_cache() -> tuple[list[Row], TableInfo]:
    rows = fetch_rows(MULTI_PLANET_WHERE)
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    stamp = _now()
    write_csv(rows, d / CACHE_TABLE)
    meta = {
        "retrieved_utc": stamp,
        "table": TABLE,
        "service": TAP_SERVICE,
        "where": MULTI_PLANET_WHERE,
        "n_rows": len(rows),
        "exostab_version": __version__,
    }
    (d / CACHE_META).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return rows, TableInfo(kind="archive", retrieved_utc=stamp, path=str(d / CACHE_TABLE))


def load_rows(*, refresh: bool = False, offline: bool = False) -> tuple[list[Row], TableInfo]:
    """Archive rows for all multi-planet systems, and where they came from."""
    if offline or offline_requested():
        return load_snapshot()
    if refresh:
        return refresh_cache()
    cached = load_cache()
    if cached is not None:
        return cached
    try:
        return refresh_cache()
    except ArchiveError as exc:
        rows, info = load_snapshot()
        note = f"archive unreachable ({exc}); using the offline snapshot instead"
        return rows, TableInfo(kind=info.kind, retrieved_utc=info.retrieved_utc, path=info.path, note=note)
