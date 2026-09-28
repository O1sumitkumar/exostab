"""One-parameter sweeps: how do the indicators change when one planet's parameter is varied?

All other parameters stay at the nominal values (randomized angles are drawn once from the seed and then
held fixed, so the sweep isolates the swept parameter). When the argument of periastron or the period is
changed, the mean anomaly at the epoch is kept.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from .indicators import amd, hill
from .indicators.megno import classify_run, megno_seed, run_many
from .integrate import RunConfig
from .models import System
from .plots import sweep_figure
from .report import software_record
from .sampling import Realization, realizations
from .units import days_to_years, mearth_to_msun

PARAM_LABELS = {
    "e": "eccentricity",
    "mass": "mass (Earth masses)",
    "period": "orbital period (days)",
    "omega": "argument of periastron (deg)",
}


def _modified(nominal: Realization, index: int, param: str, value: float) -> Realization:
    if param == "e":
        if not 0 <= value < 1:
            raise ValueError(f"eccentricity must be in [0, 1), got {value}")
        r = nominal.with_body(index, e=value)
    elif param == "mass":
        if value <= 0:
            raise ValueError(f"mass must be positive, got {value}")
        r = nominal.with_body(index, m=mearth_to_msun(value))
    elif param == "period":
        if value <= 0:
            raise ValueError(f"period must be positive, got {value}")
        r = nominal.with_body(index, P=days_to_years(value))
    elif param == "omega":
        r = nominal.with_body(index, pomega=math.radians(value) % (2 * math.pi))
    else:
        raise ValueError(f"unknown sweep parameter {param!r}")
    return replace(r, bodies=tuple(sorted(r.bodies, key=lambda b: b.P)), label=f"{param} = {value:.6g}")


def run_sweep(
    system: System,
    planet: str,
    param: str,
    value_range: tuple[float, float],
    steps: int,
    *,
    orbits: float = 1e4,
    seed: int = 0,
    jobs: int | None = None,
) -> list[dict[str, Any]]:
    """Indicators for ``steps`` values of ``param`` between the two ends of ``value_range``."""
    target = system.planet(planet).name
    nominal = realizations(system, 0, seed)[0]
    index = [b.name for b in nominal.bodies].index(target)
    values = np.linspace(value_range[0], value_range[1], steps)
    reals = [_modified(nominal, index, param, float(v)) for v in values]
    config = RunConfig(n_orbits=orbits)
    runs = run_many([(r, replace(config, megno_seed=megno_seed(seed, 0))) for r in reals], jobs)
    rows = []
    for v, r, res in zip(values, reals, runs, strict=True):
        pairs = hill.pair_table(r)
        closest = min(pairs, key=lambda p: p["separation_hill"])
        a = amd.analyse(r)
        rows.append(
            {
                "value": float(v),
                "nbody_class": classify_run(res),
                "megno": res.megno,
                "energy_error": res.energy_error,
                "status": res.status,
                "t_end_yr": res.t_end,
                "hill_verdict": hill.classify(r).value,
                "hill_min_separation": closest["separation_hill"],
                "hill_margin_min": min(p["gladman_margin"] for p in pairs),
                "hill_gladman_limit": closest["gladman_critical_hill"],
                "amd_verdict": amd.classify(r).value,
                "amd_beta_max": max(p["beta"] for p in a["pairs"]),
            }
        )
    return rows


def write_sweep(
    rows: list[dict[str, Any]], system: System, planet: str, param: str, out_dir: Path
) -> list[Path]:
    csv_path = out_dir / "sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    meta = {
        "system": system.name,
        "planet": system.planet(planet).name,
        "parameter": param,
        "unit": PARAM_LABELS[param],
        "flags": [f.model_dump() for f in system.flags],
        "software": software_record().model_dump(),
        "source": system.source.model_dump(),
    }
    meta_path = out_dir / "sweep.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    png = sweep_figure(
        rows,
        f"{PARAM_LABELS[param]} of {system.planet(planet).name}",
        f"{system.name}: sweep of {PARAM_LABELS[param]} for {system.planet(planet).name}",
        out_dir / "sweep.png",
    )
    return [csv_path, png, meta_path]
