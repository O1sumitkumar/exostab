"""Draw the figures of docs/validation.md (run: PYTHONPATH=. python scripts/validation_figures.py).

Every figure is computed here from scratch with the settings of tests/validation/test_validation.py and the
bundled offline snapshot; nothing is copied from elsewhere except the counts of the HD 127195 Research Note
(134 / 57 / 9 of 200), which are labelled as such. The figure script also prints the Hill-limit fractions and
the HD 127195 draw counts that docs/validation.md quotes.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, cast

os.environ.setdefault("EXOSTAB_OFFLINE", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from tests.validation.test_validation import inner_solar_system, pair_at

from exostab.analysis import CheckSettings, check_system
from exostab.data import load_system, load_system_file
from exostab.indicators.hill import gladman_critical_separation
from exostab.indicators.megno import ENERGY_ERROR_MAX, MEGNO_CHAOTIC, classify_run, run_many
from exostab.integrate import RunConfig, run
from exostab.plots import _RC, INK, MUTED, PLANET_COLORS, STATUS, _plotted_megno

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "validation"


def energy_figure() -> Path:
    r = inner_solar_system()
    n = 1e4 / r.bodies[0].P
    wh = run(r, RunConfig(n_orbits=n, n_samples=300))
    ias = run(r, RunConfig(n_orbits=n, n_samples=300, integrator="ias15"))
    with plt.rc_context(cast(Any, _RC)):
        fig, ax = plt.subplots(figsize=(7, 3.4))
        for res, color, label in ((wh, PLANET_COLORS[0], "WHFast"), (ias, PLANET_COLORS[1], "IAS15")):
            t = np.asarray(res.series["t"][1:])
            e = np.maximum(np.asarray(res.series["energy_error"][1:]), 1e-17)
            ax.semilogy(t, e, color=color, lw=1.3, label=f"{label} (max {res.energy_error:.1e})")
        ax.axhline(1e-7, color=MUTED, ls="--", lw=0.8)
        ax.text(
            0.99,
            1e-7,
            "test limit (WHFast) ",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="bottom",
            fontsize=7.5,
            color=MUTED,
        )
        ax.set_xlabel("time (yr)")
        ax.set_ylabel("|ΔE / E|")
        ax.set_title(
            "Inner Solar System: relative energy error over 10,000 years", fontsize=9, loc="left", color=INK
        )
        ax.legend(loc="center right", fontsize=8)
        path = OUT / "energy.png"
        fig.savefig(path)
        plt.close(fig)
    return path


def hill_figure() -> Path:
    deltas = np.round(np.arange(2.0, 4.51, 0.1), 2)
    phases = np.linspace(0.3, 2 * np.pi, 8, endpoint=False)
    jobs = [
        (pair_at(float(d), phase=float(p)), RunConfig(n_orbits=5000, megno=False))
        for d in deltas
        for p in phases
    ]
    results = run_many(jobs, None)
    grid = np.array([r.status == "encounter" for r in results]).reshape(len(deltas), len(phases))
    met = grid.mean(axis=1)
    orbits = np.array([r.n_orbits_innermost for r in results]).reshape(len(deltas), len(phases))
    # The encounter times inside the limit are chaotic transients that depend on floating-point rounding
    # (docs/validation.md), so these fractions hold for this machine and this horizon only.
    print(
        "Hill limit, 8 starting phases, 5,000 orbits: separation, phases with a close encounter, latest one"
    )
    for d, row, n in zip(deltas, grid, orbits, strict=True):
        latest = f"{n[row].max():,.0f} orbits" if row.any() else "-"
        print(f"  {d:.1f}: {int(row.sum())} of {len(row)}, latest {latest}")
    x = 0.5 * ((2e-5) / 3) ** (1 / 3)
    low_order = 2 * math.sqrt(3) / (1 + 2 * math.sqrt(3) * x)  # Gladman's lowest order, normalised to a_1
    full = gladman_critical_separation(1e-5, 1e-5, 1.0)
    with plt.rc_context(cast(Any, _RC)):
        fig, ax = plt.subplots(figsize=(7, 3.4))
        ax.plot(
            deltas,
            met,
            "o-",
            color=PLANET_COLORS[0],
            lw=1.5,
            ms=4,
            label="N-body: phases meeting within 5,000 orbits",
        )
        ax.axvline(full, color=INK, ls="--", lw=1.0, label=f"full Gladman criterion ({full:.2f})")
        ax.axvline(
            low_order, color=MUTED, ls=":", lw=1.2, label=f"lowest order, normalised to a₁ ({low_order:.2f})"
        )
        ax.set_xlabel("initial separation (mutual Hill radii)")
        ax.set_ylabel("fraction of 8 starting phases")
        ax.set_ylim(-0.05, 1.05)
        ax.set_title(
            "Two 10⁻⁵ M☉ planets on circular orbits, 8 phases × 5,000 orbits (one machine)",
            fontsize=9,
            loc="left",
            color=INK,
        )
        ax.legend(loc="lower left", fontsize=8)
        path = OUT / "hill_limit.png"
        fig.savefig(path)
        plt.close(fig)
    return path


def gj876_figure() -> Path:
    published = check_system(
        load_system_file(ROOT / "tests/validation/systems/gj876_rivera2010.yaml"),
        CheckSettings(draws=20, seed=0, n_samples=0),
    )
    archive = check_system(load_system("GJ 876"), CheckSettings(draws=20, seed=0, n_samples=0))
    with plt.rc_context(cast(Any, _RC)):
        fig, ax = plt.subplots(figsize=(7, 3.6))
        for k, res in enumerate((published, archive)):
            classes = [classify_run(r) for r in res.runs[1:]]
            ys = [_plotted_megno(r.megno, c) for r, c in zip(res.runs[1:], classes, strict=True)]
            jitter = np.linspace(-0.18, 0.18, len(ys))
            for cls, (color, marker, name) in STATUS.items():
                idx = [i for i, c in enumerate(classes) if c == cls]
                if idx:
                    ax.scatter(
                        k + jitter[idx],
                        [ys[i] for i in idx],
                        color=color,
                        marker=marker,
                        s=30,
                        edgecolor="white",
                        lw=0.6,
                        label=name if k == 1 or cls == "regular" else None,
                        zorder=3,
                    )
        ax.axhline(MEGNO_CHAOTIC, color=MUTED, ls="--", lw=0.8)
        ax.set_xticks([0, 1], ["Rivera et al. (2010)\npublished phases", "archive values,\nrandom phases"])
        ax.set_ylabel("final <Y> (encounters at 8)")
        ax.set_title("GJ 876: 20 Monte Carlo draws each", fontsize=9, loc="left", color=INK)
        handles, labels = ax.get_legend_handles_labels()
        uniq = dict(zip(labels, handles, strict=True))
        ax.legend(uniq.values(), uniq.keys(), loc="upper left", fontsize=8)
        path = OUT / "gj876.png"
        fig.savefig(path)
        plt.close(fig)
    return path


def hd127195_figure() -> Path:
    res = check_system(
        load_system_file(ROOT / "examples/hd127195_note.yaml"),
        CheckSettings(orbits=2e4, draws=200, seed=42, n_samples=0),
    )
    counts = res.report.indicators["nbody"].details["classification_counts"]
    ours = [counts["regular"], counts["chaotic"], counts["unstable"]]
    inconclusive = [r for r in res.runs[1:] if classify_run(r) == "inconclusive"]
    why = (
        f"energy error above {ENERGY_ERROR_MAX:g}"
        if all(r.status == "completed" for r in inconclusive)
        else f"energy error above {ENERGY_ERROR_MAX:g}, or a planet passing the star"
    )
    if inconclusive and all(r.megno is not None and r.megno >= MEGNO_CHAOTIC for r in inconclusive):
        why += "; all chaotic by MEGNO"
    print(f"HD 127195 draws: {counts}")
    note = [134, 57, 9]  # Research Note, Table/number N6
    n = 200
    labels = ["regular", "chaotic", "close encounter"]
    with plt.rc_context(cast(Any, _RC)):
        fig, ax = plt.subplots(figsize=(7, 3.4))
        xs = np.arange(3)
        w = 0.36
        ax.bar(xs - w / 2, note, w, color=PLANET_COLORS[1], label="Research Note (Öz 2026)")
        ax.bar(xs + w / 2, ours, w, color=PLANET_COLORS[0], label="exostab (seed 42)")
        for i in range(3):
            p = note[i] / n
            sigma = math.sqrt(p * (1 - p) / n) * n
            ax.errorbar(xs[i] + w * 0.95, note[i], yerr=3 * sigma, color=INK, capsize=3, lw=0.9)
            ax.text(xs[i] - w / 2, note[i] + 2, str(note[i]), ha="center", fontsize=8, color=INK)
            ax.text(xs[i] + w / 2, ours[i] + 2, str(ours[i]), ha="center", fontsize=8, color=INK)
        ax.set_xticks(xs, labels)
        if counts.get("inconclusive"):
            # the Note has no such class: say how many exostab draws the three bars leave out
            ax.set_xlabel(
                f"Not shown: {counts['inconclusive']} exostab draws are inconclusive ({why})",
                fontsize=8,
                color=MUTED,
            )
        ax.set_ylabel("draws (of 200)")
        ax.set_title(
            "HD 127195: Monte Carlo classification (black bars: Note's count ± 3 binomial σ)",
            fontsize=9,
            loc="left",
            color=INK,
        )
        ax.legend(fontsize=8)
        path = OUT / "hd127195.png"
        fig.savefig(path)
        plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (energy_figure, hill_figure, gj876_figure, hd127195_figure):
        print("wrote", f())


if __name__ == "__main__":
    main()
