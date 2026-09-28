# Data and assumptions

## Source

Parameters come from the NASA Exoplanet Archive's **Planetary Systems Composite Parameters** table (`pscomppars`,
doi:[10.26133/NEA13](https://doi.org/10.26133/NEA13)), queried through its Table Access Protocol (TAP) service with
astroquery. exostab downloads all planets in systems with two or more planets (`sy_pnum >= 2`, about 2,700 rows)
once, stores them in your user cache folder, and reuses the copy until you pass `--refresh`. Every report records:

- the table name and service URL;
- when the table was downloaded (`data.retrieved_utc` in `report.json`);
- the archive row of every planet (`pl_name`);
- the publication behind every value (`reference`, `reference_url`).

`--offline` (or `EXOSTAB_OFFLINE=1`) uses the snapshot of 22 well-known systems bundled with the package. The
snapshot is also used, with a warning in the report, if the archive cannot be reached and there is no cache.

> This research has made use of the NASA Exoplanet Archive, which is operated by the California Institute of
> Technology, under contract with the National Aeronautics and Space Administration under the Exoplanet
> Exploration Program.

Please also cite Christiansen et al. (2025, PSJ 6, 186) and the table DOI with the access date, and the
publications behind the values you use. Their references are in `report.json`.

### A caution about the composite table

The archive picks each parameter of a planet separately: the value from the planet's default publication if it
exists, otherwise the most precise one. One row can therefore combine a period from one paper, an eccentricity from
another and a transit time from a third. The archive's documentation calls the table "not necessarily
self-consistent". This matters most for orbital phases (below).

## Completion rules

Every rule that fires adds a line to the report card and an entry to `system.flags` in `report.json`.

| Missing or special value | What exostab does | Flag |
|---|---|---|
| Eccentricity | 0 | `eccentricity_assumed_zero` |
| Eccentricity or mass given as an upper limit | the nominal run uses the limit (the worst case); draws are uniform between 0 and the limit | `eccentricity_upper_limit`, `mass_upper_limit` |
| Argument of periastron ω | drawn uniformly in [0°, 360°) for every run | `omega_randomized` |
| Longitude of the ascending node Ω | not used: in a coplanar system only ϖ = Ω + ω matters, and randomizing ω covers it | (part of `coplanar_assumed`) |
| Inclinations | all orbits in one plane; sky-plane inclinations do not give the angles between orbits | `coplanar_assumed` |
| Mass is m sin i (`pl_bmassprov = Msini`) | used as the mass (sin i = 1); `--inclination-prior isotropic` draws one inclination per draw (cos i uniform, sin i ≥ 0.1) and divides the minimum masses by sin i | `minimum_mass` |
| Mass estimated by the archive from the radius | used, flagged "estimated" | `mass_estimated_by_archive` |
| No mass at all, radius known | Chen & Kipping (2017) relation, for radii up to 11.3 R⊕; refused above, where the relation gives no unique mass | `mass_from_radius_chen_kipping` |
| No period, semi-major axis known | Kepler's third law | `period_from_semimajor_axis` |
| Several stars in the system | only the host star is modelled | `companion_stars_ignored` |
| Planet flagged controversial | kept, flagged | `controversial_planet` |
| Circumbinary planets, or no mass and no radius, or no period and no semi-major axis | the system is rejected with the reason | — |

### Orbital phases

Where each planet is along its orbit at the start of the integration matters a lot for resonant systems.

1. **Transiting planets:** the phase follows from the mid-transit time. At mid-transit the true anomaly is
   f = 90° − ω (Winn 2010). It is propagated to a common epoch with the period, and the uncertainties of both
   enter every draw.
2. **Non-transiting planets with a time of conjunction or of periastron:** used only if it comes from the same
   publication as the period. A phase from one orbital solution combined with a period from another would be
   meaningless. A time of periastron that several planets share is treated as an epoch, not a periastron time.
   This happens for GJ 876.
3. **Otherwise:** the phase is drawn at random for every run, the nominal run included, and the report says so.

### Monte Carlo draws

Each draw takes every value from a *split normal* distribution: one Gaussian half with the upper error bar and one
with the lower. Values without published errors are held fixed. Negative eccentricities are set to 0 and
eccentricities are capped at 0.95. Masses, periods and the stellar mass are redrawn until positive. Draws are
independent: correlations in the published posteriors are ignored, which usually widens the spread of outcomes.
The same `--seed` always gives the same draws.

## Your own parameters

`exostab check --from-file system.yaml` reads a YAML file (see `examples/two_planet.yaml`). The units are in the
key names (`period_days`, `mass_earth` / `mass_jupiter` / `mass_msun`, `omega_deg`, `mean_longitude_deg`,
`transit_time_jd`, …). The same completion rules apply to anything left out. `examples/hd127195_note.yaml`
contains the inputs of the HD 127195 Research Note.
