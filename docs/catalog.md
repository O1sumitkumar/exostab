---
hide:
  - navigation
  - toc
---

# Stability catalog

exostab's three indicators for every multi-planet system in the NASA Exoplanet Archive's Planetary Systems
Composite Parameters table, recomputed every week by the
[catalog workflow](https://github.com/mimitoz62/exostab/blob/main/.github/workflows/catalog.yml).


!!! warning "Read the verdicts with their caveats"
    Every system is checked with the same settings. Missing orbital phases are drawn at random,
    minimum masses are used as masses, and orbits are coplanar. A resonant system can therefore look unstable
    here, although the full solution of one paper shows it is stable (GJ 876 is the standard example).
    Masses and eccentricities that are only upper limits are used at the limit, with draws below it; a system
    whose instability rests on them is shown as marginal. Systems exostab cannot model (for example circumbinary
    planets, a planet with neither mass nor radius, or a host whose other planets orbit a companion star) are
    listed as skipped with the reason. A run in which a planet passes within half its Hill radius of the star
    gets no verdict. Run `exostab check "<name>"` to see every assumption, or `--from-file` with a published
    solution.

*This copy of the page has no catalog table: it was generated without a catalog. The documentation workflow builds
the [published page](https://mimitoz62.github.io/exostab/catalog/) from the newest catalog on the branch [`catalog-data`](https://github.com/mimitoz62/exostab/tree/catalog-data).*
