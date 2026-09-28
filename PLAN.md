# exostab — plan

exostab is an open-source tool that tells you whether a known exoplanet system is dynamically
stable, using three independent indicators (Hill spacing, angular momentum deficit, N-body + MEGNO)
and parameters fetched from the NASA Exoplanet Archive.

This file is the working plan. Decisions and their reasons live in [DECISIONS.md](DECISIONS.md).

## Status (updated 2026-09-28)

**Paused after setup. No package code written yet.**

Done:
- [x] Environment inspected (see DECISIONS.md, D0)
- [x] Name chosen: `exostab` (D1), project folder `~/Projects/exostab`, git initialised on `main`
- [x] Local dev environment: `.venv` (Python 3.12, created with `uv`) with the core dependencies installed
- [x] Archive reachable; `pscomppars` column names checked against `TAP_SCHEMA` (D6)
- [x] Current PyPI versions of every planned dependency checked (D4, D5, D7)

Started, not finished:
- [ ] Reference verification. A multi-agent check of every citation (title, year, journal, DOI) and
  extraction of the load-bearing formulas (Gladman 1993 criterion, Laskar & Petit 2017 critical AMD,
  Petit et al. 2017 MMR-overlap criterion, Petit et al. 2018 AMD-Hill criterion, Chen & Kipping 2017
  parameters, MEGNO thresholds used in the literature) was launched and then stopped when the session
  was paused. **Nothing from it has been recorded; re-run it first.** The script is kept locally (not
  committed) in `.handoff/verify_references.workflow.js`.

### How to resume

1. Open a Claude Code session in `~/Projects/exostab` and say: *"Continue exostab from PLAN.md."*
2. `source .venv/bin/activate` (or recreate it: `uv venv --python 3.12 .venv` and reinstall; see D4).
3. Re-run reference verification (step 0 below), then start the v0.1 spine (step 1).

## v0.1 — minimum viable product (build end to end first)

0. Verify references and formulas; write `docs/references.bib` from verified entries only.
1. **Spine** (commit when green):
   - `pyproject.toml` (src layout, hatchling, entry point `exostab`), `src/exostab/__init__.py`
   - `models.py`: Star, Planet, System (pydantic), each value carrying its provenance and completion flag
   - `data/`: archive client (astroquery TAP on `pscomppars`), on-disk cache (platformdirs, `--refresh`),
     offline snapshot of about 20 well-known systems
   - `indicators/hill.py`: mutual Hill separations, Gladman 1993 two-planet criterion,
     Chambers et al. 1996 multi-planet heuristic
   - `report.py` (minimal) + `cli.py` with `exostab check NAME` printing a Rich report card
   - one validation test: a synthetic two-planet system past the Hill limit comes out unstable
2. Data completion rules (explicit, logged, shown in every report): e → 0 "assumed"; ω, Ω, M randomised
   per draw; m·sin i treated as minimum mass (+ `--inclination-prior`); mass from radius via a published
   mass–radius relation, "estimated"; missing inclinations → coplanar.
3. `indicators/amd.py`: Laskar & Petit 2017 AMD stability, with the MMR-overlap (Petit, Laskar & Boué 2017)
   and Hill (Petit, Laskar & Boué 2018) refinements.
4. `integrate.py` + `indicators/megno.py`: REBOUND (units yr, AU, Msun), WHFast with the timestep
   justified in comments, IAS15 cross-check and close encounters, escape/encounter exits, relative energy
   error on every run ("inconclusive" above threshold), Monte Carlo over archive uncertainties
   (default 20 draws), `--seed`.
5. Per-indicator verdicts (stable / marginal / unstable / inconclusive) + conservative overall summary.
6. `report.py`: versioned JSON schema (seed, versions, integrator, dt, run length, snapshot date, flags,
   archive row identifiers); `plots.py`: `orbits.png`, `megno.png`.
7. CLI: `check` (by name, `--from-file`, `--orbits`, `--draws`, `--seed`, `--out`), `sweep`, `list`,
   `catalog build --limit`.
8. Validation suite (marked `slow`): inner Solar System energy conservation over 1e4 yr; TRAPPIST-1
   (stable or marginal, never unstable); GJ 876 (stable); Kepler-11 (stable over test horizon);
   HD 127195 reproduces the Research Note's conclusions; synthetic past-Hill-limit system unstable.
9. Tests: unit tests per module, hypothesis property tests, CLI smoke tests, ≥ 85% coverage.
10. CI: ruff + mypy + pytest on Linux and macOS, Python 3.10 to latest; nightly slow suite; release
    workflow with PyPI trusted publishing.
11. Repo hygiene: README (GIF, quickstart, example report card, Mermaid diagram, limitations, citation,
    acknowledgments incl. NASA Exoplanet Archive text), LICENSE (MIT), CITATION.cff, CONTRIBUTING.md,
    CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md, issue/PR templates, pre-commit, .editorconfig.
12. Create the public GitHub repo `mimitoz62/exostab`, push, get CI green.
13. WHATS_NEXT.md with v0.2 tasks, each opened as a GitHub issue; issues for uncertain scientific choices.
14. Run every README command; final report with the TRAPPIST-1 and HD 127195 report cards.

## v0.2

- Streamlit web app (search, editable table, sliders, time budget, plots, shareable URL, downloads,
  result cache keyed on an input hash); deploy to Streamlit Community Cloud (fallback: Hugging Face Spaces).
- Optional SPOCK indicator for 3+ planet systems (`[ml]` extra). **Blocked**, see D7.

## v1.0

- Weekly GitHub Actions catalog job (all archive systems with ≥ 2 planets, per-system time cap) →
  `catalog.csv` + `catalog.parquet` as release assets and a sortable docs table.
- MkDocs Material site on GitHub Pages (Quickstart, CLI reference, Methods, Data assumptions,
  Validation, FAQ, Changelog).
- Zenodo DOI, `CITATION.cff`, draft `paper/paper.md` (JOSS).
