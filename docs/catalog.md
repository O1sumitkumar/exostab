# Stability catalog

exostab's three indicators for every multi-planet system in the NASA Exoplanet Archive's Planetary Systems
Composite Parameters table, recomputed every week by the
[catalog workflow](https://github.com/mimitoz62/exostab/blob/main/.github/workflows/catalog.yml).


!!! warning "Read the verdicts with their caveats"
    Every system is checked with the same default settings. Missing orbital phases are drawn at random,
    minimum masses are used as masses, and orbits are coplanar. A resonant system can therefore look unstable
    here, although the full solution of one paper shows it is stable (GJ 876 is the standard example). Run
    `exostab check "<name>"` to see every assumption, or `--from-file` with a published solution.

*No catalog has been published yet.*
