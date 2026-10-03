"""SPOCK worker: runs inside a separate Python environment that has SPOCK installed.

This file is executed as a script by the SPOCK environment's interpreter (``python spock_worker.py``); it does
not import exostab. It reads a JSON request from stdin and writes a JSON answer to stdout:

    request:  {"systems": [{"m_star": .., "planets": [{"m": .., "P": .., "e": .., "pomega": .., "M": ..}, ...]}]}
              (units: Msun, yr, rad; planets ordered by period)
    answer:   {"p_stable": [..], "spock": "2.1.1", "rebound": "4.6.0"}

SPOCK 2.1.1 needs REBOUND < 5, which is why it cannot run inside exostab's own environment (DECISIONS.md, D23).
On macOS the xgboost wheel looks for libomp in Homebrew's location; if it is missing, the worker restarts itself
once with DYLD_LIBRARY_PATH pointing at the copy of libomp bundled with scikit-learn.
"""

import json
import os
import platform
import sys

# This file lives next to exostab's own indicators/spock.py; drop its folder from the import path so that
# "import spock" finds the SPOCK package of this environment.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]


def _ensure_xgboost() -> None:
    try:
        import xgboost  # noqa: F401
    except Exception:
        if platform.system() != "Darwin" or os.environ.get("EXOSTAB_SPOCK_RETRY"):
            raise
        import sklearn

        dylibs = os.path.join(os.path.dirname(sklearn.__file__), ".dylibs")
        env = dict(os.environ, EXOSTAB_SPOCK_RETRY="1")
        env["DYLD_LIBRARY_PATH"] = dylibs + (
            ":" + env["DYLD_LIBRARY_PATH"] if env.get("DYLD_LIBRARY_PATH") else ""
        )
        os.execve(sys.executable, [sys.executable, *sys.argv], env)


def main() -> None:
    _ensure_xgboost()
    import warnings

    import rebound
    import spock

    request = json.load(sys.stdin)
    sims = []
    for system in request["systems"]:
        sim = rebound.Simulation()
        sim.units = ("yr", "AU", "Msun")
        sim.add(m=system["m_star"])
        for p in system["planets"]:
            sim.add(m=p["m"], P=p["P"], e=p["e"], inc=0.0, Omega=0.0, omega=p["pomega"], M=p["M"])
        sim.move_to_com()
        sims.append(sim)
    classifier = spock.FeatureClassifier()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        probs = classifier.predict_stable(sims, n_jobs=int(request.get("n_jobs", 1)), singleWrap=True)
    answer = {
        "p_stable": [float(p) for p in probs],
        "spock": getattr(spock, "__version__", "unknown"),
        "rebound": rebound.__version__,
    }
    json.dump(answer, sys.stdout)


if __name__ == "__main__":
    main()
