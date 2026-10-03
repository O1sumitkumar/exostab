from pathlib import Path

import pytest

from conftest import EXAMPLES
from exostab.data import IncompleteSystemError, SystemFileError, load_system_file
from exostab.models import MassKind, PhaseKind, Provenance
from exostab.units import MJUP_IN_MEARTH


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "s.yaml"
    p.write_text(text)
    return p


GOOD = """
name: T
star: {mass_msun: 1.0}
planets:
  - {name: T b, period_days: 10, mass_earth: 5}
  - {name: T c, period_days: 30, mass_earth: 8}
"""


def test_examples_load() -> None:
    s = load_system_file(EXAMPLES / "two_planet.yaml")
    assert s.epoch_jd == 2460000.0
    c = s.planet("c")
    assert c.mass_kind is MassKind.MINIMUM
    assert c.mass_earth.value == pytest.approx(0.5 * MJUP_IN_MEARTH)
    assert c.eccentricity.provenance is Provenance.UPPER_LIMIT
    assert c.phase.kind is PhaseKind.TRANSIT
    assert c.omega_deg.provenance is Provenance.RANDOMIZED
    hd = load_system_file(EXAMPLES / "hd127195_note.yaml")
    assert hd.planet("b").phase.kind is PhaseKind.MEAN_LONGITUDE
    assert hd.source.kind == "file" and hd.source.note


def test_defaults_and_flags(tmp_path: Path) -> None:
    s = load_system_file(write(tmp_path, GOOD))
    rules = {f.rule for f in s.flags}
    assert {"eccentricity_assumed_zero", "omega_randomized", "phase_randomized", "coplanar_assumed"} <= rules


def test_alternative_units_and_fields(tmp_path: Path) -> None:
    s = load_system_file(
        write(
            tmp_path,
            """
epoch_jd: 2450010.0
star: {mass_msun: {value: 1.0, err_plus: 0.1, err_minus: 0.05}}
planets:
  - {name: b, semimajor_axis_au: {value: 0.1, err: 0.001}, radius_earth: 1.5, mean_anomaly_deg: 10, omega_deg: 5}
  - {name: c, semimajor_axis_au: 0.2, mass_msun: 3.0e-6, periastron_time_jd: 2450000.0, eccentricity: 0.1,
     omega_deg: 30}
""",
        )
    )
    b, c = s.planets
    assert b.mass_kind is MassKind.ESTIMATED
    assert b.period_days.provenance is Provenance.DERIVED and b.period_days.has_errors
    assert not c.period_days.has_errors
    assert c.mass_earth.value == pytest.approx(0.9988, rel=1e-3)
    assert s.star.mass_msun.err_minus == 0.05
    assert s.name == "s"


@pytest.mark.parametrize(
    ("text", "error", "match"),
    [
        ("- a", SystemFileError, "mapping"),
        ("star: {mass_msun: 1}\nplanets: [{period_days: 1, mass_earth: 1}]", SystemFileError, "at least two"),
        ("planets: []", SystemFileError, "star"),
        (GOOD + "extra: 1", SystemFileError, "unknown top-level"),
        (GOOD.replace("mass_earth: 5", "mass_earth: 5, foo: 1"), SystemFileError, "unknown keys"),
        (GOOD.replace("mass_earth: 5", "mass_earth: 5, mass_jupiter: 1"), SystemFileError, "only one"),
        (GOOD.replace("mass_earth: 5", "mass_earth: {err: 1}"), SystemFileError, "missing 'value'"),
        (GOOD.replace("mass_earth: 5", "mass_earth: {value: 1, bad: 2}"), SystemFileError, "unknown keys"),
        (GOOD.replace("mass_earth: 5", "mass_earth: yes"), SystemFileError, "number"),
        (GOOD.replace("mass_earth: 5", "mass_earth: [1]"), SystemFileError, "number"),
        (GOOD.replace("mass_earth: 5", "mass_earth: {value: abc}"), SystemFileError, "could not convert"),
        (GOOD.replace("mass_earth: 5", "mass_earth: 5, mass_kind: weird"), SystemFileError, "mass_kind"),
        (GOOD.replace(", mass_earth: 5", ""), IncompleteSystemError, "give a mass"),
        (GOOD.replace(", mass_earth: 5", ", radius_earth: 13"), IncompleteSystemError, "giant-planet"),
        (GOOD.replace("period_days: 10, ", ""), IncompleteSystemError, "period_days"),
        (
            GOOD.replace("mass_earth: 5", "mass_earth: 5, mean_anomaly_deg: 1, mean_longitude_deg: 2"),
            SystemFileError,
            "at most one",
        ),
        (GOOD.replace("mass_earth: 5", "mass_earth: 5, eccentricity: 1.5"), SystemFileError, "eccentricity"),
        # a mean anomaly or a time of periastron places the planet relative to its periastron, whose direction
        # omega_deg gives; without it the planet's longitude would be random in every run
        (GOOD.replace("mass_earth: 5", "mass_earth: 5, mean_anomaly_deg: 30"), SystemFileError, "omega_deg"),
        (
            GOOD.replace("mass_earth: 5", "mass_earth: 5, periastron_time_jd: 2460000.0"),
            SystemFileError,
            "omega_deg",
        ),
        # invalid values give a SystemFileError naming the field, not a traceback
        (
            GOOD.replace("mass_msun: 1.0", "mass_msun: -1.0"),
            SystemFileError,
            "star: .*stellar mass must be positive",
        ),
        (
            GOOD.replace("period_days: 10", "semimajor_axis_au: 0"),
            SystemFileError,
            "semimajor_axis_au must be",
        ),
        (
            GOOD.replace("period_days: 10", "semimajor_axis_au: -0.3"),
            SystemFileError,
            "semimajor_axis_au must be",
        ),
        ("epoch_jd: 2460000 BJD\n" + GOOD, SystemFileError, "epoch_jd"),
        (GOOD.replace("name: T c", "name: T b"), SystemFileError, "unique"),
        ("star: [", SystemFileError, "not valid YAML"),
        ("star: {mass_msun: 1}\nplanets: [1, 2]", SystemFileError, "must be a mapping"),
    ],
)
def test_errors(tmp_path: Path, text: str, error: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match):
        load_system_file(write(tmp_path, text))


MIXED = """
name: Mix
star: {mass_msun: 1.0}
planets:
  - {name: Mix b, period_days: 10, mass_earth: 5, omega_deg: 0, mean_anomaly_deg: 10}
  - {name: Mix c, period_days: 25, mass_earth: 8, transit_time_jd: 2459000.0}
"""


def test_mean_anomalies_next_to_reference_times_need_an_epoch(tmp_path: Path) -> None:
    # A mean anomaly or longitude only means something at a stated epoch. Without epoch_jd it used to be taken
    # at whichever transit or periastron time choose_epoch picked, an arbitrary relative phase.
    with pytest.raises(SystemFileError, match="epoch_jd"):
        load_system_file(write(tmp_path, MIXED))
    with pytest.raises(SystemFileError, match="epoch_jd"):
        load_system_file(write(tmp_path, MIXED.replace("mean_anomaly_deg", "mean_longitude_deg")))
    s = load_system_file(write(tmp_path, "epoch_jd: 2459003.0\n" + MIXED))
    assert s.epoch_jd == 2459003.0
    # angles alone share a common, unspecified epoch, and reference times alone need none
    load_system_file(write(tmp_path, MIXED.replace("transit_time_jd: 2459000.0", "mean_longitude_deg: 90")))
    load_system_file(
        write(tmp_path, MIXED.replace("omega_deg: 0, mean_anomaly_deg: 10", "transit_time_jd: 2459001"))
    )


def test_missing_file() -> None:
    with pytest.raises(SystemFileError, match="cannot read"):
        load_system_file("/nonexistent/system.yaml")


def test_upper_limit_mass_flag(tmp_path: Path) -> None:
    s = load_system_file(
        write(tmp_path, GOOD.replace("mass_earth: 5", "mass_earth: {value: 5, upper_limit: true}"))
    )
    assert "mass_upper_limit" in {f.rule for f in s.flags}
