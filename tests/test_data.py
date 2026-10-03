"""Archive client, completion rules, cache/snapshot store and name matching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from astropy.table import MaskedColumn, Table

from exostab.data import (
    IncompleteSystemError,
    SystemNotFoundError,
    archive,
    completion,
    list_systems,
    load_rows,
    load_system,
    names,
    store,
    system_from_rows,
)
from exostab.data.store import TableInfo
from exostab.models import MassKind, PhaseKind, Provenance

INFO = TableInfo(kind="archive", retrieved_utc="2026-09-28T00:00:00+00:00", path=None)
REF_A = "<a refstr=A href=https://ui.adsabs.harvard.edu/abs/A/abstract target=ref>Alpha et al. 2020</a>"
REF_B = "<a refstr=B href=https://ui.adsabs.harvard.edu/abs/B/abstract target=ref>Beta et al. 2021</a>"


def row(name: str = "Host b", host: str = "Host", **kw: Any) -> dict[str, Any]:
    r: dict[str, Any] = dict.fromkeys(archive.COLUMN_NAMES)
    r.update(
        pl_name=name,
        hostname=host,
        pl_letter=name.split()[-1],
        sy_pnum=2,
        sy_snum=1,
        cb_flag=0,
        tran_flag=0,
        pl_orbper=10.0,
        pl_orbpererr1=0.01,
        pl_orbpererr2=-0.01,
        pl_orbper_reflink=REF_A,
        pl_orbeccen=0.1,
        pl_orbeccenerr1=0.02,
        pl_orbeccenerr2=-0.03,
        pl_orbeccenlim=0,
        pl_orbeccen_reflink=REF_A,
        pl_orblper=45.0,
        pl_orblper_reflink=REF_A,
        pl_bmasse=5.0,
        pl_bmasseerr1=0.5,
        pl_bmasseerr2=-0.5,
        pl_bmasselim=0,
        pl_bmassprov="Mass",
        pl_bmasse_reflink=REF_A,
        st_mass=1.0,
        st_masserr1=0.05,
        st_masserr2=-0.05,
        st_mass_reflink=REF_A,
    )
    r.update(kw)
    return r


def pair(**kw_c: Any) -> list[dict[str, Any]]:
    return [row("Host b"), row("Host c", **{"pl_orbper": 25.0, **kw_c})]


# ------------------------------------------------------------------------------------------ archive module


def test_parse_reflink() -> None:
    assert completion.parse_reflink(REF_A) == (
        "Alpha et al. 2020",
        "https://ui.adsabs.harvard.edu/abs/A/abstract",
    )
    assert completion.parse_reflink(None) == (None, None)
    assert completion.parse_reflink("Plain text") == ("Plain text", None)


def test_parse_reflink_unescapes_entities_and_resolves_relative_links() -> None:
    # Archive cells carry HTML entities, and archive-calculated values link to a page relative to the
    # archive site; report.json must hold plain text and links that work outside the archive.
    text, url = completion.parse_reflink(
        "<a refstr=X href=https://ui.adsabs.harvard.edu/abs/X/abstract target=ref>"
        "Su&aacute;rez Mascare&ntilde;o et al. 2025</a>"
    )
    assert text == "Suárez Mascareño et al. 2025"
    assert url == "https://ui.adsabs.harvard.edu/abs/X/abstract"
    assert completion.parse_reflink("<a href=x>Fulton &amp; Petigura 2018</a>")[0] == "Fulton & Petigura 2018"
    assert completion.parse_reflink("<a href=x>Kunovac Hod&#x17E;i&#x107; et al. 2021</a>")[0] == (
        "Kunovac Hodžić et al. 2021"
    )
    calc = "<a refstr=CALCULATED_VALUE href=/docs/pscp_calc.html target=_blank>Calculated Value</a>"
    assert completion.parse_reflink(calc) == (
        "Calculated Value",
        "https://exoplanetarchive.ipac.caltech.edu/docs/pscp_calc.html",
    )


def test_csv_roundtrip(tmp_path: Path) -> None:
    rows = pair()
    archive.write_csv(rows, tmp_path / "t.csv")
    back = archive.read_csv(tmp_path / "t.csv")
    assert back == rows


def test_read_csv_rejects_missing_columns(tmp_path: Path) -> None:
    (tmp_path / "bad.csv").write_text("pl_name,hostname\nx,y\n")
    with pytest.raises(archive.ArchiveError, match="lacks columns"):
        archive.read_csv(tmp_path / "bad.csv")


def test_rows_from_astropy_table_handles_masks_and_units() -> None:
    import astropy.units as u

    rows = pair()
    t = Table()
    for c, kind in archive.COLUMNS:
        vals = [r[c] for r in rows]
        if kind == "str":
            t[c] = MaskedColumn([v or "" for v in vals], mask=[v is None for v in vals])
        else:
            t[c] = MaskedColumn([np.nan if v is None else v for v in vals], mask=[v is None for v in vals])
    t["pl_orbper"].unit = u.day
    out = archive.rows_from_table(t)
    assert out[0]["pl_orbper"] == 10.0
    assert out[0]["pl_tranmid"] is None
    assert out[0]["sy_pnum"] == 2
    assert out[1]["pl_name"] == "Host c"
    with pytest.raises(archive.ArchiveError):
        archive.rows_from_table(Table({"pl_name": ["x"]}))


def test_clean_values() -> None:
    import astropy.units as u

    assert archive._clean(3 * u.day, "float") == 3.0
    assert archive._clean("  ", "str") is None
    assert archive._clean("abc", "float") is None
    assert archive._clean(float("nan"), "float") is None
    assert archive._clean(2.0, "int") == 2


def test_fetch_rows_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    calls = []

    def boom(**kw: Any) -> None:
        calls.append(kw)
        raise ConnectionError("no network")

    monkeypatch.setattr(NasaExoplanetArchive, "query_criteria", boom)
    with pytest.raises(archive.ArchiveError, match="no network"):
        archive.fetch_rows(attempts=2, pause=0.0)
    assert len(calls) == 2
    assert calls[0]["table"] == "pscomppars"


# ------------------------------------------------------------------------------------------ completion rules


def rules(rows: list[dict[str, Any]]) -> set[str]:
    return {f.rule for f in system_from_rows(rows, INFO).flags}


def test_complete_system_basic() -> None:
    s = system_from_rows(pair(), INFO)
    assert [p.name for p in s.planets] == ["Host b", "Host c"]
    b = s.planets[0]
    assert b.period_days.reference == "Alpha et al. 2020"
    assert b.eccentricity.err_minus == 0.03
    assert b.archive_name == "Host b"
    assert s.source.table == "pscomppars"
    assert "coplanar_assumed" in rules(pair())


def test_missing_eccentricity_and_omega() -> None:
    s = system_from_rows(pair(pl_orbeccen=None, pl_orblper=None), INFO)
    c = s.planets[1]
    assert c.eccentricity.value == 0.0 and c.eccentricity.provenance is Provenance.ASSUMED
    assert c.omega_deg.provenance is Provenance.RANDOMIZED
    assert {"eccentricity_assumed_zero", "omega_randomized"} <= {f.rule for f in s.flags}


def test_published_zero_eccentricity_without_errors_is_an_assumption() -> None:
    # e = 0 with no uncertainty is a circular orbit fixed in the source's fit (e.g. the DR25 KOI table),
    # not a measurement: it must be labelled and flagged like exostab's own e = 0 assumption.
    fixed = {
        "pl_orbeccen": 0.0,
        "pl_orbeccenerr1": None,
        "pl_orbeccenerr2": None,
        "pl_orbeccen_reflink": REF_B,
    }
    s = system_from_rows(pair(**fixed), INFO)
    c = s.planets[1]
    assert c.eccentricity.value == 0.0 and c.eccentricity.provenance is Provenance.ASSUMED
    assert c.eccentricity.reference == "Beta et al. 2021"
    flag = next(f for f in s.flags if f.rule == "eccentricity_fixed_zero_by_source")
    assert flag.planet == "Host c" and "Beta et al. 2021" in flag.message
    # zero error bars are no uncertainty either
    s = system_from_rows(pair(**{**fixed, "pl_orbeccenerr1": 0.0, "pl_orbeccenerr2": 0.0}), INFO)
    assert s.planets[1].eccentricity.provenance is Provenance.ASSUMED
    # a zero eccentricity with an error bar is a measurement
    s = system_from_rows(pair(pl_orbeccen=0.0, pl_orbeccenerr1=0.05, pl_orbeccenerr2=0.0), INFO)
    assert s.planets[1].eccentricity.provenance is Provenance.MEASURED
    assert "eccentricity_fixed_zero_by_source" not in {f.rule for f in s.flags}


def test_limits() -> None:
    s = system_from_rows(pair(pl_orbeccenlim=1, pl_bmasselim=1), INFO)
    c = s.planets[1]
    assert c.eccentricity.provenance is Provenance.UPPER_LIMIT
    assert c.mass_earth.provenance is Provenance.UPPER_LIMIT
    r = rules(pair(pl_orbeccenlim=-1, pl_bmasselim=-1, pl_orbperlim=-1))
    assert {"eccentricity_lower_limit", "mass_lower_limit", "period_lower_limit"} <= r


def test_bad_eccentricity_rejected() -> None:
    with pytest.raises(IncompleteSystemError, match="outside"):
        system_from_rows(pair(pl_orbeccen=1.2), INFO)


@pytest.mark.parametrize(
    ("prov", "kind", "rule"),
    [
        ("Mass", MassKind.TRUE, None),
        ("Msini", MassKind.MINIMUM, "minimum_mass"),
        ("M-R relationship", MassKind.ESTIMATED, "mass_estimated_by_archive"),
        ("Msin(i)/sin(i)", MassKind.TRUE, "mass_from_msini_and_inclination"),
    ],
)
def test_mass_provenance(prov: str, kind: MassKind, rule: str | None) -> None:
    s = system_from_rows(pair(pl_bmassprov=prov), INFO)
    assert s.planets[1].mass_kind is kind
    if rule:
        assert rule in {f.rule for f in s.flags}


def test_mass_from_radius_and_failures() -> None:
    s = system_from_rows(pair(pl_bmasse=None, pl_rade=2.0), INFO)
    assert s.planets[1].mass_kind is MassKind.ESTIMATED
    assert s.planets[1].mass_earth.value == pytest.approx(4.4, abs=0.3)
    with pytest.raises(IncompleteSystemError, match="giant-planet"):
        system_from_rows(pair(pl_bmasse=None, pl_rade=13.0), INFO)
    with pytest.raises(IncompleteSystemError, match="neither a mass nor a radius"):
        system_from_rows(pair(pl_bmasse=None, pl_rade=None), INFO)


def test_period_from_semimajor_axis() -> None:
    s = system_from_rows(
        pair(pl_orbper=None, pl_orbsmax=0.2, pl_orbsmaxerr1=0.01, pl_orbsmaxerr2=-0.01), INFO
    )
    c = s.planets[1]
    assert c.period_days.provenance is Provenance.DERIVED
    assert c.period_days.value == pytest.approx(0.2**1.5 * 365.25, rel=1e-3)
    assert c.period_days.err_plus == pytest.approx(1.5 * 0.05 * c.period_days.value)
    with pytest.raises(IncompleteSystemError, match="semi-major axis"):
        system_from_rows(pair(pl_orbper=None, pl_orbsmax=None), INFO)


def test_star_rules() -> None:
    with pytest.raises(IncompleteSystemError, match="circumbinary"):
        system_from_rows(pair(cb_flag=1), INFO)
    rows = pair()
    rows[0]["st_mass"] = None
    with pytest.raises(IncompleteSystemError, match="stellar mass"):
        system_from_rows(rows, INFO)
    rows = [row("Host b", sy_snum=2, st_masslim=1), row("Host c", pl_orbper=25.0)]
    assert {"companion_stars_ignored", "star_mass_upper_limit"} <= rules(rows)
    with pytest.raises(IncompleteSystemError, match="only one planet"):
        system_from_rows([row("Host b")], INFO)


def test_controversial_flag() -> None:
    assert "controversial_planet" in rules(pair(pl_controv_flag=1))


def test_phase_rules() -> None:
    # transiting: always from the transit time, noting a different reference
    s = system_from_rows(pair(tran_flag=1, pl_tranmid=2460000.0, pl_tranmid_reflink=REF_B), INFO)
    assert s.planets[1].phase.kind is PhaseKind.TRANSIT
    assert any("different publications" in f.message for f in s.flags)
    # non-transiting conjunction time: only from the same publication as the period
    s = system_from_rows(pair(pl_tranmid=2460000.0, pl_tranmid_reflink=REF_A), INFO)
    assert s.planets[1].phase.kind is PhaseKind.TRANSIT
    assert "phase_from_conjunction" in {f.rule for f in s.flags}
    s = system_from_rows(pair(pl_tranmid=2460000.0, pl_tranmid_reflink=REF_B), INFO)
    assert s.planets[1].phase.kind is PhaseKind.RANDOM
    assert any("different publication" in f.message for f in s.flags)
    # periastron time from the same publication
    s = system_from_rows(pair(pl_orbtper=2460001.0, pl_orbtper_reflink=REF_A), INFO)
    assert s.planets[1].phase.kind is PhaseKind.PERIASTRON
    # identical periastron times across planets are treated as an epoch, not a periastron time
    rows = [
        row("Host b", pl_orbtper=2450602.093, pl_orbtper_reflink=REF_A),
        row("Host c", pl_orbper=25.0, pl_orbtper=2450602.093, pl_orbtper_reflink=REF_A),
    ]
    s = system_from_rows(rows, INFO)
    assert all(p.phase.kind is PhaseKind.RANDOM for p in s.planets)
    assert any("likely an epoch" in f.message for f in s.flags)
    # nothing published
    s = system_from_rows(pair(), INFO)
    assert any("no transit, conjunction or periastron time" in f.message for f in s.flags)


# ------------------------------------------------------------------------------------------ store and names


def test_snapshot_loads_and_has_validation_systems() -> None:
    rows, info = load_rows()
    assert info.kind == "snapshot"
    hosts = archive.group_by_host(rows)
    for h in ("TRAPPIST-1", "HD 127195", "GJ 876", "Kepler-11"):
        assert h in hosts
    assert 18 <= len(hosts) <= 25


def test_every_snapshot_system_builds_or_is_rejected_with_a_reason() -> None:
    rows, info = load_rows()
    for host, rs in archive.group_by_host(rows).items():
        if host == "Kepler-47":  # circumbinary: rejected on purpose
            with pytest.raises(IncompleteSystemError, match="circumbinary"):
                system_from_rows(rs, info)
        else:
            assert len(system_from_rows(rs, info).planets) >= 2


def test_cache_roundtrip_and_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXOSTAB_OFFLINE")
    monkeypatch.setattr(store, "fetch_rows", lambda where: pair())
    rows, info = load_rows()
    assert info.kind == "archive" and rows == pair()
    meta = json.loads((store.cache_dir() / store.CACHE_META).read_text())
    assert meta["table"] == "pscomppars" and meta["n_rows"] == 2
    rows, info = load_rows()
    assert info.kind == "archive-cache" and rows == pair()
    rows, info = load_rows(refresh=True)
    assert info.kind == "archive"


def test_damaged_cache_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXOSTAB_OFFLINE")
    d = store.cache_dir()
    d.mkdir(parents=True)
    (d / store.CACHE_TABLE).write_text("garbage")
    (d / store.CACHE_META).write_text("{}")
    assert store.load_cache() is None


def test_network_failure_falls_back_to_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXOSTAB_OFFLINE")

    def fail(where: str) -> None:
        raise archive.ArchiveError("down")

    monkeypatch.setattr(store, "fetch_rows", fail)
    _, info = load_rows()
    assert info.kind == "snapshot" and "unreachable" in (info.note or "")
    with pytest.raises(archive.ArchiveError):
        load_rows(refresh=True)


def test_offline_flag_and_env() -> None:
    assert store.offline_requested()
    assert load_rows(offline=True)[1].kind == "snapshot"


def test_name_resolution() -> None:
    assert names.normalize("TRAPPIST-1") == names.normalize("trappist 1") == "trappist1"
    s = load_system("trappist 1")
    assert s.name == "TRAPPIST-1" and len(s.planets) == 7
    assert load_system("Kepler-11 b").name == "Kepler-11"
    with pytest.raises(SystemNotFoundError) as err:
        load_system("TRAPIST-1")
    assert "TRAPPIST-1" in err.value.suggestions
    with pytest.raises(SystemNotFoundError, match="No multi-planet system"):
        load_system("Nonexistent-999")
    assert names.all_names(["b", "A", "c"]) == ["A", "b", "c"]


def test_list_systems_filters() -> None:
    rows, _ = load_rows()
    all_ = list_systems(rows)
    assert all(s.n_planets >= 2 for s in all_)
    four = list_systems(rows, min_planets=4, max_period_days=200)
    assert four and all(s.n_planets >= 4 and (s.max_period_days or 0) <= 200 for s in four)
    assert "TRAPPIST-1" in {s.host for s in four}
    assert "HD 127195" not in {s.host for s in four}
    hd = next(s for s in all_ if s.host == "HD 127195")
    assert hd.minimum_masses == 2
