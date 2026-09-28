"""Angular momentum deficit (AMD) indicator.

The AMD of a planetary system (Laskar & Petit 2017, their Sect. 3) is

    C = sum_k Lambda_k (1 - sqrt(1 - e_k^2) cos i_k),   Lambda_k = m_k sqrt(G M_* a_k),

the difference between the angular momentum of circular, coplanar orbits and the actual one. It is
conserved by the secular (orbit-averaged) dynamics, so it bounds how eccentric the orbits can ever
become. exostab models coplanar systems (cos i_k = 1).

AMD stability (Laskar & Petit 2017)
    A pair of adjacent planets (inner m, a; outer m', a'; alpha = a/a', gamma = m/m') is AMD-stable if
    the total AMD, even if absorbed entirely by this pair, cannot make the orbits cross:
    beta = C / (Lambda' C_c(alpha, gamma)) < 1, where the critical relative AMD C_c is the smallest AMD
    allowing a(1 + e) = a'(1 - e'). The critical inner eccentricity e_c solves

        alpha e + gamma e / sqrt(alpha (1 - e^2) + gamma^2 e^2) - 1 + alpha = 0,

    with e'_c = 1 - alpha - alpha e_c and C_c = gamma sqrt(alpha) (1 - sqrt(1 - e_c^2)) + 1 - sqrt(1 - e'_c^2)
    (their Eqs. for the collision line, the Lagrange condition and the relative AMD). The system is
    AMD-stable if every adjacent pair is; it is *strongly* AMD-stable if in addition the AMD cannot
    bring the innermost planet to the star, beta_S = C / Lambda_1 < 1.

Mean-motion-resonance overlap (Petit, Laskar & Boué 2017)
    Close pairs can become chaotic through overlapping first-order mean-motion resonances before their
    orbits cross. With eps = (m + m') / M_* and r = 0.80199, the overlap condition defines

        g(alpha, eps) = 3^4 (1 - alpha)^5 / (2^9 r eps) - 32 r eps / (9 (1 - alpha)^2)  (0 if alpha > alpha_cir),
        C_MMR = g^2 / 2 * gamma sqrt(alpha) / (1 + gamma sqrt(alpha)),

    where 1 - alpha_cir = 1.46 eps^(2/7) is the circular-orbit overlap limit. The critical AMD is C_c for
    alpha < alpha_R and C_MMR for alpha > alpha_R, alpha_R being the root of
    3^6 (1 - alpha)^7 - 3^2 2^9 r eps (1 - alpha)^3 - 2^14 (r eps)^2 = 0.

Hill stability in the AMD framework (Petit, Laskar & Boué 2018)
    For two planets (eps = (m + m') / M_*), the pair is Hill stable if its relative AMD C / Lambda' is below

        C_H = gamma sqrt(alpha) + 1 - (1 + gamma)^(3/2) sqrt(alpha / (gamma + alpha) (1 + 3^(4/3) eps^(2/3) gamma / (1 + gamma)^2)).

    The authors note that this criterion does not carry over to tightly packed systems of three or
    more planets, so it is only used for two-planet systems.

Verdicts
    * stable: strongly AMD-stable (all beta < 1, including the MMR-overlap refinement, and beta_S < 1);
    * unstable: a two-planet system that is neither AMD-stable nor Hill stable (beta_H >= 1);
    * marginal: anything else. AMD instability means only that collisions are not excluded by AMD
      conservation; the Solar System itself is AMD-unstable (Laskar & Petit 2017).
"""

from __future__ import annotations

import math
from typing import Any

from .._numerics import bisect
from ..sampling import Realization
from . import DrawStats, IndicatorResult, Verdict, combine


def _b(x: float) -> str:
    return "∞" if math.isinf(x) else f"{x:.3g}"


R_MMR = 0.80199  # Petit et al. (2017), r = (K_1(2/3) + 2 K_0(2/3)) / pi
REFERENCES = ["laskar2017", "petit2017", "petit2018"]


def relative_amd(e_in: float, e_out: float, alpha: float, gamma: float) -> float:
    """Relative AMD C / Lambda' of a coplanar pair (Laskar & Petit 2017)."""
    return gamma * math.sqrt(alpha) * (1 - math.sqrt(1 - e_in**2)) + 1 - math.sqrt(1 - e_out**2)


def critical_eccentricity(alpha: float, gamma: float) -> float:
    """Inner-orbit eccentricity e_c at the AMD-critical collision (Laskar & Petit 2017)."""
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    def F(e: float) -> float:
        return alpha * e + gamma * e / math.sqrt(alpha * (1 - e**2) + gamma**2 * e**2) - 1 + alpha

    return bisect(F, 0.0, min(1.0, 1 / alpha - 1))


def critical_amd_collision(alpha: float, gamma: float) -> float:
    """Critical relative AMD C_c(alpha, gamma) for orbit crossing (Laskar & Petit 2017)."""
    e_c = critical_eccentricity(alpha, gamma)
    e_c_out = 1 - alpha - alpha * e_c
    return relative_amd(e_c, e_c_out, alpha, gamma)


def alpha_circular_overlap(eps: float) -> float:
    """alpha above which first-order resonances overlap even for circular orbits (Petit et al. 2017).

    Exact root of 3^6 (1 - alpha)^7 = 2^14 r^2 eps^2, i.e. 1 - alpha = 4 r^(2/7) eps^(2/7) / 3^(6/7) = 1.46 eps^(2/7).
    """
    return float(1 - 4 * R_MMR ** (2 / 7) * eps ** (2 / 7) / 3 ** (6 / 7))


def alpha_resonance_switch(eps: float) -> float:
    """alpha_R: the MMR-overlap critical AMD replaces the collision one for alpha > alpha_R (Petit et al. 2017)."""

    def P(x: float) -> float:  # x = 1 - alpha
        return 3**6 * x**7 - 3**2 * 2**9 * R_MMR * eps * x**3 - 2**14 * (R_MMR * eps) ** 2

    x = bisect(P, 1e-12, 1.0) if P(1.0) > 0 else 1.0
    return 1 - x


def critical_amd_mmr(alpha: float, gamma: float, eps: float) -> float:
    """Critical relative AMD from first-order MMR overlap, C_c^(1) of Petit et al. (2017)."""
    if alpha >= alpha_circular_overlap(eps):
        return 0.0
    x = 1 - alpha
    g = 3**4 * x**5 / (2**9 * R_MMR * eps) - 32 * R_MMR * eps / (9 * x**2)
    g = max(g, 0.0)
    s = gamma * math.sqrt(alpha)
    return g**2 / 2 * s / (1 + s)


def critical_amd(alpha: float, gamma: float, eps: float) -> tuple[float, str]:
    """Piece-wise critical relative AMD of Petit et al. (2017) and which branch was used."""
    if alpha > alpha_resonance_switch(eps):
        return critical_amd_mmr(alpha, gamma, eps), "mmr_overlap"
    return critical_amd_collision(alpha, gamma), "collision"


def critical_amd_hill(alpha: float, gamma: float, eps: float) -> float:
    """Critical relative AMD for Hill stability of two planets, C_H of Petit et al. (2018)."""
    term = alpha / (gamma + alpha) * (1 + 3 ** (4 / 3) * eps ** (2 / 3) * gamma / (1 + gamma) ** 2)
    return float(gamma * math.sqrt(alpha) + 1 - (1 + gamma) ** 1.5 * math.sqrt(term))


def analyse(real: Realization) -> dict[str, Any]:
    """AMD, per-pair coefficients beta (and beta_H for two planets) and beta_S."""
    a = real.semi_major_axes()
    ms = [b.m for b in real.bodies]
    # Lambda_k / sqrt(G M_*): the common factor cancels in every ratio below.
    lam = [m * math.sqrt(float(ak)) for m, ak in zip(ms, a, strict=True)]
    amd_k = [lam[k] * (1 - math.sqrt(1 - b.e**2)) for k, b in enumerate(real.bodies)]
    total = sum(amd_k)
    pairs = []
    for k in range(len(real.bodies) - 1):
        alpha = float(a[k] / a[k + 1])
        gamma = ms[k] / ms[k + 1]
        eps = (ms[k] + ms[k + 1]) / real.m_star
        cc, branch = critical_amd(alpha, gamma, eps)
        rel = total / lam[k + 1]
        beta = rel / cc if cc > 0 else math.inf
        row: dict[str, Any] = {
            "pair": f"{real.bodies[k].name} / {real.bodies[k + 1].name}",
            "alpha": alpha,
            "gamma": gamma,
            "epsilon": eps,
            "relative_amd": rel,
            "critical_amd": cc,
            "critical_branch": branch,
            "beta": beta,
            "circular_overlap": alpha >= alpha_circular_overlap(eps),
        }
        if len(real.bodies) == 2:
            ch = critical_amd_hill(alpha, gamma, eps)
            row["critical_amd_hill"] = ch
            row["beta_hill"] = rel / ch if ch > 0 else math.inf
        pairs.append(row)
    return {"total_amd_relative_to_lambda_1": total / lam[0], "beta_star": total / lam[0], "pairs": pairs}


def classify(real: Realization) -> Verdict:
    info = analyse(real)
    pairs = info["pairs"]
    if all(p["beta"] < 1 for p in pairs) and info["beta_star"] < 1:
        return Verdict.STABLE
    if len(pairs) == 1 and pairs[0]["beta"] >= 1 and pairs[0]["beta_hill"] >= 1:
        return Verdict.UNSTABLE
    return Verdict.MARGINAL


def evaluate(nominal: Realization, draws: list[Realization]) -> IndicatorResult:
    info = analyse(nominal)
    v_nom = classify(nominal)
    v_draws = [classify(r) for r in draws]
    verdict = combine(v_nom, v_draws)
    pairs = info["pairs"]
    worst = max(pairs, key=lambda p: p["beta"])
    amd_stable = all(p["beta"] < 1 for p in pairs)
    if v_nom is Verdict.STABLE:
        summary = (
            f"AMD-stable: largest β = {_b(worst['beta'])} ({worst['pair']}), so collisions are excluded "
            "in the secular approximation."
        )
    elif amd_stable:
        summary = (
            f"Weakly AMD-stable: no planet-planet collisions (largest β = {_b(worst['beta'])}), but the AMD "
            f"could in principle bring the innermost planet to the star (β_S = {_b(info['beta_star'])})."
        )
    elif len(pairs) == 1 and pairs[0]["beta_hill"] < 1:
        summary = (
            f"AMD-unstable (β = {_b(worst['beta'])}) but Hill stable in the AMD framework "
            f"(β_H = {_b(pairs[0]['beta_hill'])}): close encounters are impossible, chaos is not excluded."
        )
    elif len(pairs) == 1:
        summary = (
            f"Neither AMD-stable (β = {_b(worst['beta'])}) nor Hill stable (β_H = {_b(pairs[0]['beta_hill'])}): "
            "the AMD allows close encounters."
        )
    else:
        n_bad = sum(p["beta"] >= 1 for p in pairs)
        summary = (
            f"AMD-unstable: {n_bad} of {len(pairs)} adjacent pairs have β ≥ 1 (largest {_b(worst['beta'])}, "
            f"{worst['pair']}); collisions are not excluded by AMD conservation, which does not imply they happen."
        )
    notes = []
    if verdict is not v_nom and v_nom is not Verdict.INCONCLUSIVE:
        notes.append(f"The nominal parameters give '{v_nom.value}', but the draws disagree.")
    mmr = [p["pair"] for p in pairs if p["critical_branch"] == "mmr_overlap"]
    if mmr:
        notes.append(
            "Critical AMD from first-order resonance overlap (Petit et al. 2017) used for: "
            + ", ".join(mmr)
            + "."
        )
    circ = [p["pair"] for p in pairs if p["circular_overlap"]]
    if circ:
        notes.append("Resonances overlap even for circular orbits for: " + ", ".join(circ) + ".")
    return IndicatorResult(
        name="amd",
        title="AMD",
        verdict=verdict,
        nominal_verdict=v_nom,
        summary=summary,
        draws=DrawStats.from_verdicts(v_draws) if draws else None,
        details=info,
        notes=notes,
        references=REFERENCES,
    )
