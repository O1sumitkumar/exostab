# Quickstart

## Install

```bash
pip install git+https://github.com/mimitoz62/exostab
```

(After the first release: `pip install exostab`.) Requires Python 3.10 or newer. Wheels of REBOUND exist for
Linux, macOS and Windows.

## Check a system

```bash
exostab check "TRAPPIST-1"
```

The first run downloads the archive's multi-planet table (about 10 seconds) and caches it. The report card shows:

- the parameters used, with a mark on every value that was assumed, derived, estimated or randomized;
- one verdict per indicator, with an explanation;
- the overall verdict;
- the data-completion rules that were applied.

The folder `exostab-results/trappist-1/` then contains `report.json`, `orbits.png` and `megno.png`.

Useful options:

```bash
exostab check "HD 127195" --orbits 100000 --draws 50 --seed 7 --out results/
exostab check "HD 127195" --inclination-prior isotropic   # true masses from random inclinations
exostab check "Kepler-11" --offline                       # bundled snapshot, no network
exostab check --from-file examples/two_planet.yaml        # your own parameters
```

## Explore one parameter

```bash
exostab sweep "HD 127195" --planet b --param e --range 0 0.6 --steps 25
```

This writes `sweep.csv` and `sweep.png`: MEGNO, the Hill spacing and the AMD ratio as the eccentricity of planet b
changes, all other parameters fixed.

## Find systems

```bash
exostab list --min-planets 4 --max-period-days 200
```
