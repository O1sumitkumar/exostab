"""Hill-spacing indicator.

Two planets
    Gladman (1993) applied the Hill-stability criterion of Marchal & Bozis (1982) for the general
    three-body problem to two planets: if it holds, the planets can never have a close encounter. For
    initially circular orbits and small masses it reduces to a separation of 2*sqrt(3) mutual Hill
    radii. We evaluate the eccentric form as restated by Veras & Armitage (2004, their Eqs. 2.5 and
    2.8, without the next-order mass term) and Giuppone et al. (2013, Eq. 3), see :func:`gladman_margin`.
    Petit, Laskar & Boué (2018, Eq. 26) showed that the same inequality can be written with the AMD;
    ``tests/test_hill.py`` checks that the two forms agree. For two planets this is a rigorous
    sufficient condition for the absence of close encounters. It does not exclude the escape of the
    outer planet.

Three or more planets
    No analytic criterion exists. Chambers, Wetherill & Boss (1996) found that the time to the first
    close encounter grows roughly exponentially with the spacing measured in mutual Hill radii. We use
    the spacing of each adjacent pair as a heuristic: any pair that fails the two-planet criterion or
    has crossing orbits is flagged unstable; the system is called stable only if every adjacent pair
    is at least ``DELTA_MULTI`` = 12 mutual Hill radii apart; anything in between is marginal. Pu & Wu
    (2015) found that systems like the Kepler multi-planet systems need a spacing of about 10 to
    survive for a billion years if the orbits are circular and coplanar, and about 12 if the
    eccentricities are about 0.02; we use the larger, more conservative value (DECISIONS.md, D12).

The mutual Hill radius of planets j and k is ((m_j + m_k) / (3 M_*))^(1/3) (a_j + a_k) / 2, the
convention of Chambers et al. (1996) and Pu & Wu (2015). In these units the Gladman limit for two
Earth-mass planets is about 3.4 rather than exactly 2*sqrt(3), because conventions for the reference
semi-major axis differ at order (m / M_*)^(1/3).
"""

from __future__ import annotations

import math
from typing import Any

from .._numerics import bisect
from ..sampling import Realization
from . import DrawStats, IndicatorResult, Verdict, combine

# Spacing (in mutual Hill radii) above which an adjacent pair in a system of three or more planets is
# treated as widely spaced (Pu & Wu 2015). See DECISIONS.md (D12) for the choice and its uncertainty.
DELTA_MULTI = 12.0

REFERENCES = [
    "gladman1993",
    "marchal1982",
    "veras2004",
    "giuppone2013",
    "petit2018",
    "chambers1996",
    "pu2015",
]


def mutual_hill_radius(m1: float, m2: float, a1: float, a2: float, m_star: float) -> float:
    return float(((m1 + m2) / (3 * m_star)) ** (1 / 3) * (a1 + a2) / 2)


def separation_in_hill_radii(m1: float, m2: float, a1: float, a2: float, m_star: float) -> float:
    return (a2 - a1) / mutual_hill_radius(m1, m2, a1, a2, m_star)


def gladman_margin(m1: float, m2: float, a1: float, a2: float, e1: float, e2: float, m_star: float) -> float:
    """Relative margin of the Gladman (1993) two-planet Hill-stability criterion.

    With mu_i = m_i / M_*, alpha = mu_1 + mu_2, gamma_i = sqrt(1 - e_i^2) and delta = sqrt(a_2 / a_1),
    the pair is Hill stable when (Veras & Armitage 2004, Eqs. 2.5 and 2.8; Giuppone et al. 2013, Eq. 3)

        alpha^-3 (mu_1 + mu_2 / delta^2) (mu_1 gamma_1 + mu_2 gamma_2 delta)^2
            > 1 + 3^(4/3) mu_1 mu_2 / alpha^(4/3).

    Returns LHS / RHS - 1: positive means Hill stable. Planet 1 must be the inner one.
    """
    mu1, mu2 = m1 / m_star, m2 / m_star
    alpha = mu1 + mu2
    g1, g2 = math.sqrt(1 - e1**2), math.sqrt(1 - e2**2)
    delta = math.sqrt(a2 / a1)
    lhs = alpha**-3 * (mu1 + mu2 / delta**2) * (mu1 * g1 + mu2 * g2 * delta) ** 2
    rhs = 1 + 3 ** (4 / 3) * mu1 * mu2 / alpha ** (4 / 3)
    return float(lhs / rhs - 1)


def gladman_critical_separation(m1: float, m2: float, m_star: float) -> float:
    """Separation (mutual Hill radii) at which two circular orbits become Hill stable (Gladman 1993)."""

    def f(ratio: float) -> float:
        return gladman_margin(m1, m2, 1.0, ratio, 0.0, 0.0, m_star)

    ratio = bisect(f, 1.0 + 1e-12, 10.0)
    return separation_in_hill_radii(m1, m2, 1.0, ratio, m_star)


def pair_table(real: Realization) -> list[dict[str, Any]]:
    """Spacing diagnostics for every adjacent pair of planets."""
    a = real.semi_major_axes()
    rows = []
    for k in range(len(real.bodies) - 1):
        b1, b2 = real.bodies[k], real.bodies[k + 1]
        a1, a2 = float(a[k]), float(a[k + 1])
        rows.append(
            {
                "pair": f"{b1.name} / {b2.name}",
                "separation_hill": separation_in_hill_radii(b1.m, b2.m, a1, a2, real.m_star),
                "gladman_critical_hill": gladman_critical_separation(b1.m, b2.m, real.m_star),
                "gladman_margin": gladman_margin(b1.m, b2.m, a1, a2, b1.e, b2.e, real.m_star),
                "orbits_cross": a1 * (1 + b1.e) >= a2 * (1 - b2.e),
            }
        )
    return rows


def classify(real: Realization) -> Verdict:
    rows = pair_table(real)
    if any(r["orbits_cross"] or r["gladman_margin"] <= 0 for r in rows):
        return Verdict.UNSTABLE
    if len(rows) == 1:
        return Verdict.STABLE
    if all(r["separation_hill"] >= DELTA_MULTI for r in rows):
        return Verdict.STABLE
    return Verdict.MARGINAL


def evaluate(nominal: Realization, draws: list[Realization]) -> IndicatorResult:
    """Hill-spacing verdict for the nominal parameters and the Monte Carlo draws."""
    rows = pair_table(nominal)
    v_nom = classify(nominal)
    v_draws = [classify(r) for r in draws]
    verdict = combine(v_nom, v_draws)
    two = len(rows) == 1
    closest = min(rows, key=lambda r: r["separation_hill"])
    failing = [r["pair"] for r in rows if r["orbits_cross"] or r["gladman_margin"] <= 0]
    if failing:
        summary = (
            f"Not Hill stable: {', '.join(failing)} "
            f"{'is' if len(failing) == 1 else 'are'} inside the Gladman (1993) limit, so close encounters "
            "are not excluded (a mean-motion resonance can still protect the pair)."
        )
    elif two:
        summary = (
            f"Hill stable: separation {closest['separation_hill']:.2f} mutual Hill radii, above the "
            f"Gladman (1993) limit of {closest['gladman_critical_hill']:.2f} for circular orbits "
            "(eccentricities included in the test)."
        )
    elif v_nom is Verdict.STABLE:
        summary = (
            f"Every adjacent pair is at least {DELTA_MULTI:g} mutual Hill radii apart "
            f"(closest: {closest['pair']}, {closest['separation_hill']:.1f})."
        )
    else:
        summary = (
            f"Every pair passes the two-planet limit, but {closest['pair']} is only "
            f"{closest['separation_hill']:.1f} mutual Hill radii apart (heuristic threshold "
            f"{DELTA_MULTI:g}); long-term stability is not guaranteed by spacing alone."
        )
    notes = []
    if verdict is not v_nom:
        notes.append(f"The nominal parameters give '{v_nom.value}', but the draws disagree.")
    if not two:
        notes.append(
            "For three or more planets the spacing test is a heuristic (Chambers et al. 1996; "
            "Pu & Wu 2015), not a proof."
        )
    return IndicatorResult(
        name="hill",
        title="Hill spacing",
        verdict=verdict,
        nominal_verdict=v_nom,
        summary=summary,
        draws=DrawStats.from_verdicts(v_draws) if draws else None,
        details={"pairs": rows, "delta_multi": DELTA_MULTI},
        notes=notes,
        references=REFERENCES,
    )
