"""Run every indicator on one system and combine the verdicts."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from .budget import Plan, plan
from .indicators import IndicatorResult, Verdict
from .indicators import amd as amd_indicator
from .indicators import hill as hill_indicator
from .indicators import megno as nbody_indicator
from .indicators import spock as spock_indicator
from .integrate import RunResult
from .models import PhaseKind, Provenance, System
from .report import Overall, Report, build_report
from .sampling import InclinationPrior, Realization, choose_epoch, realizations


@dataclass(frozen=True)
class CheckSettings:
    """User-facing settings of ``exostab check``."""

    orbits: float = 1e4  # N-body run length in orbits of the innermost planet
    draws: int = 20  # Monte Carlo draws within the published uncertainties
    seed: int = 0
    inclination_prior: InclinationPrior = "none"
    ias15_check: bool = True
    dt_fraction: float = 1 / 30
    jobs: int | None = None  # worker processes (None: all cores but one)
    n_samples: int = 400  # time-series samples kept for the plots
    budget_s: float | None = None  # wall-clock budget that chose orbits and draws, if any
    spock_python: str | None = None  # interpreter of a SPOCK environment: adds the optional SPOCK indicator


def settings_for_budget(system: System, budget_s: float, base: CheckSettings) -> tuple[CheckSettings, Plan]:
    """Settings whose run length and number of draws fit a wall-clock budget (see :mod:`exostab.budget`)."""
    nominal = realizations(system, 0, base.seed, base.inclination_prior)[0]
    p = plan(nominal, budget_s, jobs=base.jobs, ias15_check=base.ias15_check)
    return replace(base, orbits=p.orbits, draws=p.draws, budget_s=budget_s), p


@dataclass
class CheckResult:
    report: Report
    realizations: list[Realization]
    runs: list[RunResult]
    ias15: RunResult | None
    extra: dict[str, object] = field(default_factory=dict)


def _join(items: Sequence[str]) -> str:
    """Join words as in prose: a; a and b; a, b and c."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def upper_limit_inputs(system: System) -> list[str]:
    """The inputs of the runs that are only published upper limits, e.g. ``["masses of X b and X c"]``.

    The nominal run uses each limit and the draws are uniform below it (:mod:`exostab.sampling`).
    """
    out = ["stellar mass"] if system.star.mass_msun.provenance is Provenance.UPPER_LIMIT else []
    names: dict[tuple[str, str], list[str]] = {
        ("period", "periods"): [],
        ("mass", "masses"): [],
        ("eccentricity", "eccentricities"): [],
        ("argument of periastron", "arguments of periastron"): [],
        ("orbital phase", "orbital phases"): [],
    }
    for p in system.planets:
        values = (p.period_days, p.mass_earth, p.eccentricity, p.omega_deg, p.phase.value)
        for planets, v in zip(names.values(), values, strict=True):
            if v is not None and v.provenance is Provenance.UPPER_LIMIT:
                planets.append(p.name)
    for (one, many), planets in names.items():
        if planets:
            out.append(f"{one if len(planets) == 1 else many} of {_join(planets)}")
    return out


def overall_verdict(indicators: dict[str, IndicatorResult], *, upper_limits: Sequence[str] = ()) -> Overall:
    """Conservative combination of the per-indicator verdicts.

    * unstable: the direct N-body integration is unstable (close encounters or escapes in the nominal run
      and in at least 95% of the draws), and that evidence does not rest on upper limits;
    * inconclusive: the N-body integration could not be trusted;
    * stable: every indicator says stable (including SPOCK when it is enabled);
    * marginal: everything else, i.e. whenever the indicators disagree or any of them is marginal.

    ``upper_limits`` lists the inputs that are only published upper limits (:func:`upper_limit_inputs`). The
    nominal run uses each limit and the draws are uniform below it, which does not sample a measurement
    uncertainty. A limit on a mass or an eccentricity is the worst case for stability, so a stable result
    still holds; an N-body instability, however, only constrains those values and gives "marginal".
    """
    nb = indicators["nbody"].verdict
    others = {k: v for k, v in indicators.items() if k != "nbody"}
    not_stable = [
        f"{r.title}: {r.verdict.value}" for r in indicators.values() if r.verdict is not Verdict.STABLE
    ]
    d = indicators["nbody"].draws
    limits = _join(upper_limits) if upper_limits else ""
    if nb is Verdict.UNSTABLE:
        found = "Direct integration finds close encounters or escapes for the nominal parameters" + (
            f" and for {d.unstable} of {d.n} draws" if d is not None else ""
        )
        if not upper_limits:
            return Overall(
                verdict=Verdict.UNSTABLE,
                summary=found + (" within the published uncertainties." if d is not None else "."),
                reasons=not_stable,
            )
        return Overall(
            verdict=Verdict.MARGINAL,
            summary=found + f". These runs use values that are only published upper limits ({limits}): the "
            "nominal run takes each limit and the draws are uniform below it, so the instability may come from "
            "values the system does not have. It constrains those values; it does not show that the system is "
            "unstable.",
            reasons=[*not_stable, f"Only upper limits are published for: {limits}."],
        )
    if nb is Verdict.INCONCLUSIVE:
        return Overall(
            verdict=Verdict.INCONCLUSIVE,
            summary="The N-body integrations could not be trusted (see the N-body notes), so no overall verdict "
            "is given.",
            reasons=not_stable,
        )
    if nb is Verdict.STABLE and all(r.verdict is Verdict.STABLE for r in others.values()):
        return Overall(
            verdict=Verdict.STABLE,
            summary="All indicators agree: no sign of instability. The N-body test covers only the integrated "
            "time span, not the age of the system.",
            reasons=[],
        )
    if nb is Verdict.STABLE:
        summary = (
            "The N-body integration shows regular motion, but the analytic criteria cannot guarantee "
            "stability. This is typical of systems protected by mean-motion resonances or of compact systems "
            "whose long-term stability is uncertain."
        )
    else:
        summary = (
            "Mixed evidence: part of the parameter range allowed by the uncertainties is chaotic or unstable, "
            "or the indicators disagree."
        )
    return Overall(verdict=Verdict.MARGINAL, summary=summary, reasons=not_stable)


def check_system(system: System, settings: CheckSettings, *, command: str | None = None) -> CheckResult:
    """Run the Hill, AMD and N-body indicators on ``system``."""
    t0 = time.perf_counter()
    reals = realizations(system, settings.draws, settings.seed, settings.inclination_prior)
    nominal, draws = reals[0], reals[1:]
    hill = hill_indicator.evaluate(nominal, draws)
    amd = amd_indicator.evaluate(nominal, draws)
    nb_settings = nbody_indicator.NBodySettings(
        orbits=settings.orbits,
        dt_fraction=settings.dt_fraction,
        ias15_check=settings.ias15_check,
        n_samples=settings.n_samples,
        jobs=settings.jobs,
    )
    runs, ias15 = nbody_indicator.integrate_all(reals, nb_settings, settings.seed)
    random_phases = [p.name for p in system.planets if p.phase.kind is PhaseKind.RANDOM]
    nbody = nbody_indicator.evaluate(runs, ias15, random_phases=random_phases)
    indicators = {"hill": hill, "amd": amd, "nbody": nbody}
    if settings.spock_python and len(nominal.bodies) >= 3:
        indicators["spock"] = spock_indicator.evaluate(nominal, draws, settings.spock_python)
    report = build_report(
        system=system,
        settings=settings,
        epoch_jd=choose_epoch(system),
        nominal=nominal,
        nominal_run=runs[0],
        indicators=indicators,
        overall=overall_verdict(indicators, upper_limits=upper_limit_inputs(system)),
        runtime_s=time.perf_counter() - t0,
        command=command,
    )
    return CheckResult(report=report, realizations=reals, runs=runs, ias15=ias15)
