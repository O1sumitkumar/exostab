import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from exostab.data import massradius as mr


def test_terran_constant_and_transitions() -> None:
    assert mr.radius_from_mass(1.0) == pytest.approx(1.008)
    assert mr.R_T1 == pytest.approx(1.23, abs=0.005)  # quoted as 1.23 R_earth by Chen & Kipping (2017)
    assert mr.R_T2 == pytest.approx(14.3, abs=0.05)


def test_log_intercepts_match_the_archive_documentation() -> None:
    # The NASA Exoplanet Archive (pscp_calc.html) lists the same relation as log10 R = C + S log10 M with
    # C = 0.00346, -0.0925, 1.25, -2.85 for the four classes (continuity at the transitions).
    def intercept(m: float, s: float) -> float:
        return math.log10(mr.radius_from_mass(m)) - s * math.log10(m)

    assert intercept(1.0, mr.S[0]) == pytest.approx(0.00346, abs=5e-5)
    assert intercept(10.0, mr.S[1]) == pytest.approx(-0.0925, abs=5e-4)
    assert intercept(1000.0, mr.S[2]) == pytest.approx(1.25, abs=5e-3)
    assert intercept(1e5, mr.S[3]) == pytest.approx(-2.85, abs=1e-2)


def test_relation_is_continuous() -> None:
    for t in (mr.T1, mr.T2, mr.T3):
        assert mr.radius_from_mass(t * (1 - 1e-9)) == pytest.approx(
            mr.radius_from_mass(t * (1 + 1e-9)), rel=1e-6
        )


@given(st.floats(min_value=0.05, max_value=11.0))
def test_inversion_roundtrip(r: float) -> None:
    assert mr.radius_from_mass(mr.mass_from_radius(r)) == pytest.approx(r, rel=1e-9)


@pytest.mark.parametrize("r", [11.5, 13.0, 20.0, 32.6])
def test_giant_radii_are_refused(r: float) -> None:
    with pytest.raises(mr.MassRadiusError, match="unique mass"):
        mr.mass_from_radius(r)


@pytest.mark.parametrize("r", [0.0, -1.0, math.nan])
def test_invalid_radius(r: float) -> None:
    with pytest.raises(mr.MassRadiusError):
        mr.mass_from_radius(r)
    with pytest.raises(ValueError, match="positive"):
        mr.radius_from_mass(-1.0)
