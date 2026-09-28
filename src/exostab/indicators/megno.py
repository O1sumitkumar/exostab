"""N-body indicator: direct integration with the MEGNO chaos indicator.

Each run (the nominal parameters and every Monte Carlo draw) is integrated with WHFast for
``orbits`` orbits of the innermost planet and classified as

* ``regular`` (verdict stable): no close encounter or escape, and MEGNO <Y> below ``MEGNO_CHAOTIC``;
* ``chaotic`` (verdict marginal): no close encounter or escape, but <Y> at or above ``MEGNO_CHAOTIC``;
* ``unstable``: a close encounter or an escape happened;
* ``inconclusive``: the relative energy error exceeded ``ENERGY_ERROR_MAX`` (and nothing physical
  stopped the run), or the integration failed.

For quasi-periodic (regular) motion <Y> tends to 2; for chaotic motion it grows linearly with time
(Cincotta & Simo 2000). The threshold and the run length are finite, so a "regular" run means "no
chaos detected within this horizon", never "stable for billions of years".

The nominal run is repeated with IAS15. If the two integrators disagree, the indicator cannot be
"stable". If the outermost planet completes fewer than ``MIN_OUTER_ORBITS`` orbits, the horizon is too
short to judge it and the indicator cannot be "stable" either.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ..integrate import RunConfig, RunResult, run
from ..sampling import Realization
from ..units import format_count, format_years
from . import DrawStats, IndicatorResult, Verdict, combine

# <Y> at or above this value counts as chaotic. Same threshold as the HD 127195 Research Note;
# see DECISIONS.md (D8) for its uncertainty.
MEGNO_CHAOTIC = 2.2
# Runs whose maximum relative energy error exceeds this are inconclusive (DECISIONS.md, D8).
ENERGY_ERROR_MAX = 1e-5
# The outermost planet must complete at least this many orbits for a "stable" verdict.
MIN_OUTER_ORBITS = 100

REFERENCES = [
    "rein2012",
    "rein2015whfast",
    "rein2015ias15",
    "rein2016",
    "cincotta2000",
    "cincotta2003",
    "wisdom2015",
    "hadden2018",
]

RunClass = Literal["regular", "chaotic", "unstable", "inconclusive"]
_TO_VERDICT: dict[str, Verdict] = {
    "regular": Verdict.STABLE,
    "chaotic": Verdict.MARGINAL,
    "unstable": Verdict.UNSTABLE,
    "inconclusive": Verdict.INCONCLUSIVE,
}


@dataclass(frozen=True)
class NBodySettings:
    orbits: float = 1e4
    dt_fraction: float = 1 / 30
    ias15_check: bool = True
    n_samples: int = 400  # time-series samples kept for the nominal runs (plots)
    jobs: int | None = None  # worker processes; None: all cores but one


def classify_run(r: RunResult) -> RunClass:
    if r.status in ("encounter", "escape"):
        return "unstable"
    if r.status == "error" or r.megno is None or not np.isfinite(r.megno):
        return "inconclusive"
    if r.energy_error > ENERGY_ERROR_MAX:
        return "inconclusive"
    return "chaotic" if r.megno >= MEGNO_CHAOTIC else "regular"


def _run(job: tuple[Realization, RunConfig]) -> RunResult:
    return run(*job)


def run_many(jobs: Sequence[tuple[Realization, RunConfig]], n_workers: int | None) -> list[RunResult]:
    """Run integrations, in parallel worker processes when more than one worker is allowed."""
    if n_workers is None:
        n_workers = max(1, (os.cpu_count() or 2) - 1)
    n_workers = min(n_workers, len(jobs))
    if n_workers <= 1:
        return [_run(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        return list(pool.map(_run, jobs, chunksize=1))


def megno_seed(seed: int, k: int) -> int:
    """Seed for the MEGNO shadow-particle initialisation of run ``k``, derived from the user's seed."""
    return int(np.random.SeedSequence([seed, k]).generate_state(1)[0] % (2**31 - 1))


def integrate_all(
    reals: Sequence[Realization], settings: NBodySettings, seed: int
) -> tuple[list[RunResult], RunResult | None]:
    """WHFast runs for every realization (nominal first) plus the IAS15 check of the nominal run."""
    base = RunConfig(n_orbits=settings.orbits, integrator="whfast", dt_fraction=settings.dt_fraction)
    jobs: list[tuple[Realization, RunConfig]] = []
    for k, r in enumerate(reals):
        samples = settings.n_samples if k == 0 else 0
        jobs.append((r, replace(base, megno_seed=megno_seed(seed, k), n_samples=samples)))
    if settings.ias15_check:
        # IAS15 is the slowest single run (5-20 times WHFast), so it is started first: the pool then
        # works through the WHFast runs while it goes on, instead of waiting for it at the end.
        jobs.insert(0, (reals[0], replace(jobs[0][1], integrator="ias15")))
    results = run_many(jobs, settings.jobs)
    ias15 = results.pop(0) if settings.ias15_check else None
    return results, ias15


def evaluate(
    results: Sequence[RunResult], ias15: RunResult | None, *, random_phases: Sequence[str] = ()
) -> IndicatorResult:
    """N-body verdict from the nominal run (``results[0]``), the draws and the IAS15 check.

    ``random_phases`` names the planets whose orbital phase is unknown and drawn at random.
    """
    nominal, draws = results[0], list(results[1:])
    c_nom = classify_run(nominal)
    c_draws = [classify_run(r) for r in draws]
    v_nom = _TO_VERDICT[c_nom]
    v_draws = [_TO_VERDICT[c] for c in c_draws]
    verdict = combine(v_nom, v_draws)
    notes: list[str] = []
    if verdict is not v_nom and v_nom is not Verdict.INCONCLUSIVE:
        notes.append(f"The nominal run is '{c_nom}', but the draws disagree.")
    c_ias = classify_run(ias15) if ias15 is not None else None
    if c_ias is not None and c_ias != c_nom:
        notes.append(f"WHFast and IAS15 disagree on the nominal run ({c_nom} vs {c_ias}).")
        if verdict is Verdict.STABLE:
            verdict = Verdict.MARGINAL
    if nominal.status == "completed" and nominal.n_orbits_outermost < MIN_OUTER_ORBITS:
        notes.append(
            f"The outermost planet completes only {nominal.n_orbits_outermost:.0f} orbits in this run, "
            f"fewer than {MIN_OUTER_ORBITS}; increase --orbits for a meaningful test of the outer planets."
        )
        if verdict is Verdict.STABLE:
            verdict = Verdict.MARGINAL
    if random_phases:
        notes.append(
            f"The orbital phases of {', '.join(random_phases)} are not published and are drawn at random in every "
            "run (the nominal run included). A system protected by a mean-motion resonance can look chaotic or "
            "unstable for random phases; supply measured phases with --from-file to test the real configuration."
        )
    for r, c in zip([nominal, *draws], [c_nom, *c_draws], strict=True):
        if c == "inconclusive" and r.status != "error":
            notes.append(
                f"{r.label}: relative energy error {r.energy_error:.1e} exceeds {ENERGY_ERROR_MAX:.0e}; "
                "no verdict for this run."
            )
            break
    years = nominal.t_target
    counts = {c: c_draws.count(c) for c in ("regular", "chaotic", "unstable", "inconclusive")}
    planned = nominal.t_target / (nominal.t_end / nominal.n_orbits_innermost) if nominal.t_end > 0 else 0.0
    if c_nom == "unstable":
        what = "close encounter" if nominal.status == "encounter" else "escape"
        summary = (
            f"Nominal run: {what} after {format_years(nominal.t_end)} "
            f"({format_count(nominal.n_orbits_innermost)} of {format_count(planned)} planned inner orbits)"
        )
    else:
        nom_text = {
            "regular": f"regular (<Y> = {nominal.megno:.2f})" if nominal.megno is not None else "regular",
            "chaotic": f"chaotic (<Y> = {nominal.megno:.2f})" if nominal.megno is not None else "chaotic",
            "inconclusive": "inconclusive",
        }[c_nom]
        summary = (
            f"Nominal run {nom_text} over {format_years(years)} "
            f"({format_count(nominal.n_orbits_innermost)} inner orbits)"
        )
    if draws:
        summary += (
            f"; draws: {counts['regular']} regular, {counts['chaotic']} chaotic, "
            f"{counts['unstable']} close encounter/escape"
            + (f", {counts['inconclusive']} inconclusive" if counts["inconclusive"] else "")
            + f" of {len(draws)}."
        )
    else:
        summary += "."
    details = {
        "megno_threshold": MEGNO_CHAOTIC,
        "energy_error_max": ENERGY_ERROR_MAX,
        "t_target_yr": years,
        "nominal": _run_summary(nominal, c_nom),
        "ias15": _run_summary(ias15, c_ias) if ias15 is not None and c_ias is not None else None,
        "draws": [_run_summary(r, c) for r, c in zip(draws, c_draws, strict=True)],
        "classification_counts": counts,
    }
    return IndicatorResult(
        name="nbody",
        title="N-body + MEGNO",
        verdict=verdict,
        nominal_verdict=v_nom,
        summary=summary,
        draws=DrawStats.from_verdicts(v_draws) if draws else None,
        details=details,
        notes=notes,
        references=REFERENCES,
    )


def _run_summary(r: RunResult, c: str) -> dict[str, object]:
    return {
        "label": r.label,
        "integrator": r.integrator,
        "classification": c,
        "status": r.status,
        "megno": r.megno,
        "lyapunov_per_yr": r.lyapunov,
        "energy_error": r.energy_error,
        "dt_yr": r.dt,
        "t_end_yr": r.t_end,
        "n_orbits_innermost": r.n_orbits_innermost,
        "n_orbits_outermost": r.n_orbits_outermost,
        "encounter_distance_au": r.encounter_distance,
        "walltime_s": r.walltime,
        "error": r.error,
    }
