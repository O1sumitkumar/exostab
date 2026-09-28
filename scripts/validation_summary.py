"""Print the numbers quoted in docs/validation.md (run: python scripts/validation_summary.py).

Uses the same settings as tests/validation/test_validation.py and the bundled offline snapshot, so the
output is reproducible on any machine up to floating-point differences in chaotic runs.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("EXOSTAB_OFFLINE", "1")

from exostab.analysis import CheckSettings, check_system
from exostab.data import load_system, load_system_file
from exostab.indicators.hill import gladman_critical_separation
from exostab.integrate import RunConfig, run
from exostab.report import software_record

ROOT = Path(__file__).resolve().parents[1]


def summary(name: str, res) -> None:  # type: ignore[no-untyped-def]
    rep = res.report
    counts = rep.indicators["nbody"].details["classification_counts"]
    print(f"\n## {name}")
    print(f"overall: {rep.overall.verdict.value}")
    for k, ind in rep.indicators.items():
        print(f"  {k}: {ind.verdict.value} (nominal {ind.nominal_verdict.value})")
    n = res.runs[0]
    print(
        f"  nominal run: {n.status}, <Y> = {n.megno:.4f}, energy error {n.energy_error:.2e}, "
        f"{n.n_orbits_innermost:.0f} inner orbits = {n.t_end:.1f} yr, wall {n.walltime:.1f} s"
    )
    if res.ias15 is not None:
        print(
            f"  IAS15 check: {res.ias15.status}, <Y> = {res.ias15.megno:.4f}, energy error {res.ias15.energy_error:.2e}"
        )
    print(f"  draws: {counts}")
    print(f"  total runtime {rep.runtime_s:.1f} s")


def main() -> None:
    print("software:", software_record().model_dump())
    from tests.validation.test_validation import inner_solar_system  # type: ignore[import-not-found]

    r = inner_solar_system()
    wh = run(r, RunConfig(n_orbits=1e4 / r.bodies[0].P, n_samples=300))
    ias = run(r, RunConfig(n_orbits=1e4 / r.bodies[0].P, integrator="ias15", n_samples=300))
    print(
        f"\n## inner Solar System, 1e4 yr\n  WHFast: energy error {wh.energy_error:.2e}, <Y> {wh.megno:.4f}, "
        f"dt {wh.dt * 365.25:.3f} d\n  IAS15: energy error {ias.energy_error:.2e}, <Y> {ias.megno:.4f}"
    )
    print(
        f"\n## Gladman limit for two 1e-5 Msun planets: {gladman_critical_separation(1e-5, 1e-5, 1.0):.4f} "
        f"mutual Hill radii (2 sqrt 3 = {2 * math.sqrt(3):.4f})"
    )
    summary("TRAPPIST-1 (snapshot)", check_system(load_system("TRAPPIST-1"), CheckSettings(draws=20, seed=0)))
    summary(
        "GJ 876 (Rivera et al. 2010)",
        check_system(
            load_system_file(ROOT / "tests/validation/systems/gj876_rivera2010.yaml"),
            CheckSettings(draws=20, seed=0),
        ),
    )
    summary(
        "GJ 876 (snapshot, archive phases)",
        check_system(load_system("GJ 876"), CheckSettings(draws=20, seed=0)),
    )
    summary("Kepler-11 (snapshot)", check_system(load_system("Kepler-11"), CheckSettings(draws=20, seed=0)))
    summary(
        "HD 127195 (Research Note inputs, 200 draws, 2e4 orbits)",
        check_system(
            load_system_file(ROOT / "examples/hd127195_note.yaml"),
            CheckSettings(orbits=2e4, draws=200, seed=42),
        ),
    )


if __name__ == "__main__":
    main()
