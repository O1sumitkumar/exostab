"""Render docs/assets/social-preview.png, the 1280 x 640 link-preview image of the repository and the docs site.

The orbit figure is drawn from a real run, the one `exostab check "TRAPPIST-1" --offline` makes with the default
settings (10,000 orbits of the innermost planet, 20 draws, seed 0, bundled archive snapshot): the nominal orbits,
the planet positions sampled during the nominal WHFast run, and each planet's position at the end of the run. The
caption's numbers come from the same run, and the logo is drawn from docs/assets/logo/logo-light.svg. Nothing is
edited by hand.

    python scripts/make_social_preview.py [--font-dir DIR] [--out PATH]

Fonts. The text uses the typeface of the logo's wordmark, Source Sans 3 (regular and semibold; SIL Open Font
License 1.1, https://github.com/adobe-fonts/source-sans), taken from ``--font-dir`` (or the environment variable
``EXOSTAB_FONT_DIR``) or from the installed fonts. Without it the image is drawn with DejaVu Sans, which ships with
Matplotlib, and the script says so. The command in the caption uses Source Code Pro if it is installed, else
DejaVu Sans Mono.

To use the image on GitHub: Settings > General > Social preview > Edit > Upload an image (PNG under 1 MB).
"""

from __future__ import annotations

import argparse
import io
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("EXOSTAB_OFFLINE", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch
from matplotlib.path import Path as MPath
from PIL import Image

from exostab.analysis import CheckSettings, check_system
from exostab.data import load_system

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "social-preview.png"
LOGO = ROOT / "docs" / "assets" / "logo" / "logo-light.svg"

W, H = 1280, 640  # GitHub's recommended social-preview size
SS = 2  # drawn at twice the size, then downsampled once, so text and lines are antialiased alike
PT = 0.72  # points per target pixel (the canvas is W x H pixels at 100 dpi)

# The logo's palette (docs/stylesheets/extra.css): Ink, Teal, Amber, plus neutral greys for the light background.
INK, TEAL, AMBER = "#0B2A3F", "#0F8B8D", "#F0A23B"
BG, MUTED, PANEL = "#FFFFFF", "#4A6274", "#F2F6F9"

SYSTEM = "TRAPPIST-1"
TAGLINE = ("Orbital stability for known", "exoplanet systems")
SUBLINE = "Honest, traceable indicators, with every assumption shown."
PILLS = ("Hill spacing", "AMD", "N-body + MEGNO")
URL = "github.com/mimitoz62/exostab"
COMMAND = f'exostab check "{SYSTEM}" --offline'
DATA_NOTE = "NASA Exoplanet Archive data"

# Layout in target pixels, y downwards: left text column, then the orbit figure (centre x, centre y, size).
X0 = 80
LOGO_TOP, LOGO_H = 92, 96
TAG_Y, TAG_DY = 268, 56
PILL_TOP, PILL_H, PILL_PAD, PILL_GAP = 418, 40, 17, 12
URL_Y = 552
FIG_X, FIG_Y, FIG_SIZE = 955, 296, 490
CAPTION_Y = 571


# ---------------------------------------------------------------- fonts


def _font_files(directory: str | None) -> list[str]:
    if not directory or not Path(directory).is_dir():
        return []
    return sorted(str(p) for p in Path(directory).iterdir() if p.suffix.lower() in (".ttf", ".otf"))


def _source_sans(font_dir: str | None) -> dict[int, FontProperties] | None:
    """Regular (400) and semibold (600) Source Sans 3, from ``font_dir`` or the installed fonts, or None."""
    candidates: dict[int, str] = {}
    files = _font_files(font_dir) + [f.fname for f in font_manager.fontManager.ttflist]
    for path in files:
        try:
            entry = font_manager.ttfFontProperty(font_manager.ft2font.FT2Font(path))
        except (OSError, RuntimeError):
            continue
        name = entry.name.replace(" ", "").lower()
        if not name.startswith("sourcesans3") or entry.style != "normal":
            continue
        weight = int(entry.weight) if str(entry.weight).isdigit() else 400
        if weight in (400, 600):
            candidates.setdefault(weight, path)
    if 400 in candidates and 600 in candidates:
        return {w: FontProperties(fname=p) for w, p in candidates.items()}
    return None


def fonts(font_dir: str | None) -> tuple[dict[int, FontProperties], FontProperties]:
    sans = _source_sans(font_dir)
    if sans is None:
        print("Source Sans 3 (regular and semibold) not found: drawing the text with DejaVu Sans instead.")
        sans = {
            400: FontProperties(family="DejaVu Sans"),
            600: FontProperties(family="DejaVu Sans", weight="bold"),
        }
    else:
        print("Text font:", ", ".join(Path(str(p.get_file())).name for p in sans.values()))
    try:
        mono = FontProperties(
            fname=font_manager.findfont(FontProperties(family="Source Code Pro"), fallback_to_default=False)
        )
    except ValueError:
        mono = FontProperties(family="DejaVu Sans Mono")
    return sans, mono


# ---------------------------------------------------------------- logo (SVG circles and paths)

_TOKEN = re.compile(r"[MLHVCQZmlhvcqz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_NARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4, "Z": 0}


def svg_path(d: str, dx: float = 0.0, dy: float = 0.0) -> MPath:
    """A Matplotlib path from SVG path data (commands M, L, H, V, C, Q and Z, absolute or relative)."""
    verts: list[tuple[float, float]] = []
    codes: list[np.uint8] = []
    tokens = _TOKEN.findall(d)
    i, cmd = 0, ""
    x = y = sx = sy = 0.0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                verts.append((sx + dx, sy + dy))
                codes.append(MPath.CLOSEPOLY)
                x, y = sx, sy
                continue
        upper, rel = cmd.upper(), cmd.islower()
        args = [float(t) for t in tokens[i : i + _NARGS[upper]]]
        i += _NARGS[upper]
        if upper == "H":
            x = args[0] + (x if rel else 0.0)
            pts, code = [(x, y)], MPath.LINETO
        elif upper == "V":
            y = args[0] + (y if rel else 0.0)
            pts, code = [(x, y)], MPath.LINETO
        else:
            pts = [
                (args[k] + (x if rel else 0.0), args[k + 1] + (y if rel else 0.0))
                for k in range(0, len(args), 2)
            ]
            code = {"M": MPath.MOVETO, "L": MPath.LINETO, "C": MPath.CURVE4, "Q": MPath.CURVE3}[upper]
            x, y = pts[-1]
        if upper == "M":
            sx, sy = x, y
            cmd = "l" if rel else "L"  # further coordinate pairs after a moveto are linetos
        verts.extend((px + dx, py + dy) for px, py in pts)
        codes.extend([code] * len(pts))
    return MPath(verts, codes)


def draw_logo(ax: plt.Axes, x0: float, top: float, height: float) -> None:
    """Draw the logo lockup (mark and wordmark) with its top-left corner at (x0, top), in target pixels."""
    root = ET.parse(LOGO).getroot()
    scale = height / float(root.get("height", "64"))
    ns = "{http://www.w3.org/2000/svg}"
    for el in root:
        if el.tag == ns + "circle":
            cx, cy, r = (float(el.get(k, "0")) for k in ("cx", "cy", "r"))
            ax.add_patch(Circle((x0 + scale * cx, top + scale * cy), scale * r, color=el.get("fill"), lw=0))
        elif el.tag == ns + "path":
            dx = dy = 0.0
            if m := re.match(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)", el.get("transform", "")):
                dx, dy = float(m.group(1)), float(m.group(2))
            path = svg_path(el.get("d", ""), dx, dy)
            path = MPath(path.vertices * scale + (x0, top), path.codes)
            ax.add_patch(PathPatch(path, facecolor=el.get("fill"), lw=0))


# ---------------------------------------------------------------- text helpers (positions in target pixels)


def text(ax, x, y, s, prop, size, color, ha="left"):  # type: ignore[no-untyped-def]
    """Text with its baseline at y; size in target pixels."""
    return ax.text(x, y, s, fontproperties=prop, fontsize=size * PT, color=color, ha=ha, va="baseline")


def width(ax, artist) -> float:  # type: ignore[no-untyped-def]
    """Width of a text artist in target pixels."""
    bbox = artist.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    return float(bbox.width / SS)


def pill(ax, x: float, label: str, prop: FontProperties) -> float:  # type: ignore[no-untyped-def]
    """An outlined, rounded label; returns its right edge."""
    size = 20
    t = text(ax, x + PILL_PAD, PILL_TOP + PILL_H / 2 + 0.36 * size, label, prop, size, INK)
    w = width(ax, t) + 2 * PILL_PAD
    r = PILL_H / 2
    ax.add_patch(
        FancyBboxPatch(
            (x + r, PILL_TOP + r),
            w - 2 * r,
            0,
            boxstyle=f"round,pad={r}",
            facecolor=BG,
            edgecolor=TEAL,
            lw=2 * PT,
            zorder=1,
        )
    )
    t.set_zorder(2)
    return x + w


# ---------------------------------------------------------------- the orbit figure


def orbit_figure(fig: plt.Figure, result, label_font: FontProperties) -> None:  # type: ignore[no-untyped-def]
    """Top-down view of the nominal run: orbits, sampled positions and final positions of the planets."""
    nominal, run = result.realizations[0], result.runs[0]
    half = FIG_SIZE / 2
    ax = fig.add_axes(((FIG_X - half) / W, 1 - (FIG_Y + half) / H, FIG_SIZE / W, FIG_SIZE / H))
    ax.set_axis_off()
    a = nominal.semi_major_axes()
    lim = 1.075 * max(float(a[k]) * (1 + b.e) for k, b in enumerate(nominal.bodies))
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    k_lw = PT  # target pixels -> points
    for r, alpha in ((0.0042, 0.16), (0.0030, 0.28), (0.0019, 1.0)):  # the star, in AU, with a soft glow
        ax.add_patch(Circle((0, 0), r, color=AMBER, alpha=alpha, lw=0, zorder=4))
    f = np.linspace(0, 2 * np.pi, 720)
    ends = []
    for k, b in enumerate(nominal.bodies):
        ak = float(a[k])
        r = ak * (1 - b.e**2) / (1 + b.e * np.cos(f))
        ax.plot(
            r * np.cos(f + b.pomega), r * np.sin(f + b.pomega), color=INK, lw=1.3 * k_lw, alpha=0.6, zorder=2
        )
        xs, ys = np.asarray(run.series[f"x{k}"]), np.asarray(run.series[f"y{k}"])
        ax.scatter(xs, ys, s=(2.6 * k_lw) ** 2, color=TEAL, alpha=0.55, lw=0, zorder=3)
        ax.scatter(
            [xs[-1]], [ys[-1]], s=(13 * k_lw) ** 2, color=AMBER, edgecolor=INK, lw=1.8 * k_lw, zorder=6
        )
        ends.append(float(np.arctan2(ys[-1], xs[-1])))
    # Orbit labels on one ray, at the angle farthest from every planet's final position.
    angles = np.radians(np.arange(0.0, 360.0, 1.0))
    gap = [min(abs((c - e + np.pi) % (2 * np.pi) - np.pi) for e in ends) for c in angles]
    ang = float(angles[int(np.argmax(gap))])
    for k, b in enumerate(nominal.bodies):
        ak = float(a[k])
        ax.text(
            ak * np.cos(ang),
            ak * np.sin(ang),
            b.name.split()[-1],
            color=MUTED,
            fontproperties=label_font,
            fontsize=16 * PT,
            ha="center",
            va="center",
            zorder=7,
            bbox={"boxstyle": "round,pad=0.18", "fc": PANEL, "ec": "none"},
        )


# ---------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--font-dir", default=os.environ.get("EXOSTAB_FONT_DIR"), help="folder with Source Sans 3"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT, help=f"output PNG (default: {OUT.relative_to(ROOT)})"
    )
    args = parser.parse_args()

    sans, mono = fonts(args.font_dir)
    # The run `exostab check` makes with its default settings.
    result = check_system(load_system(SYSTEM, offline=True), CheckSettings())
    rep = result.report
    t_end = result.runs[0].t_end
    n_planets = len(result.realizations[0].bodies)
    print(
        f"{SYSTEM}: {n_planets} planets, nominal run {result.runs[0].status} over {t_end:.1f} yr, "
        f"overall {rep.overall.verdict.value} (data: {rep.data.source}, {rep.data.retrieved_utc})"
    )

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100 * SS, facecolor=BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.set_axis_off()
    ax.add_patch(Circle((FIG_X, FIG_Y), FIG_SIZE / 2 * 0.985, color=PANEL, lw=0))
    draw_logo(ax, X0, LOGO_TOP, LOGO_H)
    lines = [text(ax, X0, TAG_Y + i * TAG_DY, line, sans[600], 46, INK) for i, line in enumerate(TAGLINE)]
    lines.append(text(ax, X0, TAG_Y + len(TAGLINE) * TAG_DY - 8, SUBLINE, sans[400], 21, MUTED))
    # A wider fallback font must not run into the figure: shrink the text column to fit if needed.
    column = FIG_X - FIG_SIZE / 2 - 24 - X0
    widest = max(width(ax, t) for t in lines)
    if widest > column:
        for t in lines:
            t.set_fontsize(t.get_fontsize() * column / widest)
    x = float(X0)
    for label in PILLS:
        x = pill(ax, x, label, sans[600]) + PILL_GAP
    text(ax, X0, URL_Y, URL, sans[600], 20, MUTED)

    # Caption under the figure: what it shows, then the command and the data it came from.
    text(ax, FIG_X, CAPTION_Y, f"{SYSTEM} · {n_planets} planets · {t_end:.1f} yr of N-body integration",
         sans[600], 15.5, INK, ha="center")  # fmt: skip
    y2, pad = CAPTION_Y + 25, 7
    cmd = text(ax, 0, y2, COMMAND, mono, 14, INK)
    note = text(ax, 0, y2, "   ·   " + DATA_NOTE, sans[400], 14.5, MUTED)
    w_cmd = width(ax, cmd) + 2 * pad
    x_left = FIG_X - (w_cmd + width(ax, note)) / 2
    cmd.set_x(x_left + pad)
    note.set_x(x_left + w_cmd)
    ax.add_patch(
        FancyBboxPatch(
            (x_left, y2 - 15), w_cmd, 21, boxstyle="round,pad=0,rounding_size=5", fc=PANEL, ec="none"
        )
    )
    orbit_figure(fig, result, sans[600])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100 * SS, facecolor=BG)
    plt.close(fig)
    img = Image.open(buf).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out, optimize=True)
    print(f"wrote {args.out} ({img.width} x {img.height}, {args.out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
