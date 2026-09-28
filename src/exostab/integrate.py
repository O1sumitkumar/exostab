"""Direct N-body integrations with REBOUND.

Set-up (justified choices; see also DECISIONS.md):

* Units are set explicitly to (yr, AU, Msun) before any particle is added.
* Planets are added by orbital period in Jacobi coordinates (REBOUND's default when no primary is
  given), all in one plane (inclination 0): exostab models systems as coplanar because published
  sky-plane inclinations do not determine the mutual inclinations.
* WHFast (Rein & Tamayo 2015), a symplectic Wisdom-Holman integrator, is used for all runs. Its
  timestep is ``dt_fraction`` (default 1/30) of the shortest *pericentre passage timescale*
  T_p = 2 pi / f_dot_p = P (1 - e)^(3/2) / (1 + e)^(1/2) over all planets, where f_dot_p is the rate
  of change of the true anomaly at pericentre. Wisdom (2015) found 1/20 of T_p typically adequate to
  resolve the pericentre passage (as restated by Hadden & Lithwick 2018, who used 1/30). For circular
  orbits our step is P_min / 30, finer than the P_min / 20 required by the project brief and the same
  as the HD 127195 Research Note; for eccentric orbits it shrinks accordingly.
* IAS15 (Rein & Spiegel 2015), an adaptive high-order integrator, repeats the nominal run as an
  independent check; it does not rely on a fixed timestep and handles close approaches accurately.
* MEGNO (Cincotta & Simo 2000) is computed from REBOUND's variational equations (Rein & Tamayo 2016).
* A run stops early with a *close encounter* when two planets come closer than the mean of their Hill
  radii, (R_H,j + R_H,k) / 2 with R_H,k = a_k (m_k / 3 M_*)^(1/3). This uses REBOUND's collision detection
  ("line" mode, which also catches passages between two steps) with each planet given a radius of half its
  Hill radius. For two similar planets this equals the HD 127195 Research Note's rule (the smaller Hill
  radius); unlike a single global distance, it also works when the system contains a much smaller planet
  (DECISIONS.md, D20). The run stops with an *escape* when a
  body moves farther than ``escape_factor`` (default 100) times the largest semi-major axis from the
  centre of mass.
* The relative energy error |E(t) - E(0)| / |E(0)| is measured at every sample and at the end; the
  maximum is reported. A run whose error exceeds the threshold in :mod:`exostab.indicators.megno` is
  classified as inconclusive instead of receiving a verdict.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import rebound

from .sampling import Realization
from .units import SIM_UNITS

Integrator = Literal["whfast", "ias15"]
Status = Literal["completed", "encounter", "escape", "error"]


@dataclass(frozen=True)
class RunConfig:
    """How to integrate one realization."""

    n_orbits: float = 1e4  # length, in orbits of the innermost planet
    integrator: Integrator = "whfast"
    dt_fraction: float = 1 / 30  # WHFast step as a fraction of the shortest pericentre timescale
    megno: bool = True
    megno_seed: int = 0
    n_samples: int = 0  # number of time-series samples to keep (0: only the final state)
    escape_factor: float = 100.0


@dataclass
class RunResult:
    """Outcome of one integration."""

    label: str
    integrator: str
    dt: float | None  # yr (None for IAS15, which is adaptive)
    t_target: float  # yr
    t_end: float  # yr, time actually reached
    status: Status
    megno: float | None
    lyapunov: float | None  # 1/yr
    energy_error: float  # maximum relative energy error over the run
    walltime: float  # s
    encounter_distance: float  # AU
    n_orbits_innermost: float
    n_orbits_outermost: float
    series: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def pericentre_timescale(P: float, e: float) -> float:
    """P (1 - e)^(3/2) / (1 + e)^(1/2): 2 pi divided by the angular velocity at pericentre."""
    return float(P * (1 - e) ** 1.5 / math.sqrt(1 + e))


def timestep(real: Realization, dt_fraction: float) -> float:
    """WHFast timestep in years (see module docstring)."""
    return dt_fraction * min(pericentre_timescale(b.P, b.e) for b in real.bodies)


ENCOUNTER_HILL_FRACTION = 0.5  # collision radius of a planet, as a fraction of its Hill radius


def encounter_distance(real: Realization) -> float:
    """Smallest close-encounter distance over adjacent pairs, (R_H,j + R_H,k) / 2, in AU (for reports)."""
    r = hill_radii(real)
    return min(ENCOUNTER_HILL_FRACTION * (r[k] + r[k + 1]) for k in range(len(r) - 1))


def hill_radii(real: Realization) -> list[float]:
    a = real.semi_major_axes()
    return [float(a[k]) * (b.m / (3 * real.m_star)) ** (1 / 3) for k, b in enumerate(real.bodies)]


def build_simulation(real: Realization, config: RunConfig) -> rebound.Simulation:
    """A REBOUND simulation of ``real`` in (yr, AU, Msun), centred on the centre of mass."""
    sim = rebound.Simulation()
    sim.units = SIM_UNITS
    sim.add(m=real.m_star)
    for b in real.bodies:
        # inc = 0: coplanar. Omega = 0, so pomega = omega; M is the mean anomaly at the epoch.
        sim.add(m=b.m, P=b.P, e=b.e, inc=0.0, Omega=0.0, omega=b.pomega, M=b.M)
    sim.move_to_com()
    sim.integrator = config.integrator
    if config.integrator == "whfast":
        sim.dt = timestep(real, config.dt_fraction)
    for k, rh in enumerate(hill_radii(real)):
        sim.particles[k + 1].r = ENCOUNTER_HILL_FRACTION * rh
    sim.collision = "line"
    sim.collision_resolve = "halt"
    sim.exit_max_distance = config.escape_factor * max(p.a for p in sim.particles[1:])
    return sim


def run(real: Realization, config: RunConfig) -> RunResult:
    """Integrate one realization and return what happened. Never raises for physical outcomes."""
    t_wall = time.perf_counter()
    sim = build_simulation(real, config)
    if config.megno:
        sim.init_megno(seed=config.megno_seed)
    periods = [b.P for b in real.bodies]
    t_target = config.n_orbits * min(periods)
    e0 = sim.energy()
    n_planets = len(real.bodies)
    series: dict[str, Any] = {"t": [], "megno": [], "energy_error": []}
    series.update({f"x{k}": [] for k in range(n_planets)})
    series.update({f"y{k}": [] for k in range(n_planets)})
    max_err = 0.0
    status: Status = "completed"
    error: str | None = None

    def sample() -> None:
        nonlocal max_err
        err = abs((sim.energy() - e0) / e0)
        max_err = max(max_err, err)
        if config.n_samples:
            series["t"].append(sim.t)
            series["megno"].append(sim.megno() if config.megno else math.nan)
            series["energy_error"].append(err)
            star = sim.particles[0]
            for k in range(n_planets):
                p = sim.particles[k + 1]
                series[f"x{k}"].append(p.x - star.x)
                series[f"y{k}"].append(p.y - star.y)

    checkpoints = [t_target * (i + 1) / config.n_samples for i in range(config.n_samples)] or [t_target]
    try:
        if config.n_samples:
            sample()
        for tc in checkpoints:
            # exact_finish_time=0: never shorten a step to land on the checkpoint, so sampling does not
            # change the trajectory of a fixed-step integrator.
            sim.integrate(tc, exact_finish_time=0)
            sample()
    except (rebound.Collision, rebound.Encounter):
        status = "encounter"
    except rebound.Escape:
        status = "escape"
    except Exception as exc:  # pragma: no cover - defensive: REBOUND errors we do not expect
        status = "error"
        error = f"{type(exc).__name__}: {exc}"
    if status != "completed":
        try:
            max_err = max(max_err, abs((sim.energy() - e0) / e0))
        except Exception:  # pragma: no cover
            max_err = math.inf
    megno = lyap = None
    if config.megno:
        megno, lyap = float(sim.megno()), float(sim.lyapunov())
    if not math.isfinite(max_err):
        status, error = "error", error or "non-finite energy"
    return RunResult(
        label=real.label,
        integrator=config.integrator,
        dt=sim.dt if config.integrator == "whfast" else None,
        t_target=t_target,
        t_end=float(sim.t),
        status=status,
        megno=megno,
        lyapunov=lyap,
        energy_error=max_err,
        walltime=time.perf_counter() - t_wall,
        encounter_distance=encounter_distance(real),
        n_orbits_innermost=float(sim.t) / min(periods),
        n_orbits_outermost=float(sim.t) / max(periods),
        series=series if config.n_samples else {},
        error=error,
    )
