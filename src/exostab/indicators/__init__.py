"""Stability indicators.

Each indicator returns an :class:`IndicatorResult` with one of four verdicts:

* ``stable`` – the indicator's condition for stability holds for the nominal parameters and for at least
  95% of the Monte Carlo draws;
* ``unstable`` – the indicator predicts instability for the nominal parameters and for at least 95% of
  the draws;
* ``marginal`` – anything in between: a borderline value, or draws that disagree with the nominal run;
* ``inconclusive`` – the indicator could not be evaluated reliably (for example, the integration's
  energy error was too large).

The analytic indicators (Hill spacing and AMD) are *sufficient* conditions or heuristics: failing them
means stability is not guaranteed, not that the system must fall apart. Resonant systems such as
GJ 876 fail both and are nevertheless long-lived. The report explains this next to every verdict.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

AGREEMENT = 0.95  # fraction of draws that must share the nominal verdict for it to stand


class Verdict(str, Enum):
    STABLE = "stable"
    MARGINAL = "marginal"
    UNSTABLE = "unstable"
    INCONCLUSIVE = "inconclusive"


class DrawStats(BaseModel):
    """How the Monte Carlo draws were classified by one indicator."""

    model_config = ConfigDict(extra="forbid")

    n: int
    stable: int
    marginal: int
    unstable: int
    inconclusive: int

    @classmethod
    def from_verdicts(cls, verdicts: Sequence[Verdict]) -> DrawStats:
        return cls(
            n=len(verdicts),
            stable=sum(v is Verdict.STABLE for v in verdicts),
            marginal=sum(v is Verdict.MARGINAL for v in verdicts),
            unstable=sum(v is Verdict.UNSTABLE for v in verdicts),
            inconclusive=sum(v is Verdict.INCONCLUSIVE for v in verdicts),
        )

    def count(self, verdict: Verdict) -> int:
        return int(getattr(self, verdict.value))


class IndicatorResult(BaseModel):
    """Outcome of one indicator for one system."""

    model_config = ConfigDict(extra="forbid")

    name: str  # "hill", "amd", "nbody"
    title: str
    verdict: Verdict
    summary: str  # one plain-language sentence
    nominal_verdict: Verdict
    draws: DrawStats | None = None
    details: dict[str, Any] = {}
    notes: list[str] = []
    references: list[str] = []  # keys into docs/references.bib


def combine(nominal: Verdict, draws: Sequence[Verdict]) -> Verdict:
    """Combine the nominal verdict with the verdicts of the Monte Carlo draws.

    The nominal verdict stands only if at least ``AGREEMENT`` of the draws share it; otherwise the
    result is ``marginal``. An inconclusive nominal run makes the whole indicator inconclusive, and so
    does a set of draws of which more than 20% are inconclusive.
    """
    if nominal is Verdict.INCONCLUSIVE:
        return Verdict.INCONCLUSIVE
    if not draws:
        return nominal
    n = len(draws)
    if sum(v is Verdict.INCONCLUSIVE for v in draws) > 0.2 * n:
        return Verdict.INCONCLUSIVE
    agree = sum(v is nominal for v in draws)
    if agree >= AGREEMENT * n:
        return nominal
    return Verdict.MARGINAL
