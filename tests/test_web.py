"""Web app: pure helpers and a headless run of the Streamlit app (offline snapshot)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest

from conftest import two_planet_system
from exostab.analysis import CheckSettings, check_system
from exostab.data import load_system
from exostab.models import Provenance
from exostab.web import figures
from exostab.web.state import (
    AppState,
    WhatIf,
    apply_changes,
    decode_state,
    encode_state,
    input_hash,
    planet_rows,
    share_url,
    table_edits,
)

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_table_roundtrip_and_edits() -> None:
    s = two_planet_system(e=(0.1, 0.2))
    rows = planet_rows(s)
    assert [r["planet"] for r in rows] == ["Test b", "Test c"]
    assert table_edits(s, rows) == {}
    rows[1]["eccentricity"] = 0.3
    rows[0]["omega_deg"] = None
    edits = table_edits(s, rows)
    assert edits == {"Test c": {"eccentricity": 0.3}, "Test b": {"omega_deg": None}}
    changed = apply_changes(s, edits, WhatIf())
    assert changed.planet("c").eccentricity.value == 0.3
    assert changed.planet("b").omega_deg.provenance is Provenance.RANDOMIZED
    assert {f.rule for f in changed.flags} == {"edited_in_web_app"}


def test_what_if_adjustments() -> None:
    s = two_planet_system(period_ratio=2.0)
    w = WhatIf(planet="Test c", mass_factor=3.0, eccentricity=0.25, period_ratio=1.5)
    changed = apply_changes(s, {}, w)
    c = changed.planet("c")
    assert c.mass_earth.value == pytest.approx(30.0)
    assert c.eccentricity.value == 0.25
    assert c.period_days.value == pytest.approx(150.0)
    assert any(f.rule == "what_if_in_web_app" for f in changed.flags)
    # a period ratio below the next planet reorders the planets, which must stay sorted
    s3 = two_planet_system(period_ratio=3.0)
    moved = apply_changes(s3, {"Test b": {"period_days": 400.0}}, WhatIf())
    assert [p.name for p in moved.planets] == ["Test c", "Test b"]
    with pytest.raises(ValueError, match="outside another"):
        apply_changes(s, {}, WhatIf(planet="Test b", period_ratio=1.5))
    with pytest.raises(ValueError, match="eccentricity"):
        apply_changes(s, {"Test b": {"eccentricity": 1.5}}, WhatIf())
    with pytest.raises(ValueError, match="unknown planet"):
        apply_changes(s, {"X": {"eccentricity": 0.1}}, WhatIf())
    with pytest.raises(ValueError, match="cannot be edited"):
        apply_changes(s, {"Test b": {"mass_kind": 1.0}}, WhatIf())
    with pytest.raises(ValueError, match="missing"):
        apply_changes(s, {"Test b": {"eccentricity": None}}, WhatIf())
    assert not WhatIf(planet="Test b").is_active()


def test_share_link_roundtrip() -> None:
    st = AppState(
        system="HD 127195",
        source="snapshot",
        edits={"HD 127195 b": {"eccentricity": 0.1}},
        whatif=WhatIf(planet="HD 127195 c", mass_factor=2.0),
        budget_s=30,
        seed=7,
        prior="isotropic",
        orbits=5000.0,
        draws=10,
    )
    back = decode_state(encode_state(st))
    assert back == st
    url = share_url("https://example.org/app/", st)
    assert url.startswith("https://example.org/app/?") and "run=1" in url


def test_decode_rejects_garbage() -> None:
    s = decode_state(
        {
            "system": "X",
            "budget": "abc",
            "seed": "x",
            "edits": "!!!",
            "orbits": "1e12",
            "draws": "5",
            "source": "hack",
            "prior": "weird",
        }
    )
    assert (s.system, s.budget_s, s.seed, s.edits, s.orbits, s.source, s.prior) == (
        "X",
        10,
        0,
        {},
        None,
        "archive",
        "none",
    )
    assert decode_state({"budget": "1000"}).budget_s == 120
    assert decode_state({"orbits": "x", "draws": "1"}).orbits is None


def test_input_hash_changes_with_any_input() -> None:
    s = two_planet_system()
    h = input_hash(s, {"seed": 0})
    assert h == input_hash(two_planet_system(), {"seed": 0})
    assert h != input_hash(s, {"seed": 1})
    assert h != input_hash(two_planet_system(e=(0.0, 0.01)), {"seed": 0})


def test_plotly_figures() -> None:
    res = check_system(load_system("Kepler-36"), CheckSettings(orbits=200, draws=3, jobs=1, n_samples=20))
    assert len(figures.orbits(res.realizations[0], res.runs[0], "K").data) == 1 + 2 * 2
    assert len(figures.megno_time(res.runs[0], res.ias15, "K").data) == 4
    assert figures.megno_draws(res.runs).data


def test_app_runs_headless() -> None:
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params.update(
        {"system": "Kepler-36", "source": "snapshot", "orbits": "300", "draws": "2", "run": "1"}
    )
    at.run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Overall:" in text
    assert len(at.get("download_button")) == 3
    assert any("orbits=300" in c.value for c in at.code)
    # an unknown system gives a clear error instead of a crash
    at2 = AppTest.from_file(APP, default_timeout=60)
    at2.query_params.update({"system": "Nonexistent-99", "source": "snapshot"})
    at2.run()
    assert not at2.exception and at2.error and "No multi-planet system" in at2.error[0].value


def test_app_rejects_circumbinary_and_reports_json() -> None:
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params.update({"system": "Kepler-47", "source": "snapshot"})
    at.run()
    assert at.error and "circumbinary" in at.error[0].value
    # report.json produced by the app is a valid report
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params.update(
        {"system": "Kepler-36", "source": "snapshot", "orbits": "200", "draws": "1", "run": "1"}
    )
    at.run()
    data = at.get("download_button")[0].proto.url  # served from the media file manager
    assert data
    rep = json.loads(
        check_system(load_system("Kepler-36"), CheckSettings(orbits=200, draws=1, jobs=1)).report.to_json()
    )
    assert rep["settings"]["orbits"] == 200
