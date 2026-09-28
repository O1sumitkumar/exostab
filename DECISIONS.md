# Decisions

Each entry records what was decided, why, and when. "Proposed" entries are planned defaults that still
need the reference check (PLAN.md, step 0) or a test before they become final.

## D0 — Environment found (2026-09-28)

- macOS on Apple M4 Pro (14 cores). Python 3.14.7 (default) and 3.12 installed; `uv` and `ffmpeg` present;
  `vhs` and `asciinema` not installed (needed later for the README GIF).
- `gh` 2.97.0 authenticated as `mimitoz62` with `repo` scope.
- Network access works; the NASA Exoplanet Archive TAP endpoint answers in about 2 s.
- The research repository `mimitoz62/hd127195-stability` exists on GitHub (public, MIT). Its
  `paper_analysis.py` is sound and is the starting point for the integration and AMD code: REBOUND 5.2.0,
  units (yr, AU, Msun), WHFast at P_b/30 with spot checks at P_b/60, P_b/100 and IAS15, MEGNO ⟨Y⟩ < 2.2
  counts as regular, close encounter = within the smaller planet Hill radius, escape = beyond 100 a_max,
  critical AMD by minimisation along the collision line.

## D1 — Package name: `exostab` (2026-09-28, chosen by Mehmet)

Checked on 2026-09-28: free on PyPI (`/pypi/exostab/json` returned 404) and free under `mimitoz62` on
GitHub. An unrelated repository `eggls6/exostab2` ("Stability estimates for the three body problem")
exists; the names differ, so no conflict. Alternatives considered: `exostability`, `orbstab`.

## D2 — License: MIT

The brief's default, and the same license as `hd127195-stability`. Not changed, so no question needed.

## D3 — Metadata

Author Mehmet Öz, ORCID 0009-0007-1005-7640, GitHub `mimitoz62`, contact mehmet@mehmet-oz.com
(confirmed by Mehmet on 2026-09-28).

## D4 — Python support: ≥ 3.10, CI on 3.10 to 3.14

- As the brief asks. Caveat: Python 3.10 reaches end of life in October 2026, and the current numpy
  (2.5.x, needs ≥ 3.12), astropy (8.0.x, needs ≥ 3.11) and matplotlib (3.11.x, needs ≥ 3.11) no longer
  support it. On 3.10 pip resolves older releases, so CI must test that combination. Revisit dropping 3.10
  after v0.1.
- Local development uses Python 3.12 in `.venv` (created with `uv venv --python 3.12 .venv`).
- Dependency versions installed on 2026-09-28: rebound 5.2.0, numpy 2.5.3, astropy 8.0.1,
  astroquery 0.4.11, pydantic 2.13.5, typer 0.27.2, rich 15.0.0, matplotlib 3.11.2, platformdirs 4.12.1,
  pytest 9.1.1, hypothesis 6.168.3, ruff 0.16.9, mypy 2.3.1. Only lower bounds are pinned; to be set
  when `pyproject.toml` is written.

## D5 — REBOUND ≥ 5.2

Same version as the Research Note, so the HD 127195 validation compares like with like. Wheels exist for
CPython 3.9 to 3.14 on macOS (x86_64, arm64), Linux (manylinux, musllinux) and Windows.

## D6 — Archive columns (verified against `TAP_SCHEMA.columns` on 2026-09-28)

- Table `pscomppars`: 2,663 planet rows had `sy_pnum >= 2` on 2026-09-28.
- **The brief's assumed `rowupdate` column does not exist in `pscomppars`** (the query fails with
  ORA-00904). Traceability will instead use `pl_name`, the per-parameter `*_reflink` columns,
  `pl_bmassprov` (whether a mass is a true mass or m·sin i), the `*lim` limit flags, `pl_controv_flag`
  and the query timestamp.
- Columns to use (name, unit): `pl_name`, `hostname`, `sy_pnum`, `pl_letter`, `pl_orbper` (days),
  `pl_orbsmax` (au), `pl_orbeccen`, `pl_orblper` (deg), `pl_orbincl` (deg), `pl_orbtper` (days),
  `pl_tranmid` (days), `pl_bmassj` / `pl_bmasse` (mass or m·sin i), `pl_bmassprov`, `pl_radj` / `pl_rade`,
  `st_mass` (Msun), `ttv_flag`, plus the `err1`/`err2`, `lim` and `_reflink` variants.
- A local copy of the column list is in `.handoff/pscomppars_columns_2026-09-28.csv` (not committed).

## D7 — SPOCK conflicts with REBOUND 5 (found 2026-09-28; decision needed at v0.2)

`spock` 2.1.1 (latest on PyPI) requires `rebound>=4.0.1,<5.0.0` (and `celmech<1.6`). It cannot be
installed next to the core package's REBOUND 5.2. Options for v0.2: wait for a SPOCK release that
supports REBOUND 5; run SPOCK in a separate environment; or drop it. Dropping it changes the indicator
set, which needs Mehmet's approval.

## D8 — Proposed scientific defaults (not final)

Taken from the Research Note where possible; each is to be confirmed against the verified references and
the validation suite:

- WHFast timestep: P_min/30 (brief requires ≤ P_min/20), tightened for eccentric inner orbits so the
  pericentre passage is resolved.
- MEGNO: ⟨Y⟩ < 2.2 counts as regular (the Research Note's threshold); check it against thresholds used in
  the literature.
- Relative energy error threshold for "inconclusive": to be set from test runs and documented.
- Close encounter: separation below the smaller Hill radius. Escape: beyond 100 × the largest semi-major axis.
- Default run length: 1e4 orbits of the innermost planet. Reports must state the horizon in years and must
  not imply Gyr stability.

## D9 — Composite-table consistency (open concern)

`pscomppars` can take each parameter from a different publication, so orbital phases may not be
consistent with each other. This matters most for resonant systems (TRAPPIST-1, GJ 876). Proposed fix: for
transiting planets, set phases from `pl_tranmid` (transit at true longitude π/2 in the sky-plane
convention); for RV planets, use `pl_orbtper` with `pl_orblper` when both come from the same reference;
otherwise randomise per draw and flag it. Confirm with the archive's documentation of how the composite
table is built.

## D10 — HD 127195 validation target

From `hd127195-stability/results/results.json`: the best fit is regular (⟨Y⟩ = 2.000 at P_b/30) and survives
1e7 orbits of b; 200/200 Monte Carlo draws pass the AMD test; 134/200 are regular, 57 chaotic without an
encounter, 9 have close encounters within 2e4 orbits. The test tolerance must allow for the archive values
and draw scheme differing from the Note's own inputs, which came from Figueira et al. 2026 Table 2 plus
mean longitudes read from their Fig. C.2.
