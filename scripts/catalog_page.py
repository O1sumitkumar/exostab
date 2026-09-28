"""Write docs/catalog.md, a sortable table of the stability catalog.

    python scripts/catalog_page.py catalog/            # folder with catalog.csv and catalog_meta.json

The documentation workflow runs this after fetching the latest catalog from the branch "catalog-data".
Without a catalog folder it writes a placeholder page. Sorting and filtering are done by
docs/javascripts/catalog.js in the browser; the table itself is plain HTML, so it can also be read without
JavaScript.
"""

from __future__ import annotations

import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "catalog.md"
BRANCH = "https://github.com/mimitoz62/exostab/tree/catalog-data"

HEADER = """# Stability catalog

exostab's three indicators for every multi-planet system in the NASA Exoplanet Archive's Planetary Systems
Composite Parameters table, recomputed every week by the
[catalog workflow](https://github.com/mimitoz62/exostab/blob/main/.github/workflows/catalog.yml).


!!! warning "Read the verdicts with their caveats"
    Every system is checked with the same default settings. Missing orbital phases are drawn at random,
    minimum masses are used as masses, and orbits are coplanar. A resonant system can therefore look unstable
    here, although the full solution of one paper shows it is stable (GJ 876 is the standard example). Run
    `exostab check "<name>"` to see every assumption, or `--from-file` with a published solution.
"""

DOWNLOAD = """**Download:** [`catalog.csv`](data/catalog.csv), [`catalog.parquet`](data/catalog.parquet) and
[`catalog_meta.json`](data/catalog_meta.json) (settings and archive download date). Every weekly version is
kept on the [`catalog-data` branch]({branch}). Column definitions are at the end of this page.
"""

COLUMNS = [
    ("system", "System"),
    ("n_planets", "Planets"),
    ("overall", "Overall"),
    ("hill", "Hill"),
    ("amd", "AMD"),
    ("nbody", "N-body"),
    ("hill_min_separation", "Min. spacing (R_H)"),
    ("amd_beta_max", "Max. AMD β"),
    ("megno_nominal", "Nominal ⟨Y⟩"),
    ("draws_summary", "Draws reg/chaos/unst"),
    ("t_end_yr", "Horizon (yr)"),
    ("n_flags", "Flags"),
]
VERDICTS = {"stable", "marginal", "unstable", "inconclusive"}


def _num(value: str, fmt: str) -> str:
    if value in ("", "None", "nan"):
        return "—"
    x = float(value)
    if x == float("inf"):
        return "∞"
    return format(x, fmt)


def _cell(key: str, row: dict[str, str]) -> tuple[str, str]:
    """(display text, sort key)."""
    if key == "draws_summary":
        if row["status"] != "ok":
            return "—", "-1"
        return f"{row['nbody_regular']}/{row['nbody_chaotic']}/{row['nbody_unstable']}", row["nbody_regular"]
    v = row.get(key, "")
    if key in ("overall", "hill", "amd", "nbody"):
        text = v if v in VERDICTS else (row["status"] if key == "overall" else "—")
        return text, text
    if key == "hill_min_separation":
        return _num(v, ".2f"), v or "-1"
    if key == "amd_beta_max":
        return _num(v, ".3g"), "1e308" if v == "inf" else (v or "-1")
    if key == "megno_nominal":
        return _num(v, ".3f"), v or "-1"
    if key == "t_end_yr":
        return _num(v, ",.0f"), v or "-1"
    return v, v


def render(folder: Path | None) -> str:
    if folder is None or not (folder / "catalog.csv").exists():
        return HEADER.format(branch=BRANCH) + "\n*No catalog has been published yet.*\n"
    rows = list(csv.DictReader((folder / "catalog.csv").open(encoding="utf-8")))
    meta = json.loads((folder / "catalog_meta.json").read_text(encoding="utf-8"))
    counts = Counter(r["overall"] if r["status"] == "ok" else r["status"] for r in rows)
    s = meta["settings"]
    parts = [HEADER.format(branch=BRANCH), DOWNLOAD.format(branch=BRANCH)]
    parts.append(
        f"**This version:** {meta['n_systems']} systems, computed {meta['created_utc'][:10]} with exostab "
        f"{meta['exostab_version']} from archive data of {(meta.get('data_retrieved_utc') or '?')[:10]}. "
        f"Settings: {s['orbits']:,.0f} orbits of the innermost planet, {s['draws']} draws, seed {s['seed']}, "
        f"at most {s['max_seconds']:g} s per system.\n"
    )
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    parts.append(f"**Overall verdicts:** {summary}.\n")
    parts.append(
        '<input id="catalog-filter" type="search" placeholder="Filter systems…" aria-label="Filter systems">\n'
    )
    head = "".join(
        f'<th scope="col" data-col="{i}">{html.escape(t)}</th>' for i, (_, t) in enumerate(COLUMNS)
    )
    body = []
    for r in rows:
        cells = []
        for key, _ in COLUMNS:
            text, sort = _cell(key, r)
            cls = (
                f' class="verdict-{text}"'
                if key in ("overall", "hill", "amd", "nbody") and text in VERDICTS
                else ""
            )
            title = f' title="{html.escape(r["reason"])}"' if key == "overall" and r["status"] != "ok" else ""
            cells.append(f'<td data-sort="{html.escape(sort)}"{cls}{title}>{html.escape(text)}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    parts.append(
        '<div class="catalog-wrap"><table id="catalog-table">\n<thead><tr>'
        + head
        + "</tr></thead>\n<tbody>\n"
        + "\n".join(body)
        + "\n</tbody></table></div>\n"
    )
    parts.append(
        """
## Columns

| Column | Meaning |
|---|---|
| Overall, Hill, AMD, N-body | Verdicts: stable, marginal, unstable, inconclusive (see [Methods](methods.md)). "skipped" or "timeout" means no verdict; hover for the reason. |
| Min. spacing | Smallest separation of adjacent planets in mutual Hill radii |
| Max. AMD β | Largest AMD-stability coefficient; below 1 is AMD-stable, ∞ means resonances overlap even for circular orbits |
| Nominal ⟨Y⟩ | MEGNO of the nominal run (runs stopped by a close encounter still show a value) |
| Draws reg/chaos/unst | Monte Carlo draws that were regular / chaotic / had a close encounter or escape |
| Horizon | Length of the N-body runs in years |
| Flags | Number of data-completion rules applied (the CSV lists them) |

The CSV has more columns: archive row names, completion rules, energy errors, versions and run times.
"""
    )
    return "\n".join(parts)


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    OUT.write_text(render(folder), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
