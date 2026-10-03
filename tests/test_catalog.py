"""The batch catalog: same verdicts as `exostab check`, and every host accounted for."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exostab.analysis import CheckSettings, check_system
from exostab.catalog import build
from exostab.catalog.build import CatalogSettings, check_one
from exostab.data import load_rows, system_from_rows
from exostab.data.archive import group_by_host


@pytest.mark.parametrize("host", ["HD 82943", "HD 10180"])
def test_catalog_row_matches_exostab_check(host: str) -> None:
    """The catalog keeps no time series, but its energy check and verdicts are those of `exostab check`."""
    rows, info = load_rows()
    rs = group_by_host(rows)[host]
    settings = CatalogSettings(orbits=500, draws=2, seed=0)
    row = check_one(rs, info, settings)
    res = check_system(system_from_rows(rs, info), CheckSettings(orbits=500, draws=2, seed=0, jobs=1))
    rep = res.report
    assert row["status"] == "ok"
    assert row["overall"] == rep.overall.verdict.value
    assert [row[k] for k in ("hill", "amd", "nbody")] == [
        rep.indicators[k].verdict.value for k in ("hill", "amd", "nbody")
    ]
    assert row["energy_error_nominal"] == res.runs[0].energy_error
    assert row["megno_nominal"] == res.runs[0].megno
    counts = rep.indicators["nbody"].details["classification_counts"]
    assert [row[f"nbody_{c}"] for c in counts] == list(counts.values())


def test_hosts_with_a_single_planet_row_are_recorded_as_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sy_pnum >= 2 also selects hosts whose other planets orbit a companion star (e.g. WASP-94 A)."""
    rows, info = load_rows()
    hosts = group_by_host(rows)
    lonely = {**hosts["HD 82943"][0], "hostname": "Lonely A"}
    monkeypatch.setattr(build, "load_rows", lambda **_: ([*hosts["Kepler-47"], lonely], info))
    _, out = build.build_catalog(CatalogSettings(orbits=100, draws=0, jobs=2), tmp_path)
    by_host = {r["system"]: r for r in out}
    assert set(by_host) == {"Kepler-47", "Lonely A"}
    assert by_host["Lonely A"]["status"] == "skipped" and by_host["Lonely A"]["n_planets"] == 1
    assert "only one planet around Lonely A" in by_host["Lonely A"]["reason"]
    assert json.loads((tmp_path / "catalog_meta.json").read_text())["n_systems"] == 2
