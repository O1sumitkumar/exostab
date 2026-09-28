# What's next

Each item below is also a GitHub issue (linked once the repository is public). Milestones follow PLAN.md.

## v0.2: web app and optional SPOCK indicator

1. **Streamlit web app** (`src/exostab/web/app.py`, `[web]` extra with streamlit and plotly):
   - system search with autocomplete over archive host names;
   - editable per-planet parameter table;
   - sliders for mass, eccentricity and period ratio;
   - a "Run" button with a time budget (fast ≈ 10 s, thorough ≈ 2 min) that sets `--orbits` and `--draws`;
   - orbit and MEGNO plots and completion-flag warnings;
   - a shareable link that encodes the parameters in the URL;
   - downloads of the figures and `report.json`, and a feedback link;
   - results cached by a hash of all inputs.
2. **Deploy the web app.** Check that Streamlit Community Cloud is still free and available (fallback: Hugging
   Face Spaces). Prepare `requirements.txt` and config without secrets, then write click-by-click deployment
   steps. Deploying needs Mehmet's account.
3. **Time-budget mode for the CLI** (`--budget fast|thorough`), shared with the web app, so that run length and
   draws are chosen from a measured speed rather than fixed.
4. **SPOCK as an optional fourth indicator** (Tamayo et al. 2020) for 3+ planets, `[ml]` extra. **Blocked:**
   SPOCK 2.1.1 (latest, checked 2026-09-28) requires `rebound<5`, and exostab uses REBOUND 5.2. Options: wait for
   a SPOCK release, run it in a separate environment, or drop it. Dropping it changes the indicator set and needs
   Mehmet's decision (DECISIONS.md, D7).
5. **Interactive plots** (plotly) for the web app, reusing `plots.py`'s colours and markers.

## Scientific follow-ups from v0.1 (uncertain choices, DECISIONS.md)

6. **Calibrate the MEGNO threshold against run length** (D8). ⟨Y⟩ ≥ 2.2 is the Research Note's choice. Measure
   the ⟨Y⟩ distribution of clearly regular and clearly chaotic test systems at 10³–10⁶ orbits, and make the
   threshold depend on the horizon or on the IAS15/WHFast difference.
7. **Calibrate the energy-error limit** (D8). The current limit is 10⁻⁵. Test on chaotic and eccentric systems
   whether a stricter limit changes verdicts or only produces "inconclusive" runs.
8. **Multi-planet spacing threshold** (D12). 12 mutual Hill radii is a single number from Pu & Wu (2015). Replace
   it with a mass- and eccentricity-dependent criterion from the literature, e.g. an instability-time fit with
   Obertas et al. (2017)-style coefficients.
9. **Correlated uncertainties.** Draws are independent Gaussians. Where published posterior samples exist, use
   them. This matters most for eccentricities (Kepler-11) and resonant systems.
10. **Self-consistent solutions.** Offer `--solution default`, which uses the archive's Planetary Systems (`ps`)
    table default solution of each planet, so that phases, periods and eccentricities come from one paper where
    possible. Today the composite table can mix publications (D9).
11. **Stellar vs planetary ω.** Record which convention each publication uses (RV papers often give the star's
    ω) so that transit-based phases of eccentric planets are exact (D9).
12. **Longer horizons for hierarchical systems.** The run length is set by the innermost planet. Add a minimum
    number of orbits of the outermost planet, which is currently only a warning below 100.
13. **Python 3.10** reaches end of life in October 2026 and current numpy/astropy no longer support it. Decide
    whether to drop it after v0.1.

## Account-side actions for Mehmet (not issues)

- Report to the NASA Exoplanet Archive that HD 127195 b and c list `pl_orblper` = 3.10 and 4.12 "deg". These
  are the radian values of Figueira et al. (2026), Table 2 (DECISIONS.md, D18).
- PyPI trusted publishing, Zenodo, GitHub Pages: see the final report of the v0.1 session.
