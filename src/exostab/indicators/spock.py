"""Optional fourth indicator: SPOCK's machine-learned stability classifier (Tamayo et al. 2020).

SPOCK's FeatureClassifier estimates the probability that a compact system of three or more planets survives
10^9 orbits of its innermost planet, from features of a short N-body integration. SPOCK 2.1.1 (the latest release,
checked 2026-09-28) requires REBOUND < 5, while exostab uses REBOUND 5, so SPOCK runs in a separate Python
environment: exostab starts that environment's interpreter on ``spock_worker.py`` and exchanges JSON with it
(DECISIONS.md, D23). Set it up with ``scripts/make_spock_env.sh`` and point exostab at it with
``--spock-python`` or the environment variable ``EXOSTAB_SPOCK_PYTHON``.

Verdicts. Tamayo et al. (2020) chose a threshold of 0.34 on the classifier output, which gave a 10% false-positive
rate on their resonant hold-out set. Each realization is "stable" if SPOCK's estimate is at least 0.34 and
"unstable" otherwise; the usual 95% agreement rule then applies. The retrained SPOCK 2.x model has no published
threshold and its output is not a calibrated probability, so this indicator can make the overall verdict marginal
but never unstable on its own (only direct integration can). An estimate of exactly 0 means SPOCK's own short
integration already went unstable.

Domain. SPOCK was trained on compact three-planet systems with planet-to-star mass ratios of 1e-7 to 1e-4 and
adjacent spacings up to about 30 mutual Hill radii; the report warns when a system lies outside that range.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from ..sampling import Realization
from . import DrawStats, IndicatorResult, Verdict, combine
from .hill import pair_table

THRESHOLD = 0.34  # Tamayo et al. (2020): 10% false-positive rate on the resonant hold-out set
MASS_RATIO_RANGE = (1e-7, 1e-4)
MAX_SPACING = 30.0  # mutual Hill radii
WORKER = Path(__file__).with_name("spock_worker.py")
REFERENCES = ["tamayo2020"]


class SpockUnavailableError(RuntimeError):
    """The SPOCK environment is not configured or does not work."""


def spock_python(explicit: str | None = None) -> str | None:
    """Interpreter of the SPOCK environment: the explicit path, else ``EXOSTAB_SPOCK_PYTHON``."""
    return explicit or os.environ.get("EXOSTAB_SPOCK_PYTHON") or None


def _request(real: Realization) -> dict[str, Any]:
    return {
        "m_star": real.m_star,
        "planets": [{"m": b.m, "P": b.P, "e": b.e, "pomega": b.pomega, "M": b.M} for b in real.bodies],
    }


def predict(
    reals: list[Realization], python: str, *, timeout: float = 600.0
) -> tuple[list[float], dict[str, str]]:
    """SPOCK stability estimates for each realization, and the versions used by the worker."""
    payload = json.dumps({"systems": [_request(r) for r in reals], "n_jobs": 1})
    try:
        proc = subprocess.run(
            [python, str(WORKER)], input=payload, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SpockUnavailableError(f"could not run the SPOCK environment {python!r}: {exc}") from exc
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-3:]
        raise SpockUnavailableError(f"the SPOCK worker failed (exit {proc.returncode}): {' | '.join(tail)}")
    try:
        answer = json.loads(proc.stdout)
        probs = [float(p) for p in answer["p_stable"]]
    except (ValueError, KeyError, TypeError) as exc:
        raise SpockUnavailableError(
            f"unexpected answer from the SPOCK worker: {proc.stdout[:200]!r}"
        ) from exc
    if len(probs) != len(reals):
        raise SpockUnavailableError("the SPOCK worker returned a different number of results")
    return probs, {"spock": str(answer.get("spock")), "rebound": str(answer.get("rebound"))}


def classify(p: float) -> Verdict:
    return Verdict.STABLE if p >= THRESHOLD else Verdict.UNSTABLE


def domain_warnings(real: Realization) -> list[str]:
    notes = []
    lo, hi = MASS_RATIO_RANGE
    outside = [b.name for b in real.bodies if not lo <= b.m / real.m_star <= hi]
    if outside:
        notes.append(
            f"Planet-to-star mass ratio outside SPOCK's training range ({lo:g}-{hi:g}) for: {', '.join(outside)}."
        )
    wide = [r["pair"] for r in pair_table(real) if r["separation_hill"] > MAX_SPACING]
    if wide:
        notes.append(
            f"Separated by more than {MAX_SPACING:g} mutual Hill radii (outside SPOCK's training range): "
            + ", ".join(wide)
            + "."
        )
    return notes


def evaluate(nominal: Realization, draws: list[Realization], python: str) -> IndicatorResult:
    """SPOCK verdict for the nominal parameters and the draws (three or more planets only)."""
    if len(nominal.bodies) < 3:
        raise ValueError("SPOCK's classifier applies to systems of three or more planets")
    probs, versions = predict([nominal, *draws], python)
    p_nom, p_draws = probs[0], probs[1:]
    v_nom = classify(p_nom)
    v_draws = [classify(p) for p in p_draws]
    verdict = combine(v_nom, v_draws)
    if p_nom == 0.0:
        summary = "SPOCK's short integration of the nominal parameters already became unstable (estimate 0)."
    else:
        word = "above" if v_nom is Verdict.STABLE else "below"
        summary = (
            f"SPOCK estimate {p_nom:.3g} for surviving 10⁹ orbits of the innermost planet, {word} the "
            f"{THRESHOLD:g} threshold of Tamayo et al. (2020)."
        )
    notes = [
        "Machine-learned estimate, not a calibrated probability; it can make the overall verdict marginal but "
        "never unstable on its own.",
        *domain_warnings(nominal),
    ]
    if verdict is not v_nom:
        notes.append(f"The nominal parameters give '{v_nom.value}', but the draws disagree.")
    details: dict[str, Any] = {
        "threshold": THRESHOLD,
        "p_stable_nominal": p_nom,
        "p_stable_draws": p_draws,
        "versions": versions,
    }
    if p_draws:
        details["p_stable_median"] = sorted(p_draws)[len(p_draws) // 2]
    return IndicatorResult(
        name="spock",
        title="SPOCK (ML)",
        verdict=verdict,
        nominal_verdict=v_nom,
        summary=summary,
        draws=DrawStats.from_verdicts(v_draws) if draws else None,
        details=details,
        notes=notes,
        references=REFERENCES,
    )
