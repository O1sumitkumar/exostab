"""Planet mass from radius with the Chen & Kipping (2017) mass-radius relation.

Chen & Kipping (2017, ApJ 834, 17) fit a continuous broken power law, log10(R/R_earth) = C + S log10(M/M_earth),
with four classes. Posterior values from their Table 1 (``hyper_table.tex`` in the arXiv source,
arXiv:1603.08614):

* Terran worlds, M < 2.04 M_earth: R = 1.008 R_earth (M/M_earth)^0.2790
* Neptunian worlds, 2.04 M_earth < M < 0.414 M_jup: index 0.589
* Jovian worlds, 0.414 M_jup < M < 0.0800 M_sun: index -0.044
* Stellar worlds, above 0.0800 M_sun: index 0.881

The segments join continuously at the transition points. We use only the mean relation (the paper's
intrinsic radius scatter of 4-15% is not propagated) and invert it for the mass. In the Jovian class the
radius is almost independent of mass (index -0.044, "nearly degenerate" in the authors' words), and
radii between the smallest Jovian radius and the Neptunian-Jovian transition radius map to two masses,
so no mass is estimated for radii above ``R_MAX_UNIQUE``: the user must supply one.
"""

from __future__ import annotations

import math

from ..units import MEARTH_IN_MSUN, MJUP_IN_MEARTH

C_TERRAN = 1.008  # R_earth, radius at 1 M_earth
S = (0.2790, 0.589, -0.044, 0.881)  # power-law indices (Terran, Neptunian, Jovian, Stellar)
T1 = 2.04  # M_earth, Terran -> Neptunian
T2 = 0.414 * MJUP_IN_MEARTH  # M_earth, Neptunian -> Jovian
T3 = 0.0800 / MEARTH_IN_MSUN  # M_earth, Jovian -> Stellar


class MassRadiusError(ValueError):
    """The radius does not determine a unique mass."""


def radius_from_mass(m_earth: float) -> float:
    """Mean radius (R_earth) for mass ``m_earth`` (M_earth) on the continuous broken power law."""
    if m_earth <= 0:
        raise ValueError("mass must be positive")
    r1 = C_TERRAN * T1 ** S[0]
    r2 = r1 * (T2 / T1) ** S[1]
    r3 = r2 * (T3 / T2) ** S[2]
    if m_earth <= T1:
        return float(C_TERRAN * m_earth ** S[0])
    if m_earth <= T2:
        return float(r1 * (m_earth / T1) ** S[1])
    if m_earth <= T3:
        return float(r2 * (m_earth / T2) ** S[2])
    return float(r3 * (m_earth / T3) ** S[3])


R_T1 = radius_from_mass(T1)  # about 1.23 R_earth
R_T2 = radius_from_mass(T2)  # radius at the Neptunian-Jovian transition, about 14.3 R_earth
R_MAX_UNIQUE = radius_from_mass(T3)  # smallest Jovian radius, about 11.3 R_earth


def mass_from_radius(r_earth: float) -> float:
    """Mass (M_earth) for radius ``r_earth`` (R_earth), Terran and Neptunian classes only."""
    if not r_earth > 0 or not math.isfinite(r_earth):
        raise MassRadiusError(f"radius must be positive, got {r_earth}")
    if r_earth > R_MAX_UNIQUE:
        raise MassRadiusError(
            f"its radius ({r_earth:.3g} Earth radii) is in the giant-planet range where the Chen & Kipping (2017) "
            f"relation does not give a unique mass (radii above {R_MAX_UNIQUE:.3g} Earth radii); supply a mass"
        )
    if r_earth <= R_T1:
        return float((r_earth / C_TERRAN) ** (1 / S[0]))
    return float(T1 * (r_earth / R_T1) ** (1 / S[1]))
