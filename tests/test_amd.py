import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from exostab._numerics import bisect
from exostab.indicators import Verdict, amd
from exostab.sampling import Body, Realization

alphas = st.floats(0.05, 0.98)
gammas = st.floats(0.01, 100.0)
ecc = st.floats(0.0, 0.95)


def real_of(ms: list[float], periods: list[float], es: list[float], m_star: float = 1.0) -> Realization:
    return Realization(
        label="x",
        m_star=m_star,
        bodies=tuple(Body(f"p{k}", m, P, e, 0.0, 0.0) for k, (m, P, e) in enumerate(zip(ms, periods, es))),
    )


def test_reproduces_hd127195_research_note_amd_limits() -> None:
    """paper_analysis.py of the HD 127195 Research Note: AMD limits 0.148 / 0.215 / 0.203 (N11)."""
    al, ga = 1.5659307764265669 ** (-2 / 3), 0.67 / 0.65
    cc = amd.critical_amd_collision(al, ga)
    e_eq = bisect(lambda e: amd.relative_amd(e, e, al, ga) - cc, 0, 0.9)
    e_b = bisect(lambda e: amd.relative_amd(e, 0, al, ga) - cc, 0, 0.9)
    e_c = bisect(lambda e: amd.relative_amd(0, e, al, ga) - cc, 0, 0.9)
    assert (e_eq, e_b, e_c) == pytest.approx((0.1478176, 0.2148879, 0.2025903), abs=1e-6)


@given(e1=ecc, e2=ecc, alpha=alphas, gamma=gammas)
def test_amd_is_non_negative_and_zero_only_for_circular(
    e1: float, e2: float, alpha: float, gamma: float
) -> None:
    c = amd.relative_amd(e1, e2, alpha, gamma)
    assert c >= 0
    if e1 == 0 and e2 == 0:
        assert c == 0


@given(alpha=alphas, gamma=gammas)
def test_critical_eccentricity_lies_on_collision_line(alpha: float, gamma: float) -> None:
    e_c = amd.critical_eccentricity(alpha, gamma)
    assert 0 < e_c < min(1.0, 1 / alpha - 1)
    e_out = 1 - alpha - alpha * e_c
    assert 0 <= e_out < 1
    # C_c is the minimum of the relative AMD along the collision line (Laskar & Petit 2017, Sect. 3)
    cc = amd.critical_amd_collision(alpha, gamma)
    for f in (0.9, 0.97, 1.03, 1.1):
        e = e_c * f
        if 0 <= e <= min(1.0, 1 / alpha - 1):
            e2 = 1 - alpha - alpha * e
            if 0 <= e2 < 1:
                assert amd.relative_amd(e, e2, alpha, gamma) >= cc - 1e-12


@given(alpha=st.floats(0.1, 0.95), g1=gammas, g2=gammas)
def test_critical_amd_increases_with_gamma(alpha: float, g1: float, g2: float) -> None:
    assume(abs(g1 - g2) > 1e-6 * max(g1, g2))
    lo, hi = sorted((g1, g2))
    assert amd.critical_amd_collision(alpha, lo) < amd.critical_amd_collision(alpha, hi)


@given(a1=st.floats(0.1, 0.95), a2=st.floats(0.1, 0.95), gamma=gammas)
def test_critical_amd_decreases_with_alpha(a1: float, a2: float, gamma: float) -> None:
    assume(abs(a1 - a2) > 1e-6)
    lo, hi = sorted((a1, a2))
    assert amd.critical_amd_collision(lo, gamma) > amd.critical_amd_collision(hi, gamma)


def test_close_pair_asymptote() -> None:
    # Laskar & Petit (2017): C_c ~ gamma / (gamma + 1) * eta^2 / 2 for eta = 1 - alpha -> 0
    eta, gamma = 1e-3, 2.0
    assert amd.critical_amd_collision(1 - eta, gamma) == pytest.approx(
        gamma / (gamma + 1) * eta**2 / 2, rel=1e-2
    )


def test_invalid_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        amd.critical_eccentricity(1.2, 1.0)


@pytest.mark.parametrize("eps", [1e-6, 1e-5, 1e-4, 1e-3])
def test_mmr_overlap_limits_match_petit_2017_developments(eps: float) -> None:
    # the paper rounds the exact coefficient 4 r^(2/7) / 3^(6/7) = 1.4646 to 1.46
    assert 1 - amd.alpha_circular_overlap(eps) == pytest.approx(1.46 * eps ** (2 / 7), rel=5e-3)
    assert 1 - amd.alpha_resonance_switch(eps) == pytest.approx(1.50 * eps**0.25 + 0.316 * eps**0.5, rel=0.02)


def test_mmr_critical_amd_branches() -> None:
    eps = 1e-4
    a_cir = amd.alpha_circular_overlap(eps)
    assert amd.critical_amd_mmr(a_cir + 1e-3, 1.0, eps) == 0.0
    a_r = amd.alpha_resonance_switch(eps)
    assert amd.critical_amd(a_r - 0.01, 1.0, eps)[1] == "collision"
    assert amd.critical_amd(a_r + 0.01, 1.0, eps)[1] == "mmr_overlap"
    # near alpha_R the two critical AMDs are close (that is how alpha_R is defined)
    c0 = amd.critical_amd_collision(a_r, 1.0)
    c1 = amd.critical_amd_mmr(a_r, 1.0, eps)
    assert c1 == pytest.approx(c0, rel=0.15)
    assert amd.alpha_resonance_switch(10.0) == 0.0


@given(e=st.floats(0, 0.4), de=st.floats(0.001, 0.3))
def test_beta_grows_with_eccentricity_and_verdict_never_improves(e: float, de: float) -> None:
    order = {Verdict.STABLE: 0, Verdict.MARGINAL: 1, Verdict.UNSTABLE: 2}
    ms, ps = [3e-5, 3e-5], [1.0, 2.2]
    r1 = real_of(ms, ps, [e, e])
    r2 = real_of(ms, ps, [min(e + de, 0.9), min(e + de, 0.9)])
    b1 = max(p["beta"] for p in amd.analyse(r1)["pairs"])
    b2 = max(p["beta"] for p in amd.analyse(r2)["pairs"])
    assert b2 >= b1
    assert order[amd.classify(r2)] >= order[amd.classify(r1)]


def test_classification_cases() -> None:
    circ = real_of([3e-5, 3e-5], [1.0, 2.2], [0.0, 0.0])
    assert amd.classify(circ) is Verdict.STABLE
    ecc_pair = real_of([3e-5, 3e-5], [1.0, 2.2], [0.5, 0.5])
    assert amd.classify(ecc_pair) is Verdict.UNSTABLE
    # AMD-unstable (resonance-overlap branch) but Hill stable: the Hill criterion is stricter than the
    # collision criterion (Petit et al. 2018), so this only happens where C_MMR < C_H
    mid = real_of([1e-3, 1e-3], [1.0, 1.6], [0.05, 0.0])
    info = amd.analyse(mid)["pairs"][0]
    assert info["critical_branch"] == "mmr_overlap"
    assert info["beta"] > 1 > info["beta_hill"]
    assert amd.classify(mid) is Verdict.MARGINAL
    # weakly AMD-stable: a light inner planet next to an eccentric giant
    weak = real_of([1e-8, 1e-3], [1.0, 8.0], [0.0, 0.15])
    w = amd.analyse(weak)
    assert all(p["beta"] < 1 for p in w["pairs"]) and w["beta_star"] > 1
    assert amd.classify(weak) is Verdict.MARGINAL
    three = real_of([3e-5] * 3, [1.0, 2.0, 4.0], [0.4, 0.4, 0.4])
    assert amd.classify(three) is Verdict.MARGINAL


def test_evaluate_texts() -> None:
    r = amd.evaluate(real_of([3e-5, 3e-5], [1.0, 2.2], [0.0, 0.01]), [])
    assert r.verdict is Verdict.STABLE and r.summary.startswith("AMD-stable")
    r = amd.evaluate(real_of([1e-8, 1e-3], [1.0, 8.0], [0.0, 0.15]), [])
    assert r.summary.startswith("Weakly")
    r = amd.evaluate(real_of([1e-3, 1e-3], [1.0, 1.6], [0.05, 0.0]), [])
    assert "Hill stable in the AMD framework" in r.summary
    r = amd.evaluate(real_of([3e-5, 3e-5], [1.0, 2.2], [0.5, 0.5]), [])
    assert r.summary.startswith("Neither")
    r = amd.evaluate(
        real_of([3e-5] * 3, [1.0, 1.1, 4.0], [0.4, 0.4, 0.4]),
        [real_of([3e-5] * 3, [1.0, 2.0, 4.0], [0.0] * 3)],
    )
    assert r.summary.startswith("AMD-unstable") and "β ≥ 1" in r.summary
    assert any("overlap" in n for n in r.notes)
    assert math.isinf(max(p["beta"] for p in r.details["pairs"]))
    r = amd.evaluate(
        real_of([3e-5, 3e-5], [1.0, 2.2], [0.0, 0.0]), [real_of([3e-5, 3e-5], [1.0, 2.2], [0.5, 0.5])]
    )
    assert r.nominal_verdict is Verdict.STABLE and r.verdict is Verdict.MARGINAL
    assert any("draws disagree" in n for n in r.notes)
