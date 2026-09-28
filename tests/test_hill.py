import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from conftest import hill_limit_ratio, two_planet_system
from exostab.indicators import Verdict, amd, hill
from exostab.sampling import Body, Realization, realizations

masses = st.floats(1e-8, 1e-3)


def real_of(
    ms: list[float], periods: list[float], es: list[float] | None = None, m_star: float = 1.0
) -> Realization:
    es = es or [0.0] * len(ms)
    return Realization(
        label="x",
        m_star=m_star,
        bodies=tuple(Body(f"p{k}", m, P, e, 0.0, 0.0) for k, (m, P, e) in enumerate(zip(ms, periods, es))),
    )


def test_circular_limit_tends_to_two_sqrt_three() -> None:
    assert hill.gladman_critical_separation(1e-10, 1e-10, 1.0) == pytest.approx(2 * math.sqrt(3), rel=1e-3)


@given(m1=masses, m2=masses, ratio=st.floats(1.01, 3.0), m_star=st.floats(0.08, 3.0))
def test_hill_spacing_is_symmetric_in_the_two_masses(
    m1: float, m2: float, ratio: float, m_star: float
) -> None:
    a1, a2 = 1.0, ratio
    assert hill.separation_in_hill_radii(m1, m2, a1, a2, m_star) == pytest.approx(
        hill.separation_in_hill_radii(m2, m1, a1, a2, m_star)
    )
    assert hill.mutual_hill_radius(m1, m2, a1, a2, m_star) > 0


@given(m1=masses, m2=masses, alpha=st.floats(0.3, 0.999), e1=st.floats(0, 0.5), e2=st.floats(0, 0.5))
def test_gladman_equals_petit_2018_amd_form(m1: float, m2: float, alpha: float, e1: float, e2: float) -> None:
    """Gladman's criterion and the AMD form of Petit et al. (2018) are the same inequality (to O(eps))."""
    gm = hill.gladman_margin(m1, m2, alpha, 1.0, e1, e2, 1.0)
    gamma, eps = m1 / m2, m1 + m2
    rel = amd.relative_amd(e1, e2, alpha, gamma)
    ch = amd.critical_amd_hill(alpha, gamma, eps)
    if abs(gm) > 1e-6 and abs(rel - ch) > 1e-6 * max(1.0, abs(ch)):
        assert (gm > 0) == (rel < ch)


@given(e=st.floats(0, 0.3), de=st.floats(0.001, 0.2))
def test_gladman_margin_decreases_with_eccentricity(e: float, de: float) -> None:
    m = 1e-5
    lo = hill.gladman_margin(m, m, 1.0, 1.2, e, e, 1.0)
    hi = hill.gladman_margin(m, m, 1.0, 1.2, min(e + de, 0.99), min(e + de, 0.99), 1.0)
    assert hi < lo


def test_two_planet_verdicts() -> None:
    m = 3e-5
    limit = hill_limit_ratio(m)
    wide = real_of([m, m], [1.0, 1.3 * limit])
    close = real_of([m, m], [1.0, 0.95 * limit])
    assert hill.classify(wide) is Verdict.STABLE
    assert hill.classify(close) is Verdict.UNSTABLE
    crossing = real_of([m, m], [1.0, 3.0], es=[0.6, 0.6])
    assert hill.pair_table(crossing)[0]["orbits_cross"]
    assert hill.classify(crossing) is Verdict.UNSTABLE


def test_multi_planet_heuristic() -> None:
    m = 3e-6
    spaced = real_of([m] * 3, [1.0, 2.0, 4.0])
    tight = real_of([m] * 3, [1.0, 1.2, 1.44])
    assert min(r["separation_hill"] for r in hill.pair_table(spaced)) > hill.DELTA_MULTI
    assert hill.classify(spaced) is Verdict.STABLE
    assert hill.classify(tight) is Verdict.MARGINAL


def test_evaluate_summaries_and_draw_disagreement() -> None:
    res = hill.evaluate(real_of([3e-5, 3e-5], [1.0, 2.0]), [])
    assert res.verdict is Verdict.STABLE and "Hill stable" in res.summary and res.draws is None
    s = two_planet_system(period_ratio=1.2, m_earth=(10.0, 10.0), err=True)
    reals = realizations(s, 20, seed=0)
    res = hill.evaluate(reals[0], reals[1:])
    assert res.name == "hill" and res.draws is not None and res.draws.n == 20
    res = hill.evaluate(real_of([3e-5, 3e-5], [1.0, 1.01]), [])
    assert res.verdict is Verdict.UNSTABLE and "Not Hill stable" in res.summary
    res = hill.evaluate(real_of([3e-6] * 3, [1.0, 2.0, 4.0]), [real_of([3e-6] * 3, [1.0, 1.2, 1.44])] * 5)
    assert res.nominal_verdict is Verdict.STABLE
    assert res.verdict is Verdict.MARGINAL and any("draws disagree" in n for n in res.notes)
    assert "heuristic" in " ".join(res.notes)
    res = hill.evaluate(real_of([3e-6] * 3, [1.0, 2.0, 4.0]), [])
    assert res.verdict is Verdict.STABLE and "at least" in res.summary
