"""Interactive (plotly) versions of the exostab figures, with the same colours and markers as plots.py."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..indicators.megno import MEGNO_CHAOTIC, classify_run
from ..integrate import RunResult
from ..plots import MEGNO_CLIP, PLANET_COLORS, STATUS, _ellipse, _plotted_megno, planet_color
from ..sampling import Realization
from ..units import format_years

MARKERS = {"o": "circle", "s": "square", "X": "x", "D": "diamond"}


def orbits(nominal: Realization, run: RunResult, title: str) -> go.Figure:
    """Top-down view: nominal orbits (lines) and positions sampled during the nominal run (dots)."""
    a = nominal.semi_major_axes()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0],
            y=[0],
            mode="markers",
            marker={"symbol": "star", "size": 14, "color": "#eda100"},
            name="star",
            hoverinfo="name",
        )
    )
    for k, b in enumerate(nominal.bodies):
        c = planet_color(k)
        x, y = _ellipse(float(a[k]), b.e, b.pomega, n=300)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"color": c, "width": 2},
                name=b.name,
                legendgroup=b.name,
                hovertemplate=f"{b.name}<br>a = {a[k]:.4g} AU, e = {b.e:.3g}<extra></extra>",
            )
        )
        xs, ys = run.series.get(f"x{k}"), run.series.get(f"y{k}")
        if xs and ys:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    marker={"color": c, "size": 3, "opacity": 0.4},
                    name=f"{b.name} (positions)",
                    legendgroup=b.name,
                    showlegend=False,
                    hovertemplate=f"{b.name}<br>x = %{{x:.4g}} AU<br>y = %{{y:.4g}} AU<extra></extra>",
                )
            )
    fig.update_layout(
        title=f"{title}: orbits and positions over {format_years(run.t_end)}",
        height=520,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "y": -0.12},
    )
    fig.update_xaxes(title="x (AU)", zeroline=False)
    fig.update_yaxes(title="y (AU)", scaleanchor="x", scaleratio=1, zeroline=False)
    return fig


def megno_time(nominal: RunResult, ias15: RunResult | None, title: str) -> go.Figure:
    """<Y>(t) and the relative energy error of the nominal run (WHFast, and the IAS15 check)."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
    for res, color, dash, name in (
        (nominal, PLANET_COLORS[0], "solid", "WHFast"),
        (ias15, PLANET_COLORS[1], "dash", "IAS15 check"),
    ):
        if res is None or not res.series.get("t"):
            continue
        t = np.asarray(res.series["t"])
        y = np.minimum(np.asarray(res.series["megno"]), MEGNO_CLIP)
        e = np.maximum(np.asarray(res.series["energy_error"]), 1e-17)
        fig.add_trace(
            go.Scatter(
                x=t,
                y=y,
                mode="lines",
                line={"color": color, "dash": dash},
                name=name,
                legendgroup=name,
                hovertemplate="t = %{x:.4g} yr<br><Y> = %{y:.4f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=t[1:],
                y=e[1:],
                mode="lines",
                line={"color": color, "dash": dash},
                name=name,
                legendgroup=name,
                showlegend=False,
                hovertemplate="t = %{x:.4g} yr<br>|ΔE/E| = %{y:.2e}<extra></extra>",
            ),
            row=2,
            col=1,
        )
    fig.add_hline(y=2.0, line={"color": "#52514e", "dash": "dot", "width": 1}, row=1, col=1)
    fig.add_hline(
        y=MEGNO_CHAOTIC,
        line={"color": "#52514e", "dash": "dash", "width": 1},
        row=1,
        col=1,
        annotation_text=f"chaotic above {MEGNO_CHAOTIC:g}",
        annotation_position="top right",
    )
    fig.update_yaxes(title="MEGNO <Y>", row=1, col=1)
    fig.update_yaxes(title="|ΔE / E|", type="log", exponentformat="power", row=2, col=1)
    fig.update_xaxes(title="time (yr)", row=2, col=1)
    fig.update_layout(
        title=f"{title}: nominal run",
        height=460,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "y": 1.08},
    )
    return fig


def megno_draws(runs: Sequence[RunResult]) -> go.Figure:
    """Final <Y> of every Monte Carlo draw, sorted, coloured and shaped by classification."""
    draws = list(runs[1:])
    classes = [classify_run(r) for r in draws]
    ys = [_plotted_megno(r.megno, c) for r, c in zip(draws, classes, strict=True)]
    order = np.argsort(ys) if ys else np.array([], dtype=int)
    fig = go.Figure()
    for cls, (color, marker, label) in STATUS.items():
        idx = [i for i in range(len(order)) if classes[order[i]] == cls]
        if not idx:
            continue
        runs_sel = [draws[order[i]] for i in idx]
        fig.add_trace(
            go.Scatter(
                x=idx,
                y=[ys[order[i]] for i in idx],
                mode="markers",
                name=f"{label} ({len(idx)})",
                marker={
                    "color": color,
                    "symbol": MARKERS[marker],
                    "size": 9,
                    "line": {"color": "white", "width": 1},
                },
                customdata=[
                    [r.label, r.megno if r.megno is not None else float("nan"), r.status, r.energy_error]
                    for r in runs_sel
                ],
                hovertemplate="%{customdata[0]}<br><Y> = %{customdata[1]:.3f}<br>%{customdata[2]}"
                "<br>|ΔE/E| = %{customdata[3]:.1e}<extra></extra>",
            )
        )
    fig.add_hline(y=MEGNO_CHAOTIC, line={"color": "#52514e", "dash": "dash", "width": 1})
    fig.update_layout(
        title=f"{len(draws)} draws within the uncertainties",
        height=420,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "y": -0.2},
    )
    fig.update_xaxes(title="draws, sorted by <Y>")
    fig.update_yaxes(title=f"final <Y> (encounters at {MEGNO_CLIP:g})")
    return fig
