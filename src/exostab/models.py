"""Data models for stars, planets and systems.

Every number carries its provenance: whether it was published (``measured``), computed from other
published numbers (``derived``), filled in by a completion rule (``assumed`` / ``estimated``), drawn at
random for each run (``randomized``), or is only an upper limit. The completion rules that produce
these labels live in :mod:`exostab.data.completion`; every rule that fires also adds a
:class:`CompletionFlag` to the system, and the flags are printed in every report.

Units are part of the field names (``period_days``, ``mass_earth``, ``omega_deg`` ...). Conversion to
the simulation units (yr, AU, Msun) happens in one place, :mod:`exostab.units`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Provenance(str, Enum):
    """Where a value came from."""

    MEASURED = "measured"
    DERIVED = "derived"
    ASSUMED = "assumed"
    ESTIMATED = "estimated"
    RANDOMIZED = "randomized"
    UPPER_LIMIT = "upper_limit"


class MassKind(str, Enum):
    """What a planet mass means."""

    TRUE = "true"
    MINIMUM = "minimum"  # m sin i from radial velocities
    ESTIMATED = "estimated"  # from a mass-radius relation


class PhaseKind(str, Enum):
    """How the orbital phase of a planet at the common epoch is known."""

    TRANSIT = "transit"  # time of mid-transit or inferior conjunction (JD)
    PERIASTRON = "periastron"  # time of periastron passage (JD)
    MEAN_ANOMALY = "mean_anomaly"  # mean anomaly at the system epoch (deg)
    MEAN_LONGITUDE = "mean_longitude"  # mean longitude at the system epoch (deg)
    RANDOM = "random"  # unknown: drawn uniformly for every run


class Value(BaseModel):
    """A number with asymmetric uncertainties and its provenance.

    ``err_plus`` and ``err_minus`` are magnitudes (both >= 0). For an ``upper_limit`` value, ``value``
    is the limit itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = None
    err_plus: float | None = Field(default=None, ge=0)
    err_minus: float | None = Field(default=None, ge=0)
    provenance: Provenance = Provenance.MEASURED
    reference: str | None = None
    reference_url: str | None = None

    @property
    def is_known(self) -> bool:
        return self.value is not None and self.provenance is not Provenance.RANDOMIZED

    @property
    def has_errors(self) -> bool:
        return self.err_plus is not None and self.err_minus is not None

    def require(self) -> float:
        """Return the value, or raise if it is missing."""
        if self.value is None:
            raise ValueError("value is missing")
        return self.value


class Phase(BaseModel):
    """Orbital phase information for one planet."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: PhaseKind = PhaseKind.RANDOM
    value: Value | None = None  # JD for transit/periastron, degrees for mean anomaly/longitude

    @model_validator(mode="after")
    def _check(self) -> Phase:
        if self.kind is not PhaseKind.RANDOM and (self.value is None or self.value.value is None):
            raise ValueError(f"phase kind {self.kind.value!r} needs a value")
        return self


class CompletionFlag(BaseModel):
    """Record of one completion rule applied to the input data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    planet: str | None  # None for star- or system-level flags
    parameter: str
    rule: str  # short machine-readable code, e.g. "eccentricity_assumed_zero"
    message: str  # plain-language explanation shown in the report


class Planet(BaseModel):
    """One planet. Orbital elements are in the (assumed coplanar) orbital plane of the system."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    period_days: Value
    mass_earth: Value
    mass_kind: MassKind = MassKind.TRUE
    eccentricity: Value = Value(value=0.0, provenance=Provenance.ASSUMED)
    omega_deg: Value = Value(provenance=Provenance.RANDOMIZED)
    phase: Phase = Phase()
    radius_earth: Value | None = None
    inclination_deg: Value | None = None  # sky-plane inclination; informational only
    semimajor_axis_au: Value | None = None  # published value; informational only
    archive_name: str | None = None  # pl_name of the archive row this planet came from

    @model_validator(mode="after")
    def _check(self) -> Planet:
        p = self.period_days.value
        if p is None or not p > 0:
            raise ValueError(f"{self.name}: orbital period must be positive, got {p}")
        m = self.mass_earth.value
        if m is None or not m > 0:
            raise ValueError(f"{self.name}: mass must be positive, got {m}")
        e = self.eccentricity.value
        if e is None or not 0 <= e < 1:
            raise ValueError(f"{self.name}: eccentricity must be in [0, 1), got {e}")
        return self


class Star(BaseModel):
    """The host star. Companion stars are not modelled (see ``n_stars``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    mass_msun: Value
    n_stars: int = 1
    circumbinary: bool = False

    @model_validator(mode="after")
    def _check(self) -> Star:
        m = self.mass_msun.value
        if m is None or not m > 0:
            raise ValueError(f"{self.name}: stellar mass must be positive, got {m}")
        return self


SourceKind = Literal["archive", "archive-cache", "snapshot", "file"]


class DataSource(BaseModel):
    """Where the parameters of a system were read from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: SourceKind
    table: str | None = None  # e.g. "pscomppars"
    service: str | None = None  # TAP endpoint
    retrieved_utc: str | None = None  # when the archive was queried (ISO 8601)
    path: str | None = None  # file path for user-supplied systems
    note: str | None = None


class System(BaseModel):
    """A star with two or more planets, ordered by orbital period."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    star: Star
    planets: tuple[Planet, ...]
    epoch_jd: float | None = None  # epoch of mean anomalies / longitudes, if given
    source: DataSource
    flags: tuple[CompletionFlag, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> System:
        if len(self.planets) < 2:
            raise ValueError(f"{self.name}: a stability check needs at least two planets")
        periods = [p.period_days.require() for p in self.planets]
        if periods != sorted(periods):
            raise ValueError(f"{self.name}: planets must be ordered by period")
        names = [p.name for p in self.planets]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.name}: planet names must be unique")
        return self

    def planet(self, name_or_letter: str) -> Planet:
        """Look up a planet by full name ("HD 127195 b") or by letter ("b")."""
        key = name_or_letter.strip().lower()
        for p in self.planets:
            if p.name.lower() == key or p.name.lower().endswith(" " + key):
                return p
        raise KeyError(f"no planet {name_or_letter!r} in {self.name}; have {[p.name for p in self.planets]}")
