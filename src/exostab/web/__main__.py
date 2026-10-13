"""``python -m exostab.web``: start the web app from an installed package with the ``[web]`` extra.

It runs ``streamlit run`` on the packaged copy of ``streamlit_app.py``; extra arguments are passed on, e.g.
``python -m exostab.web --server.port 8502``.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("streamlit_app.py")
# exostab is installed from GitHub, not PyPI, so the hint points to the install commands instead of naming one
MISSING = (
    "The web app needs the optional [web] extra (Streamlit and Plotly). Install it in the same way as exostab, "
    'with "exostab[web]" in place of "exostab": https://mimitoz62.github.io/exostab/quickstart/'
)


def main(args: list[str] | None = None) -> int:
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        print(MISSING, file=sys.stderr)
        return 1
    sys.argv = ["streamlit", "run", str(SCRIPT), *(sys.argv[1:] if args is None else args)]
    stcli.main()  # a click command: it exits with Streamlit's exit code
    return 0


if __name__ == "__main__":
    sys.exit(main())
