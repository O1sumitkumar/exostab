"""Pure helpers of the web app: the editable parameter table, "what if" adjustments, shareable links and
the cache key. Kept free of Streamlit so they can be unit-tested.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from ..models import CompletionFlag, MassKind, Provenance, System, Value

BUDGET_MIN, BUDGET_MAX, BUDGET_DEFAULT = 5, 120, 10
MASS_FACTORS = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0)


@dataclass
class WhatIf:
    """Adjustments of one planet on top of the table: mass factor, eccentricity, period ratio to the planet
    just inside it."""

    planet: str | None = None
    mass_factor: float = 1.0
    eccentricity: float | None = None
    period_ratio: float | None = None

    def is_active(self) -> bool:
        return self.planet is not None and (
            self.mass_factor != 1.0 or self.eccentricity is not None or self.period_ratio is not None
        )


@dataclass
class AppState:
    """Everything the shareable link must reproduce."""

    system: str = "TRAPPIST-1"
    source: str = "archive"  # "archive" or "snapshot"
    edits: dict[str, dict[str, float | None]] = field(default_factory=dict)  # planet -> column -> value
    whatif: WhatIf = field(default_factory=WhatIf)
    budget_s: float = BUDGET_DEFAULT
    seed: int = 0
    prior: str = "none"
    orbits: float | None = None  # exact run length of a finished run (makes a shared link reproducible)
    draws: int | None = None
    run: bool = False


EDITABLE = ("period_days", "mass_earth", "eccentricity", "omega_deg")


def planet_rows(system: System) -> list[dict[str, Any]]:
    """Rows for the editable table (one per planet)."""
    rows = []
    for p in system.planets:
        rows.append(
            {
                "planet": p.name,
                "period_days": p.period_days.value,
                "mass_earth": p.mass_earth.value,
                "mass_kind": p.mass_kind.value,
                "eccentricity": p.eccentricity.value,
                "omega_deg": p.omega_deg.value if p.omega_deg.is_known else None,
                "phase": p.phase.kind.value.replace("_", " "),
            }
        )
    return rows


def table_edits(system: System, rows: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Cells of the table that differ from the system's published values."""
    base = {r["planet"]: r for r in planet_rows(system)}
    edits: dict[str, dict[str, float | None]] = {}
    for r in rows:
        orig = base.get(r["planet"])
        if orig is None:
            continue
        for col in EDITABLE:
            new, old = r.get(col), orig[col]
            new = None if new is None or (isinstance(new, float) and math.isnan(new)) else float(new)
            if new != old and not (
                new is not None and old is not None and math.isclose(new, old, rel_tol=1e-12)
            ):
                edits.setdefault(r["planet"], {})[col] = new
    return edits


def _edited(v: Value, new: float | None, *, randomize_if_none: bool = False) -> Value:
    if new is None:
        if randomize_if_none:
            return Value(provenance=Provenance.RANDOMIZED, reference="set to random in the web app")
        raise ValueError("a value is missing")
    return v.model_copy(
        update={"value": new, "provenance": Provenance.MEASURED, "reference": "edited in the web app"}
    )


def apply_changes(system: System, edits: dict[str, dict[str, float | None]], whatif: WhatIf) -> System:
    """The system with table edits and "what if" adjustments applied, each recorded as a completion flag."""
    planets = {p.name: p for p in system.planets}
    flags: list[CompletionFlag] = []
    for name, cols in edits.items():
        p = planets.get(name)
        if p is None:
            raise ValueError(f"unknown planet {name!r}")
        update: dict[str, Any] = {}
        for col, new in cols.items():
            if col not in EDITABLE:
                raise ValueError(f"column {col!r} cannot be edited")
            update[col] = _edited(getattr(p, col), new, randomize_if_none=col == "omega_deg")
            shown = "random" if new is None else f"{new:g}"
            flags.append(
                CompletionFlag(
                    planet=name,
                    parameter=col,
                    rule="edited_in_web_app",
                    message=f"{col.replace('_', ' ')} set to {shown} in the web app (published: "
                    f"{_fmt(getattr(p, col))}).",
                )
            )
        planets[name] = p.model_copy(update=update)
    if whatif.is_active():
        assert whatif.planet is not None
        p = planets.get(whatif.planet)
        if p is None:
            raise ValueError(f"unknown planet {whatif.planet!r}")
        update = {}
        notes = []
        if whatif.mass_factor != 1.0:
            m = p.mass_earth.require() * whatif.mass_factor
            update["mass_earth"] = _edited(p.mass_earth, m)
            if p.mass_kind is MassKind.ESTIMATED:
                update["mass_kind"] = MassKind.TRUE
            notes.append(f"mass × {whatif.mass_factor:g} = {m:.4g} Earth masses")
        if whatif.eccentricity is not None:
            update["eccentricity"] = _edited(p.eccentricity, whatif.eccentricity)
            notes.append(f"e = {whatif.eccentricity:g}")
        if whatif.period_ratio is not None:
            ordered = sorted(planets.values(), key=lambda q: q.period_days.require())
            k = [q.name for q in ordered].index(p.name)
            if k == 0:
                raise ValueError("the period ratio applies to a planet outside another one")
            inner = ordered[k - 1].period_days.require()
            update["period_days"] = _edited(p.period_days, inner * whatif.period_ratio)
            notes.append(f"period ratio to {ordered[k - 1].name} = {whatif.period_ratio:g}")
        planets[p.name] = p.model_copy(update=update)
        flags.append(
            CompletionFlag(
                planet=p.name,
                parameter="what-if",
                rule="what_if_in_web_app",
                message="What-if adjustment in the web app: " + "; ".join(notes) + ".",
            )
        )
    # Re-validate: model_copy() skips the checks (positive values, 0 <= e < 1, ordered and unique planets).
    ordered_planets = sorted(planets.values(), key=lambda q: q.period_days.require())
    data = system.model_dump()
    data["planets"] = [q.model_dump() for q in ordered_planets]
    data["flags"] = [f.model_dump() for f in (*system.flags, *flags)]
    return System.model_validate(data)


def _fmt(v: Value) -> str:
    if v.provenance is Provenance.RANDOMIZED or v.value is None:
        return "random"
    return f"{v.value:g}"


# ------------------------------------------------------------------------------------------ shareable links


def _b64(obj: Any) -> str:
    raw = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> Any:
    pad = "=" * (-len(text) % 4)
    return json.loads(base64.urlsafe_b64decode(text + pad).decode())


def encode_state(state: AppState) -> dict[str, str]:
    """Query parameters for a shareable link."""
    q = {"system": state.system, "budget": f"{state.budget_s:g}", "seed": str(state.seed)}
    if state.source != "archive":
        q["source"] = state.source
    if state.prior != "none":
        q["prior"] = state.prior
    if state.edits:
        q["edits"] = _b64(state.edits)
    if state.whatif.is_active():
        q["whatif"] = _b64(asdict(state.whatif))
    if state.orbits is not None and state.draws is not None:
        q["orbits"] = f"{state.orbits:g}"
        q["draws"] = str(state.draws)
    if state.run:
        q["run"] = "1"
    return q


def decode_state(params: dict[str, str]) -> AppState:
    """AppState from query parameters; invalid values fall back to the defaults."""
    s = AppState()
    s.system = params.get("system", s.system)[:200]
    if params.get("source") in ("archive", "snapshot"):
        s.source = params["source"]
    if params.get("prior") in ("none", "isotropic"):
        s.prior = params["prior"]
    with contextlib.suppress(ValueError):
        s.budget_s = min(max(float(params.get("budget", s.budget_s)), BUDGET_MIN), BUDGET_MAX)
    with contextlib.suppress(ValueError):
        s.seed = int(params.get("seed", s.seed))
    try:
        if "edits" in params:
            raw = _unb64(params["edits"])
            s.edits = {
                str(p): {str(c): (None if v is None else float(v)) for c, v in cols.items() if c in EDITABLE}
                for p, cols in raw.items()
            }
        if "whatif" in params:
            raw = _unb64(params["whatif"])
            factor = raw.get("mass_factor")
            s.whatif = WhatIf(
                planet=None if raw.get("planet") is None else str(raw["planet"]),
                mass_factor=1.0 if factor is None else float(factor),
                eccentricity=None if raw.get("eccentricity") is None else float(raw["eccentricity"]),
                period_ratio=None if raw.get("period_ratio") is None else float(raw["period_ratio"]),
            )
    except (ValueError, TypeError, AttributeError):
        s.edits, s.whatif = {}, WhatIf()
    try:
        if "orbits" in params and "draws" in params:
            s.orbits, s.draws = float(params["orbits"]), int(params["draws"])
            if not (10 <= s.orbits <= 1e7 and 0 <= s.draws <= 500):
                s.orbits = s.draws = None
    except ValueError:
        s.orbits = s.draws = None
    s.run = params.get("run") == "1"
    return s


def share_url(base: str, state: AppState) -> str:
    from urllib.parse import urlencode

    return base.rstrip("/") + "/?" + urlencode(encode_state(replace(state, run=True)))


def input_hash(system: System, settings: dict[str, Any]) -> str:
    """SHA-256 of every input of a run: the system (values, errors, flags) and the settings."""
    payload = json.dumps({"system": system.model_dump(mode="json"), "settings": settings}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
