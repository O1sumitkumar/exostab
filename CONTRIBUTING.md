# Contributing to exostab

Thank you for helping. Bug reports, questions about specific systems and proposals for new indicators are all
welcome; please use the issue templates.

## Development setup

```bash
git clone https://github.com/mimitoz62/exostab
cd exostab
python -m venv .venv && source .venv/bin/activate   # Python 3.10 or newer
pip install -e ".[dev]"
pre-commit install                                   # optional: run ruff and mypy before each commit
```

## Checks

```bash
ruff check src tests scripts && ruff format --check src tests scripts
mypy
pytest                      # fast suite (about 15-20 s), uses the bundled offline snapshot
pytest --cov=exostab        # coverage; CI requires at least 85%
pytest -m slow              # validation suite (about a minute on many cores)
mkdocs serve                # documentation preview
```

Tests never touch the network or your cache: `tests/conftest.py` sets `EXOSTAB_OFFLINE=1` and a temporary
`EXOSTAB_CACHE_DIR`.

## Scientific standards

- Every formula and threshold cites a source that has been checked (title, journal, year, DOI) and is in
  `docs/references.bib`. Quote equation numbers in docstrings.
- Every data assumption must produce a `CompletionFlag` so that it appears in the report.
- Never weaken a validation tolerance to make a test pass. If a result disagrees with the literature, open an
  issue and describe it.
- Record new defaults and thresholds, and why they were chosen, in `DECISIONS.md`.

## How to add an indicator

1. Create `src/exostab/indicators/<name>.py` with:
   - `classify(realization) -> Verdict` for one set of parameters;
   - `evaluate(nominal, draws) -> IndicatorResult`, which calls `combine()` from `exostab.indicators` so the
     95% agreement rule applies;
   - a module docstring with the equations and references, and a `REFERENCES` list of BibTeX keys.
2. Add it to `check_system()` in `src/exostab/analysis.py`, and decide with the maintainers how it enters
   `overall_verdict()`. Changing the indicator set needs an issue first.
3. Add unit tests, including hypothesis property tests for invariants, and a validation test against published
   numbers in `tests/validation/`.
4. Document it in `docs/methods.md` and regenerate the JSON schema: `python -m exostab.report`.

## Updating the offline snapshot

```bash
python scripts/make_snapshot.py   # downloads the listed systems and rewrites src/exostab/data/snapshot/
```

Validation numbers and figures in `docs/validation.md` come from `scripts/validation_summary.py` and
`scripts/validation_figures.py` (run from the repository root with `PYTHONPATH=.`); rerun both after changes
that can affect them.

## Releases

Maintainers follow [RELEASING.md](RELEASING.md): set the version in `src/exostab/__init__.py` and
`CITATION.cff` (with `date-released`), move the "Unreleased" changelog entries under the new version, and push a
tag `vX.Y.Z`. The release workflow checks that these agree, builds the package, tests the built wheel, uploads
it to PyPI with trusted publishing when the repository variable `PUBLISH_PYPI` is `true`, and creates the GitHub
release (archived by Zenodo). RELEASING.md also covers the one-time setup of PyPI, Zenodo, Streamlit Community
Cloud and the catalog's Zenodo dataset.
