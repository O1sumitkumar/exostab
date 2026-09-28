import math

import pytest
import rebound

from exostab import units


def test_rebound_and_astropy_agree_on_G_in_simulation_units() -> None:
    sim = rebound.Simulation()
    sim.units = units.SIM_UNITS
    assert sim.G == pytest.approx(units.G_SIM, rel=1e-8)
    # Gaussian gravitational constant check: G ~ 4 pi^2 in AU^3 / (Msun yr^2) for a Julian year.
    assert units.G_SIM == pytest.approx(4 * math.pi**2, rel=1e-4)


def test_day_and_year_are_julian() -> None:
    assert units.DAY_IN_YR == pytest.approx(1 / 365.25, rel=1e-15)
    assert units.years_to_days(units.days_to_years(123.4)) == pytest.approx(123.4)


def test_mass_conversions() -> None:
    assert units.MJUP_IN_MEARTH == pytest.approx(317.8, rel=1e-3)
    assert units.msun_to_mearth(units.mearth_to_msun(5.0)) == pytest.approx(5.0)


def test_kepler_third_law_roundtrip_and_earth() -> None:
    assert units.period_from_semimajor_axis(1.0, 1.0) == pytest.approx(1.0, rel=1e-4)
    p = 0.37
    assert units.period_from_semimajor_axis(units.semimajor_axis_from_period(p, 0.8), 0.8) == pytest.approx(p)


def test_rebound_period_matches_units_module() -> None:
    sim = rebound.Simulation()
    sim.units = units.SIM_UNITS
    sim.add(m=1.0)
    sim.add(m=0.0, a=2.0)
    assert sim.particles[1].P == pytest.approx(units.period_from_semimajor_axis(2.0, 1.0), rel=1e-8)
