"""The batch catalog: same verdicts as `exostab check`, and every host accounted for."""

from __future__ import annotations

import pytest

from exostab.analysis import CheckSettings, check_system
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
