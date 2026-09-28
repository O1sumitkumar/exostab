# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `exostab check --budget fast|thorough|<seconds>` chooses the run length and number of draws from a measured
  integration speed (report schema 1.1 records `settings.budget_s`).

### Changed

- The IAS15 check starts first, so long checks finish sooner.
- Close encounters are detected for each pair of planets (closer than the mean of their Hill radii) with
  REBOUND collision detection, instead of one global distance set by the smallest planet (DECISIONS.md, D20).

## [0.1.0] - unreleased

### Added

- `exostab check` for any multi-planet system in the NASA Exoplanet Archive (`pscomppars`), or from a YAML file,
  with a report card, `report.json` (schema 1.0), `orbits.png` and `megno.png`.
- Three indicators: Hill spacing (Gladman 1993; multi-planet spacing heuristic), angular momentum deficit
  (Laskar & Petit 2017; Petit, Laskar & Boué 2017, 2018) and REBOUND N-body integration with MEGNO, WHFast with
  an IAS15 cross-check.
- Monte Carlo draws within the published uncertainties, reproducible with `--seed`, and an optional isotropic
  inclination prior for minimum masses.
- Explicit, flagged data-completion rules; disk cache with `--refresh`; bundled offline snapshot of 22 systems.
- `exostab sweep`, `exostab list` and `exostab catalog build`.
- Validation suite (inner Solar System, Hill limit, TRAPPIST-1, GJ 876, Kepler-11, HD 127195 Research Note).
