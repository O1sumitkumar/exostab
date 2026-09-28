# Decisions

Each entry records what was decided, why, and when. Entries D0–D7 were written during setup; D8 onwards
were written while building v0.1 (2026-09-28), after the references and formulas were checked against
their primary sources (D13).

## D0 — Environment found (2026-09-28)

- macOS on Apple M4 Pro (14 cores). Python 3.14.7 (default) and 3.12 installed; `uv` and `ffmpeg` present;
  `vhs` and `asciinema` not installed (needed later for the README GIF).
- `gh` 2.97.0 authenticated as `mimitoz62` with `repo` scope.
- Network access works; the NASA Exoplanet Archive TAP endpoint answers in about 2 s.
- The research repository `mimitoz62/hd127195-stability` exists on GitHub (public, MIT). Its
  `paper_analysis.py` is sound and is the starting point for the integration and AMD code: REBOUND 5.2.0,
  units (yr, AU, Msun), WHFast at P_b/30 with spot checks at P_b/60, P_b/100 and IAS15, MEGNO ⟨Y⟩ < 2.2
  counts as regular, close encounter = within the smaller planet Hill radius, escape = beyond 100 a_max,
  critical AMD by minimisation along the collision line.

## D1 — Package name: `exostab` (2026-09-28, chosen by Mehmet)

Checked on 2026-09-28: free on PyPI (`/pypi/exostab/json` returned 404) and free under `mimitoz62` on
GitHub. An unrelated repository `eggls6/exostab2` ("Stability estimates for the three body problem")
exists; the names differ, so no conflict. Alternatives considered: `exostability`, `orbstab`.

## D2 — License: MIT

The brief's default, and the same license as `hd127195-stability`. Not changed, so no question needed.

## D3 — Metadata

Author Mehmet Öz, ORCID 0009-0007-1005-7640, GitHub `mimitoz62`, contact mehmet@mehmet-oz.com
(confirmed by Mehmet on 2026-09-28).

## D4 — Python support: ≥ 3.10, CI on 3.10 to 3.14

- As the brief asks. Caveat: Python 3.10 reaches end of life in October 2026, and the current numpy
  (2.5.x, needs ≥ 3.12), astropy (8.0.x, needs ≥ 3.11) and matplotlib (3.11.x, needs ≥ 3.11) no longer
  support it. On 3.10 pip resolves older releases, so CI must test that combination. Revisit dropping 3.10
  after v0.1.
- Local development uses Python 3.12 in `.venv` (created with `uv venv --python 3.12 .venv`).
- Dependency versions installed on 2026-09-28: rebound 5.2.0, numpy 2.5.3, astropy 8.0.1,
  astroquery 0.4.11, pydantic 2.13.5, typer 0.27.2, rich 15.0.0, matplotlib 3.11.2, platformdirs 4.12.1,
  pytest 9.1.1, hypothesis 6.168.3, ruff 0.16.9, mypy 2.3.1. Only lower bounds are pinned; to be set
  when `pyproject.toml` is written.

## D5 — REBOUND ≥ 5.2

Same version as the Research Note, so the HD 127195 validation compares like with like. Wheels exist for
CPython 3.9 to 3.14 on macOS (x86_64, arm64), Linux (manylinux, musllinux) and Windows.

## D6 — Archive columns (verified against `TAP_SCHEMA.columns` on 2026-09-28)

- Table `pscomppars`: 2,663 planet rows had `sy_pnum >= 2` on 2026-09-28.
- **The brief's assumed `rowupdate` column does not exist in `pscomppars`** (the query fails with
  ORA-00904). Traceability will instead use `pl_name`, the per-parameter `*_reflink` columns,
  `pl_bmassprov` (whether a mass is a true mass or m·sin i), the `*lim` limit flags, `pl_controv_flag`
  and the query timestamp.
- Columns to use (name, unit): `pl_name`, `hostname`, `sy_pnum`, `pl_letter`, `pl_orbper` (days),
  `pl_orbsmax` (au), `pl_orbeccen`, `pl_orblper` (deg), `pl_orbincl` (deg), `pl_orbtper` (days),
  `pl_tranmid` (days), `pl_bmassj` / `pl_bmasse` (mass or m·sin i), `pl_bmassprov`, `pl_radj` / `pl_rade`,
  `st_mass` (Msun), `ttv_flag`, plus the `err1`/`err2`, `lim` and `_reflink` variants.
- A local copy of the column list is in `.handoff/pscomppars_columns_2026-09-28.csv` (not committed).

## D7 — SPOCK conflicts with REBOUND 5 (found 2026-09-28; decision needed at v0.2)

`spock` 2.1.1 (latest on PyPI) requires `rebound>=4.0.1,<5.0.0` (and `celmech<1.6`). It cannot be
installed next to the core package's REBOUND 5.2. Options for v0.2: wait for a SPOCK release that
supports REBOUND 5; run SPOCK in a separate environment; or drop it. Dropping it changes the indicator
set, which needs Mehmet's approval.

## D8 — Integration settings (final for v0.1, 2026-09-28)

| Setting | Value | Why |
|---|---|---|
| Unit system | `sim.units = ("yr", "AU", "Msun")`, set before any particle is added | Brief; the Julian year of astropy and REBOUND agree; `tests/test_units.py` checks G |
| Coordinates | Planets added by period in Jacobi coordinates (REBOUND default) | Same as the Research Note; Rivera et al. (2010) elements are Jacobi |
| Main integrator | WHFast (REBOUND 5.2 defaults: Jacobi, safe mode on, no symplectic corrector) | Brief; fast and symplectic |
| Timestep | 1/30 of the shortest pericentre-passage timescale T_p = P (1−e)^{3/2}/(1+e)^{1/2} | Wisdom (2015) found T_p/20 adequate (as restated by Hadden & Lithwick 2018, who used 1/30); equals P_min/30 for circular orbits (Note's choice, finer than the brief's P_min/20) |
| Cross-check | IAS15 repeats the nominal run with MEGNO; disagreement prevents a "stable" N-body verdict | Brief |
| Run length | 1e4 orbits of the innermost planet (`--orbits`) | Brief. Reports state the horizon in years and never imply Gyr stability. If the outermost planet completes < 100 orbits the N-body verdict cannot be "stable" |
| Close encounter | two planets closer than the mean of their Hill radii, (R_H,j + R_H,k)/2 (REBOUND collision detection, "line" mode) | Changed from the Research Note's global rule, see D20 |
| Escape | distance from the centre of mass above 100 × the largest semi-major axis | Research Note's rule |
| MEGNO threshold | ⟨Y⟩ ≥ 2.2 is chaotic | See below |
| Energy-error limit | maximum relative energy error over the run (sampled 400 times for the nominal run, at the end for draws) > 1e-5 → run "inconclusive" | See below |

**MEGNO threshold (uncertain).** ⟨Y⟩ → 2 for quasi-periodic orbits and grows linearly for chaotic ones
(Cincotta & Simó 2000; restated by Goździewski et al. 2008, arXiv:0802.0254, and Maffione et al. 2011,
arXiv:1108.5481). Published working thresholds vary with integration length: |⟨Y⟩−2| ≤ 0.001 after 1e5 yr
(Satyal et al. 2013, arXiv:1211.3956), 2.01 (Maffione et al. 2011, galactic potentials), ⟨Y⟩ ≳ 5 as
"chaotic" on colour scales (Goździewski et al. 2015, arXiv:1510.02776). These four were read in their arXiv
LaTeX sources but are not in `docs/references.bib`. 2.2 is the Research Note's value, which the HD 127195 validation reproduces. A lower value would be
more conservative but, at 1e4 orbits, would also flag regular orbits whose ⟨Y⟩ has not converged (for
example TRAPPIST-1's nominal run gives 2.17 with both WHFast and IAS15). Kept at 2.2; improvement tracked in issue #6.

**Energy-error limit (uncertain).** Measured values: 1.4e-9 (inner Solar System, 1e4 yr), 4e-8 (GJ 876),
2.4e-7 (TRAPPIST-1), up to 3.5e-6 for chaotic HD 127195 draws. 1e-5 leaves room for chaotic runs whose
MEGNO is still meaningful while catching broken integrations. Petit et al. (2018) used 1e-8 with a
higher-order integrator. Improvement tracked in issue #7.

## D9 — Orbital phases (resolved, 2026-09-28)

The composite table can take each parameter from a different publication (archive documentation,
`pscp_about.html`, `pscp_calc.html`). Phases are therefore used only when they are safe to combine with the
period:

1. Transiting planet (`tran_flag = 1`) with `pl_tranmid`: phase from the transit time, whatever its
   reference (transit times are direct observations); the report notes when the period comes from another
   publication. Uncertainties of the transit time and the period are propagated to the common epoch in
   every draw.
2. Non-transiting planet with a time of conjunction (`pl_tranmid`): used only if it comes from the same
   publication as the period.
3. Time of periastron (`pl_orbtper`): used only if from the same publication as the period **and** not shared
   by several planets of the system. (GJ 876 lists 2450602.093 for all four planets: that is the osculating
   epoch of Rivera et al. 2010, not a time of periastron.)
4. Otherwise the mean anomaly is drawn uniformly in every run, including the nominal run, and the N-body
   verdict carries a note that resonant systems can look unstable with random phases.

The common epoch is the reference time that minimises the summed variance of the propagated phases.
Mid-transit is at true anomaly f = π/2 − ω (Winn 2010, Eq. 6). If a publication gives the star's ω (RV
convention) instead of the planet's, the phase of an eccentric planet is off by the difference; for a
common convention across all planets of a coplanar system the error is a rotation of the whole system and
does not affect the dynamics.

## D10 — HD 127195 validation target (final)

The validation uses `examples/hd127195_note.yaml`, which holds the Note's own inputs (`paper_analysis.py`
`BEST`/`ERR`, angles converted from radians to degrees), and the Note's settings (2e4 orbits of b, 200
draws, WHFast at P_b/30, MEGNO < 2.2). Tolerances (`tests/validation/test_validation.py`):

- geometry (a_b, a_c, period ratio, 4.37 mutual Hill radii): relative 1e-5 to 1e-3;
- best-fit ⟨Y⟩ = 2.00 ± 0.02 with WHFast and IAS15;
- Monte Carlo fractions within 3 binomial standard deviations of 134/200 regular and 9/200 close encounters
  (draws are independent Gaussians in both codes, but the random streams differ);
- every draw passes the Laskar & Petit (2017) collision criterion (Note N7);
- AMD limit for equal eccentricities 0.1478 ± 0.0005 (Note N11);
- conclusion: nominal regular, N-body verdict marginal, overall marginal.

Measured on 2026-09-28 (seed 42): 133 regular, 62 chaotic, 5 close encounters.

Note: with the Petit et al. (2017) resonance-overlap refinement, which the Note did not use, the pair falls in
the "MMR overlap" branch (α = 0.742 > α_R = 0.728) and some draws are AMD-unstable, so exostab's AMD verdict
for these inputs is "marginal" although every draw passes the collision criterion.

## D11 — Data completion rules (final for v0.1)

As in the brief, plus these choices:

- Missing eccentricity → 0, "assumed". Upper limits (`*lim = 1`): the nominal run uses the limit (worst case
  for stability) and draws are uniform between 0 and the limit. Lower limits are used as values, flagged.
- Draws: split normal on asymmetric errors; negative eccentricities set to 0 (as in the Note), capped at
  0.95; masses, periods and stellar mass redrawn until positive. Values without errors are held fixed.
- **Deviation:** the longitude of the ascending node is not randomized. exostab integrates coplanar systems,
  in which Ω and ω only enter as ϖ = Ω + ω; randomizing ω (when it is missing) is equivalent.
- Sky-plane inclinations are not used (they do not give mutual inclinations); all orbits coplanar, flagged.
- m sin i: used as the mass (sin i = 1) by default; `--inclination-prior isotropic` draws one inclination per
  draw for the whole system with cos i uniform, truncated at sin i ≥ 0.1 (true mass ≤ 10 × minimum mass, the
  largest factor in the Note's scan). The nominal run always uses minimum masses.
- Mass from radius: the archive already fills missing masses with the Chen & Kipping (2017) relation
  (`pl_bmassprov = "M-R relationship"`, 44% of planets in multi-planet systems on 2026-09-28); these are
  flagged "estimated". For the few rows with no mass at all, and for YAML files, exostab inverts the same
  relation for radii below 11.3 R⊕ and refuses above (the relation is degenerate there; the archive itself
  computes no mass between 11.1 and 14.3 R⊕).
- Circumbinary systems (`cb_flag`) are rejected; companion stars (`sy_snum > 1`) are ignored with a flag.
- Period missing but semi-major axis present → period from Kepler's third law, "derived".
- Hosts with only one planet row are rejected (`sy_pnum` counts planets around all stars of the system).

On 2026-09-28, 1,044 of the 1,070 hosts with `sy_pnum ≥ 2` can be modelled; 26 are rejected with a stated
reason.

## D12 — Hill indicator (final for v0.1)

- Two planets: the eccentric Gladman (1993) criterion in the form restated by Veras & Armitage (2004, Eqs.
  2.5 and 2.8) and Giuppone et al. (2013, Eq. 3), with μ_i = m_i/M_* and without the next-order mass term.
  It is algebraically the Petit et al. (2018) Hill criterion (tested). Failing it gives "unstable" for the
  Hill indicator ("close encounters not excluded"), with the note that resonances can protect a pair.
- Mutual Hill radius ((m_1+m_2)/3M_*)^{1/3} (a_1+a_2)/2 (Chambers et al. 1996; Pu & Wu 2015). In these units
  the circular Gladman limit is 3.462 for two 1e-5 M☉ planets. (The Research Note's notebook quotes 3.35
  for the same case: that is the lowest-order criterion normalised to a_1, converted to mean-a Hill radii.
  The two differ at order μ^{1/3}; neither changes the Note's conclusions.)
- Three or more planets: heuristic. "Unstable" if any adjacent pair fails the two-planet criterion or has
  crossing orbits; "stable" only if every adjacent pair is ≥ 12 mutual Hill radii apart; otherwise
  "marginal". Pu & Wu (2015): about 10 for circular coplanar orbits and about 12 for e ≈ 0.02 to survive
  1 Gyr; Obertas et al. (2017) find 8.5–8.6 for 10^9–10^10 orbits of five Earth-mass planets on circular
  orbits. The conservative 12 is used; improvement tracked in issue #8.

## D13 — Reference verification (2026-09-28)

Every entry in `docs/references.bib` was checked against its Crossref record (articles), arXiv, or DataCite
(the archive's dataset DOIs); raw responses were kept locally. Formulas were copied from the arXiv LaTeX
sources (Laskar & Petit 2017; Petit et al. 2017, 2018; Chen & Kipping 2017; Rivera et al. 2010; Winn 2010)
and cross-checked numerically in the tests. Differences from the brief:

- Cincotta & Simó (2000)'s title is "Simple tools to study global dynamics in non-axisymmetric galactic
  potentials – I"; Tamayo et al. (2020)'s is "Predicting the long-term stability of compact multiplanet
  systems"; Winn (2010)'s chapter is "Transits and Occultations".
- The archive now asks to cite Christiansen et al. (2025, PSJ 6, 186), which replaces Akeson et al. (2013).
- Not verifiable from open sources: Gladman (1993), Chambers et al. (1996), Cincotta & Simó (2000) and
  Wisdom (2015) are not on arXiv. Their bibliographic data are verified; statements attributed to them in
  the docs rely on the restatements cited next to them.

## D14 — AMD indicator (final for v0.1)

- β = C/(Λ' C_c) for every adjacent pair, with the total AMD C of the system (Laskar & Petit 2017) and the
  piece-wise critical AMD of Petit et al. (2017) (collision for α < α_R, MMR overlap above; β = ∞ for
  α > α_cir). β_S = C/Λ_1 for the innermost planet and the star.
- Verdicts: "stable" = strongly AMD-stable (all β < 1 and β_S < 1); "unstable" = two-planet system with
  β ≥ 1 and β_H ≥ 1 (Petit et al. 2018); "marginal" otherwise, including weakly AMD-stable systems. The Hill
  form is used only for two planets because Petit et al. (2018) note it does not carry over to tightly
  packed multi-planet systems.

## D15 — Verdict combination (final for v0.1)

- Per indicator: the nominal verdict stands only if ≥ 95% of the draws share it, otherwise "marginal";
  "inconclusive" if the nominal run is, or if > 20% of the draws are.
- Overall: "unstable" only on direct N-body evidence (nominal and ≥ 95% of draws); "inconclusive" if the
  N-body indicator is; "stable" only if all three indicators say stable; "marginal" otherwise. Disagreement
  is never collapsed into a confident verdict.

## D16 — How the brief's validation expectations are tested

- TRAPPIST-1 "stable or marginal, never unstable": overall verdict in {stable, marginal} and N-body verdict
  not unstable, from the archive snapshot. Measured: marginal.
- GJ 876 "stable": the archive has no usable phases for GJ 876 (D9), and with random phases the Laplace
  resonance is destroyed (archive run: 12 of 20 draws have close encounters). The test therefore uses the
  Rivera et al. (2010) coplanar solution with its mean anomalies (`tests/validation/systems/`) and requires
  the **N-body** verdict to be stable (measured: 20/20 draws regular, ⟨Y⟩ = 1.99). The Hill and AMD criteria
  fail for this resonance-protected system, so the overall verdict is "marginal" by design (D15).
- Kepler-11 "stable over the test horizon": the nominal configuration (archive values, phases from the
  transit times) completes 1e4 orbits of b without close encounters and is regular with WHFast and IAS15;
  N-body and overall verdicts are not "unstable". Measured: the Monte Carlo over the archive uncertainties
  gives 10 regular, 8 chaotic and 2 close encounters of 20 draws (the eccentricity errors are large and the
  draws ignore correlations), so the N-body verdict is "marginal". Reported as found.
- Synthetic pair past the Hill limit: overall "unstable" (tested at 2.5 mutual Hill radii).

## D17 — Other deviations and additions (2026-09-28)

- Dependencies: PyYAML added to the core (needed for `--from-file`); no SciPy (a bisection helper
  suffices); pyarrow is an optional `[catalog]` extra for Parquet output.
- CLI options beyond the brief's examples, needed for the tests, the offline demo and speed: `--offline`,
  `--jobs`, `--no-plots`, `--no-ias15`, `--limit` (list), `--max-seconds` (catalog). `sweep --param` accepts
  e, mass (Earth masses), period (days) and omega (degrees).
- Default output folder: `exostab-results/<system>/`; `--out` writes directly into the given folder.
- `catalog build` defaults to 10 draws and a 120 s cap per system; systems over the cap are recorded as
  "timeout" rather than silently shortened.
- The mypy configuration has no fixed `python_version`: recent numpy stubs only type-check for ≥ 3.12,
  and CI runs mypy on every supported version.

## D18 — Archive data issues found (2026-09-28)

- HD 127195: `pl_orblper` = 3.10 and 4.12 "deg". These are the radian values of Figueira et al. (2026,
  Table 2), whose degree label is a typo (noted in the Research Note). Phases are not published in the
  archive, so they are randomized anyway; ω enters only through the apsidal orientation. Worth reporting to
  the archive (account-side action for Mehmet).
- GJ 876: `pl_orbtper` is the osculating epoch for all four planets (D9).
- `pl_bmassprov` takes the value "M-R relationship", which is not in the archive's column documentation.

## D19 — Time-budget mode (2026-09-28, issue #3)

`--budget fast|thorough|<seconds>` (10 s, 120 s) measures this system's WHFast and IAS15 speed with short runs
and picks the most thorough preset (orbits, draws) from (2e3, 8), (5e3, 10), (1e4, 20), (2e4, 30), (5e4, 50),
(1e5, 100) whose estimated wall time fits. The estimate is overhead (1.5 s) + 1.3 × max(total CPU time /
workers, longest single run); 1.3 is the slowdown measured with all cores busy on an Apple M4 Pro. Runs never go
below the cheapest preset (a warning is printed instead). The IAS15 check is now started first because it is
the longest single job. Measured on TRAPPIST-1: "fast" chose (1e4, 20), estimated 8 s, took 7.8 s; "thorough"
chose (1e5, 100), estimated 90 s, took 82 s. Because the choice depends on the machine, `report.json` records the
chosen orbits and draws and the budget; repeating with `--orbits/--draws/--seed` reproduces the run exactly.

## D20 — Close encounters are detected per pair of planets (2026-09-28)

Until now a run stopped when any two bodies came closer than the smallest planetary Hill radius (the Research
Note's rule, a single REBOUND `exit_min_distance`). The full catalog run showed the flaw: in K2-157 the
ultra-short-period Earth-mass planet has a Hill radius of 1e-4 AU, so the two outer giants passed within
0.0085 AU of each other (inside planet d's Hill radius) without stopping the run, and WHFast then lost accuracy
(relative energy error 5%). Now each planet gets a REBOUND collision radius of half its Hill radius, with
"line" collision detection (which also catches passages between two steps) and `collision_resolve = "halt"`.
A close encounter is therefore two planets closer than the mean of their Hill radii. For two similar planets
this is the Note's rule. Effects on the validation set: none, except GJ 876 with random archive phases, where one
formerly "inconclusive" draw is now a close encounter (3 / 5 / 12 instead of 3 / 6 / 10 + 1). Measured cost:
none.

