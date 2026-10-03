"""The N-body/MEGNO indicator, the verdict combination rules and the overall verdict."""

import math
from dataclasses import replace

import pytest

from conftest import V, two_planet_system
from exostab.analysis import CheckSettings, check_system, overall_verdict, upper_limit_inputs
from exostab.indicators import AGREEMENT, DrawStats, IndicatorResult, Verdict, combine
from exostab.indicators import megno as nb
from exostab.integrate import RunResult
from exostab.models import Provenance
from exostab.sampling import realizations

S, M, U, INC = Verdict.STABLE, Verdict.MARGINAL, Verdict.UNSTABLE, Verdict.INCONCLUSIVE


def result(**kw: object) -> RunResult:
    base: dict[str, object] = {
        "label": "nominal",
        "integrator": "whfast",
        "dt": 0.001,
        "t_target": 100.0,
        "t_end": 100.0,
        "status": "completed",
        "megno": 2.0,
        "lyapunov": 0.0,
        "energy_error": 1e-9,
        "walltime": 0.1,
        "encounter_distance": 0.01,
        "n_orbits_innermost": 1e4,
        "n_orbits_outermost": 1e3,
    }
    base.update(kw)
    return RunResult(**base)  # type: ignore[arg-type]


# ------------------------------------------------------------------------------------------ combination rules


def test_combine_rules() -> None:
    assert combine(S, []) is S
    assert combine(S, [S] * 20) is S
    assert combine(S, [S] * 19 + [M]) is S  # 95% agreement
    assert combine(S, [S] * 18 + [M, M]) is M
    assert combine(U, [U] * 20) is U
    assert combine(INC, [S] * 20) is INC
    assert combine(S, [S] * 15 + [INC] * 5) is INC  # more than 20% inconclusive
    assert AGREEMENT == 0.95


def test_draw_stats() -> None:
    d = DrawStats.from_verdicts([S, S, M, U, INC])
    assert (d.n, d.stable, d.marginal, d.unstable, d.inconclusive) == (5, 2, 1, 1, 1)
    assert d.count(M) == 1


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({}, "regular"),
        ({"megno": 3.0}, "chaotic"),
        ({"megno": nb.MEGNO_CHAOTIC}, "chaotic"),
        ({"status": "encounter"}, "unstable"),
        ({"status": "escape", "energy_error": 1.0}, "unstable"),
        ({"energy_error": 1e-3}, "inconclusive"),
        ({"status": "error"}, "inconclusive"),
        ({"megno": math.nan}, "inconclusive"),
        ({"megno": None}, "inconclusive"),
    ],
)
def test_classify_run(kw: dict[str, object], expected: str) -> None:
    assert nb.classify_run(result(**kw)) == expected


def test_evaluate_counts_and_notes() -> None:
    runs = [result()] + [result(label=f"draw {k}") for k in range(19)] + [result(label="draw 20", megno=4.0)]
    ind = nb.evaluate(runs, result(integrator="ias15"))
    assert ind.verdict is S and ind.draws is not None and ind.draws.marginal == 1
    assert ind.details["classification_counts"] == {
        "regular": 19,
        "chaotic": 1,
        "unstable": 0,
        "inconclusive": 0,
    }
    assert "19 regular, 1 chaotic" in ind.summary
    ind = nb.evaluate(runs, result(integrator="ias15", status="encounter"))
    assert ind.verdict is M and any("disagree" in n for n in ind.notes)
    ind = nb.evaluate([result(n_orbits_outermost=20)], None)
    assert ind.verdict is M and any("fewer than" in n for n in ind.notes)
    ind = nb.evaluate([result(energy_error=1e-3)], None)
    assert ind.verdict is INC and any("energy error" in n for n in ind.notes)
    ind = nb.evaluate([result(status="encounter", t_end=5.0)], None, random_phases=["X b"])
    assert ind.verdict is U and "close encounter after 5 yr" in ind.summary
    assert any("X b" in n and "random" in n for n in ind.notes)
    ind = nb.evaluate([result()] + [result(megno=5.0)] * 5, None)
    assert ind.verdict is M and any("draws disagree" in n for n in ind.notes)


def test_megno_seed_is_deterministic_and_distinct() -> None:
    assert nb.megno_seed(3, 1) == nb.megno_seed(3, 1)
    assert len({nb.megno_seed(3, k) for k in range(50)}) == 50


def test_integrate_all_serial_and_parallel_agree() -> None:
    reals = realizations(two_planet_system(err=True), 3, seed=2)
    settings = nb.NBodySettings(orbits=200, n_samples=5, jobs=1)
    serial, ias = nb.integrate_all(reals, settings, seed=2)
    parallel, ias2 = nb.integrate_all(reals, replace(settings, jobs=2), seed=2)
    assert [r.megno for r in serial] == [r.megno for r in parallel]
    assert ias is not None and ias2 is not None and ias.integrator == "ias15"
    assert serial[0].series["t"] and not serial[1].series
    none, no_ias = nb.integrate_all(reals[:1], replace(settings, ias15_check=False), seed=2)
    assert no_ias is None and len(none) == 1


# ------------------------------------------------------------------------------------------ overall verdict


def ind(name: str, v: Verdict, draws: list[Verdict] | None = None) -> IndicatorResult:
    """An indicator result whose draws (20 sharing its verdict by default; [] for none) are as given."""
    d = [v] * 20 if draws is None else draws
    stats = DrawStats.from_verdicts(d) if d else None
    return IndicatorResult(name=name, title=name, verdict=v, nominal_verdict=v, summary="", draws=stats)


def nbody_ind(regular: int, encounters: int = 0, chaotic: int = 0, **nominal: object) -> IndicatorResult:
    """N-body result from a nominal run (``nominal`` overrides), the given draws and an agreeing IAS15 run."""
    runs = [result(**nominal)]
    runs += [result(label="draw")] * regular + [result(label="draw", megno=5.0)] * chaotic
    runs += [result(label="draw", status="encounter", t_end=5.0)] * encounters
    return nb.evaluate(runs, result(**{**nominal, "integrator": "ias15"}))


@pytest.mark.parametrize(
    ("hill", "amd", "nbody", "expected"),
    [
        (S, S, S, S),
        (U, M, S, M),  # resonance-protected, like GJ 876
        (S, S, M, M),
        (S, S, U, U),
        (U, U, U, U),
        (S, S, INC, INC),
        (U, S, INC, INC),
        (M, S, S, M),
    ],
)
def test_overall_verdict_is_conservative(
    hill: Verdict, amd: Verdict, nbody: Verdict, expected: Verdict
) -> None:
    o = overall_verdict({"hill": ind("hill", hill), "amd": ind("amd", amd), "nbody": ind("nbody", nbody)})
    assert o.verdict is expected
    if expected is not S:
        assert o.reasons


def test_overall_unstable_states_the_draw_counts() -> None:
    o = overall_verdict(
        {"hill": ind("hill", U), "amd": ind("amd", U), "nbody": nbody_ind(1, 19, status="encounter")}
    )
    assert o.verdict is U
    assert "for the nominal parameters and for 19 of 20 draws within the published uncertainties" in o.summary


def test_unstable_nbody_resting_on_upper_limits_is_not_overall_unstable() -> None:
    """HD 215152 was "unstable" with its masses set to astrometric upper limits about 300 x m sin i."""
    inds = {"hill": ind("hill", U), "amd": ind("amd", M), "nbody": nbody_ind(0, 20, status="encounter")}
    o = overall_verdict(inds, upper_limits=["masses of X b and X c"])
    assert o.verdict is M
    assert "(masses of X b and X c)" in o.summary and "does not show that the system is unstable" in o.summary
    assert "within the published uncertainties" not in o.summary
    assert "Only upper limits are published for: masses of X b and X c." in o.reasons
    # A limit is the worst case for stability, so a stable result at the limits stands.
    stable = {"hill": ind("hill", S), "amd": ind("amd", S), "nbody": nbody_ind(20)}
    assert overall_verdict(stable, upper_limits=["mass of X b"]).verdict is S


def test_upper_limit_inputs() -> None:
    s = two_planet_system()
    assert upper_limit_inputs(s) == []
    ul = Provenance.UPPER_LIMIT
    b, c = s.planets
    s = s.model_copy(
        update={
            "star": s.star.model_copy(update={"mass_msun": V(1.0, provenance=ul)}),
            "planets": (
                b.model_copy(
                    update={"mass_earth": V(10.0, provenance=ul), "eccentricity": V(0.1, provenance=ul)}
                ),
                c.model_copy(update={"mass_earth": V(10.0, provenance=ul)}),
            ),
        }
    )
    assert upper_limit_inputs(s) == ["stellar mass", "masses of Test b and Test c", "eccentricity of Test b"]


def test_check_system_with_upper_limit_masses_is_never_unstable() -> None:
    """Two planets 5% apart in period with masses below 1000 Earth masses: every run has a close encounter."""
    s = two_planet_system(period_ratio=1.05, m_earth=(1000.0, 1000.0))
    planets = tuple(
        p.model_copy(update={"mass_earth": V(1000.0, provenance=Provenance.UPPER_LIMIT)}) for p in s.planets
    )
    s = s.model_copy(update={"planets": planets})
    res = check_system(s, CheckSettings(orbits=300, draws=3, seed=0, jobs=1, n_samples=5, ias15_check=False))
    assert res.report.indicators["nbody"].verdict is U
    assert res.report.overall.verdict is M
    assert "masses of Test b and Test c" in res.report.overall.summary


def test_no_draws_never_give_a_confident_overall_verdict() -> None:
    """With --draws 0 nothing was tested against the uncertainties."""
    o = overall_verdict({"hill": ind("hill", S, []), "amd": ind("amd", S, []), "nbody": nbody_ind(0)})
    assert o.verdict is M and "--draws 0" in o.summary and o.reasons
    o = overall_verdict(
        {"hill": ind("hill", U, []), "amd": ind("amd", U, []), "nbody": nbody_ind(0, status="encounter")}
    )
    assert o.verdict is M and "--draws 0" in o.summary
    assert "draws within" not in o.summary and "almost all draws" not in o.summary
    o = overall_verdict(
        {"hill": ind("hill", S, []), "amd": ind("amd", S, []), "nbody": nbody_ind(0, energy_error=1e-3)}
    )
    assert o.verdict is INC  # an untrustworthy integration stays inconclusive
    res = check_system(two_planet_system(err=True), CheckSettings(orbits=300, draws=0, jobs=1, n_samples=5))
    assert res.report.indicators["nbody"].verdict is S and res.report.overall.verdict is M


def test_check_system_end_to_end_small() -> None:
    s = two_planet_system(err=True)
    res = check_system(s, CheckSettings(orbits=300, draws=3, seed=1, jobs=1, n_samples=10), command="test")
    rep = res.report
    assert set(rep.indicators) == {"hill", "amd", "nbody"}
    assert rep.overall.verdict is S
    assert rep.settings.seed == 1 and rep.settings.draws == 3 and rep.command == "test"
    assert rep.nominal.bodies[0].period_days == pytest.approx(100.0)
    assert len(res.runs) == 4 and res.ias15 is not None
