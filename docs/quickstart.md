# Quickstart

## Install

```bash
pip install "exostab @ git+https://github.com/mimitoz62/exostab@v1.0.0"
```

This installs release 1.0.0 from GitHub; `pip install git+https://github.com/mimitoz62/exostab` installs the
current development version instead. A release on PyPI is planned. Requires Python 3.10 or newer; exostab is
tested on Linux and macOS.

Optional extras use the same form:

```bash
pip install "exostab[web] @ git+https://github.com/mimitoz62/exostab@v1.0.0"       # the web app
pip install "exostab[catalog] @ git+https://github.com/mimitoz62/exostab@v1.0.0"   # Parquet output of catalog build
```

Without the `[catalog]` extra, `exostab catalog build` writes `catalog.csv` but no `catalog.parquet`, and does not
say so.

## Check a system

```bash
exostab check "TRAPPIST-1"
```

The first run downloads the archive's multi-planet table (about 2,700 rows; 7 s on 13 October 2026) and caches
it. The report card shows:

- the parameters used, with a mark on every value that was assumed, derived, estimated or randomized;
- one verdict per indicator, with an explanation;
- the overall verdict;
- the data-completion rules that were applied.

The folder `exostab-results/trappist-1/` then contains `report.json`, `orbits.png` and `megno.png`.

Useful options:

```bash
exostab check "HD 127195" --orbits 100000 --draws 50 --seed 7 --out results/
exostab check "HD 127195" --inclination-prior isotropic   # true masses from random inclinations
exostab check "HD 127195" --budget fast                   # run length and draws chosen to fit about 10 s
exostab check "Kepler-11" --offline                       # bundled snapshot, no network
exostab check --from-file examples/two_planet.yaml        # your own parameters
```

## Explore one parameter

```bash
exostab sweep "HD 127195" --planet b --param e --range 0 0.6 --steps 25
```

This writes `sweep.csv`, `sweep.png` and `sweep.json` (seed, run length, range, steps and the command): MEGNO, the
Hill spacing and the AMD ratio as the eccentricity of planet b changes, all other parameters fixed. `--range` is
required for `--param mass`, `period` and `omega`; for `e` it defaults to 0 to 0.5.

## Find systems

```bash
exostab list --min-planets 4 --max-period-days 200
```

## Web app

```bash
python -m exostab.web
```

This starts the browser version locally (it needs the `[web]` extra); see [Web app](web.md).
