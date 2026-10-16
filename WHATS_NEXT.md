# What's next

Open work is tracked in the [GitHub issues](https://github.com/mimitoz62/exostab/issues). Items 1–13 below are
issues [#1](https://github.com/mimitoz62/exostab/issues/1)–[#13](https://github.com/mimitoz62/exostab/issues/13);
the items after them are proposed issues, listed by title, that have not been opened yet. Decisions referred to
as Dn are in [DECISIONS.md](DECISIONS.md).

## Issues #1–#13

1. [#1](https://github.com/mimitoz62/exostab/issues/1) **Streamlit web app.** Done (`python -m exostab.web`);
   to be closed.
2. [#2](https://github.com/mimitoz62/exostab/issues/2) **Deploy the web app.** The repository is prepared for
   Streamlit Community Cloud (`requirements.txt`, `.streamlit/config.toml`, steps in RELEASING.md); deploying needs
   Mehmet's account. No hosted instance exists yet.
3. [#3](https://github.com/mimitoz62/exostab/issues/3) **Time-budget mode** (`--budget`). Done (D19); to be closed.
4. [#4](https://github.com/mimitoz62/exostab/issues/4) **SPOCK as an optional fourth indicator.** Done, in a
   separate environment because SPOCK 2.1.1 needs REBOUND < 5 (D23); to be closed. Whether to keep this design is
   Mehmet's decision.
5. [#5](https://github.com/mimitoz62/exostab/issues/5) **Interactive plots** for the web app. Done; to be closed.
6. [#6](https://github.com/mimitoz62/exostab/issues/6) **Calibrate the MEGNO threshold against run length** (D8).
   ⟨Y⟩ ≥ 2.2 is the Research Note's choice. TRAPPIST-1's nominal configuration shows the dependence: ⟨Y⟩ = 2.17
   after 1e4 orbits, 6.46 after 5e4.
7. [#7](https://github.com/mimitoz62/exostab/issues/7) **Calibrate the energy-error limit** (D8). The limit is
   10⁻⁵, checked at 1,200 times in every run; the maximum found grows with the number of checks.
8. [#8](https://github.com/mimitoz62/exostab/issues/8) **Multi-planet spacing threshold** (D12). 12 mutual Hill
   radii is now a floor, and the required spacing grows with eccentricity (Pu & Wu 2015, Eq. 15 as corrected in
   2016); eccentricities above 0.05 never give stable. Remaining: calibrate the eccentricity term beyond 0.05 and
   its dependence on the number of planets.
9. [#9](https://github.com/mimitoz62/exostab/issues/9) **Correlated uncertainties.** Draws are independent; use
   published posterior samples where they exist.
10. [#10](https://github.com/mimitoz62/exostab/issues/10) **Self-consistent solutions** from the archive's `ps`
    table, so that phases, periods and eccentricities come from one paper where possible (D9).
11. [#11](https://github.com/mimitoz62/exostab/issues/11) **Stellar vs planetary ω.** The archive does not
    standardize the convention, and for transit-derived phases of eccentric planets a wrong convention changes
    the starting configuration, not just its orientation (D9, corrected 2026-10-13).
12. [#12](https://github.com/mimitoz62/exostab/issues/12) **Longer horizons for hierarchical systems.** The run
    length is set by the innermost planet; fewer than 100 orbits of the outermost planet currently only prevent a
    "stable" N-body verdict (with a note).
13. [#13](https://github.com/mimitoz62/exostab/issues/13) **Python 3.10** reaches end of life in October 2026;
    decide whether to drop it.

## Proposed issues (not yet opened)

From the review of October 2026; the reasons are in the DECISIONS.md entries named.

Verdicts and indicators:

- Decide: should one close-encounter draw block an overall 'stable'? (D27)
- Decide on a minimum number of draws for a confident verdict
- Keep an 'unstable' verdict that does not depend on the upper-limit values (KOI-319) (D27)
- Use a physical nominal mass instead of a loose upper limit (m sin i or mass-radius estimate) (D11)
- Say when Hill/AMD verdicts rest on assumed circular orbits; consider an eccentricity prior (D14, D24)
- Add per-indicator notes when draws disagree but the verdict stands
- Name the actual reason in the marginal summary instead of "typical of systems protected by mean-motion
  resonances or of compact systems"
- AMD: replace the fixed equipartition factor (β = 2β_p) with sampled mutual inclinations (D14)
- AMD: find a criterion for pairs above α_R that lie outside the domain of Petit et al. (2017) (D14)
- Hill multi-planet heuristic: calibrate the eccentricity dependence beyond e = 0.05, and compare a dispersion
  estimate rather than each planet's e with it (extends #8; D12)
- hill.gladman_critical_separation fails for very massive pairs (its period-ratio bracket ends at 10)
- Use a physical threshold for planets passing close to the star (D20)
- Energy-error maximum depends on how often it is checked (related to #7; D8)
- Companion stars: model them, or detect planets that cannot share one star (D27)

Data:

- Rescale planet masses to the stellar mass used, or propagate the stellar-mass spread (D24)
- Accept directly imaged planets whose semi-major axis comes from an orbit fit (D24)
- Document or revisit the 0.95 eccentricity cap; make `sweep --param e` consistent with it (D24)
- Refine the semimajor_axis_au / period_days consistency tolerance for YAML files (D24)
- Radii calculated by the archive are labelled 'measured'

Web app, CLI, packaging:

- Web app: enforce a wall-clock limit on integrations, not only an estimated cost (D28)
- Web app: refresh the archive cache when it is old, and put the data date in shared links (docs/web.md)
- Web app: derive the largest what-if period ratio from the loaded table (D28)
- `catalog build`: say when `catalog.parquet` is not written because pyarrow is missing
- Make the SPOCK environment script available from the installed package, and pin the whole SPOCK environment
  with per-platform constraint files (D23)
- Derive the sdist guard test's file list from the tests

## Account-side actions for Mehmet (not issues)

- Report to the NASA Exoplanet Archive that HD 127195 b and c list `pl_orblper` = 3.10 and 4.12 "deg". These
  are the radian values of Figueira et al. (2026), Table 2 (D18).
- PyPI trusted publishing, the Zenodo software DOI, Streamlit Community Cloud and the catalog's Zenodo dataset:
  see RELEASING.md. GitHub Pages and private vulnerability reporting are already set up.
