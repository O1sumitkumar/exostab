from __future__ import annotations

import math
from pathlib import Path

import pytest

from exostab.models import DataSource, MassKind, Phase, PhaseKind, Planet, Provenance, Star, System, Value

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
VALIDATION = Path(__file__).resolve().parent / "validation" / "systems"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Never touch the network or the user's cache from tests unless a test opts in."""
    monkeypatch.setenv("EXOSTAB_OFFLINE", "1")
    monkeypatch.setenv("EXOSTAB_CACHE_DIR", str(tmp_path / "cache"))


def V(value: float | None, err: float | None = None, provenance: Provenance = Provenance.MEASURED) -> Value:
    return Value(value=value, err_plus=err, err_minus=err, provenance=provenance)


def two_planet_system(
    *,
    period_ratio: float = 2.5,
    m_earth: tuple[float, float] = (10.0, 10.0),
    e: tuple[float, float] = (0.0, 0.0),
    err: bool = False,
    phases: tuple[float, float] | None = (0.0, 180.0),
) -> System:
    """Two planets around a solar-mass star, inner period 100 d."""
    planets = []
    for k, (P, m, ecc) in enumerate(zip((100.0, 100.0 * period_ratio), m_earth, e)):
        planets.append(
            Planet(
                name=f"Test {'bc'[k]}",
                period_days=V(P, 0.01 if err else None),
                mass_earth=V(m, 0.1 * m if err else None),
                mass_kind=MassKind.TRUE,
                eccentricity=V(ecc, 0.01 if err else None),
                omega_deg=V(90.0 * k),
                phase=Phase(kind=PhaseKind.MEAN_LONGITUDE, value=V(phases[k]))
                if phases is not None
                else Phase(kind=PhaseKind.RANDOM),
            )
        )
    return System(
        name="Test",
        star=Star(name="Test", mass_msun=V(1.0, 0.02 if err else None)),
        planets=tuple(planets),
        source=DataSource(kind="file"),
    )


def hill_limit_ratio(m: float, m_star: float = 1.0) -> float:
    """Period ratio at which two equal circular planets sit exactly 2 sqrt(3) mutual Hill radii apart."""
    x = 0.5 * ((2 * m) / (3 * m_star)) ** (1 / 3) * 2 * math.sqrt(3)
    return ((1 + x) / (1 - x)) ** 1.5
