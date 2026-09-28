# exostab — plan

exostab is an open-source tool that tells you whether a known exoplanet system is dynamically
stable, using three independent indicators (Hill spacing, angular momentum deficit, N-body + MEGNO)
and parameters fetched from the NASA Exoplanet Archive.

This file is the working plan. Decisions and their reasons live in [DECISIONS.md](DECISIONS.md).

## Status (updated 2026-09-28, end of the v0.1 build session)

**v0.1 is built and tested locally.** What is done, what is waiting, and why:

Done:
- [x] Reference verification: every citation checked against Crossref/arXiv/DataCite, and the load-bearing
  formulas taken from the arXiv LaTeX sources (DECISIONS.md, D13); `docs/references.bib`.
- [x] Steps 1–11 below: package, data layer (archive, cache, snapshot, completion rules), three indicators,
  report and JSON schema, plots, CLI (`check`, `sweep`, `list`, `catalog build`), unit and property tests
  (98% coverage), validation suite (16 slow tests), docs, CI workflows, repository files.
- [x] Every README command run by hand (see the session's final report).

Waiting:
- [ ] Step 12: the public repository mimitoz62/exostab exists (commits use the GitHub noreply address), but
  the push waits for Mehmet to add the `workflow` scope: `gh auth refresh -h github.com -s workflow`, then
  `git push -u origin main`. After that, check that CI is green.
- [x] Step 13: issues #1–#13 opened (WHATS_NEXT.md).
- [ ] Account-side: PyPI trusted publisher, Zenodo, GitHub Pages; then tag v0.1.0.

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
