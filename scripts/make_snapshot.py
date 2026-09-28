"""Rebuild the bundled offline snapshot (src/exostab/data/snapshot/) from the live archive.

    python scripts/make_snapshot.py

Downloads every multi-planet row of pscomppars, keeps all planets of the systems listed below, and records
the download time. The systems cover the validation targets and the edge cases the completion rules handle
(minimum masses, companion stars, a circumbinary system, a directly imaged system, resonant chains).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from exostab.data.archive import MULTI_PLANET_WHERE, TABLE, TAP_SERVICE, fetch_rows, group_by_host, write_csv

SYSTEMS = [
    "TRAPPIST-1",
    "HD 127195",
    "GJ 876",
    "Kepler-11",
    "HD 10180",
    "55 Cnc",
    "Kepler-36",
    "Kepler-223",
    "TOI-178",
    "HR 8799",
    "K2-138",
    "Kepler-80",
    "HD 219134",
    "GJ 667 C",
    "ups And",
    "HD 82943",
    "Kepler-9",
    "WASP-47",
    "Kepler-51",
    "TOI-270",
    "L 98-59",
    "Kepler-47",
]
OUT = Path(__file__).resolve().parents[1] / "src" / "exostab" / "data" / "snapshot"


def main() -> None:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    hosts = group_by_host(fetch_rows(MULTI_PLANET_WHERE))
    missing = [s for s in SYSTEMS if s not in hosts]
    if missing:
        raise SystemExit(f"not in the archive table: {missing}")
    rows = [r for s in SYSTEMS for r in hosts[s]]
    write_csv(rows, OUT / "pscomppars_snapshot.csv")
    meta = {
        "retrieved_utc": stamp,
        "table": TABLE,
        "service": TAP_SERVICE,
        "where": MULTI_PLANET_WHERE,
        "systems": SYSTEMS,
        "n_systems": len(SYSTEMS),
        "n_rows": len(rows),
        "note": "Subset of the pscomppars table (all planets of each listed host) for offline tests and demos. "
        "Regenerate with scripts/make_snapshot.py.",
    }
    (OUT / "snapshot.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows for {len(SYSTEMS)} systems, retrieved {stamp}")


if __name__ == "__main__":
    main()
