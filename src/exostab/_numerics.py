"""Small numerical helpers (kept here to avoid a SciPy dependency)."""

from __future__ import annotations

from collections.abc import Callable


def bisect(
    f: Callable[[float], float], lo: float, hi: float, *, xtol: float = 1e-14, maxiter: int = 200
) -> float:
    """Root of ``f`` in ``[lo, hi]`` by bisection. ``f(lo)`` and ``f(hi)`` must differ in sign."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if (flo > 0) == (fhi > 0):
        raise ValueError(f"root not bracketed: f({lo})={flo}, f({hi})={fhi}")
    for _ in range(maxiter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if fmid == 0 or hi - lo < xtol * max(1.0, abs(mid)):
            return mid
        if (fmid > 0) == (flo > 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return 0.5 * (lo + hi)
