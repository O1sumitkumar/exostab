"""``python -m exostab.web``: start the web app from an installed package (``pip install "exostab[web]"``).

It runs ``streamlit run`` on the packaged copy of ``streamlit_app.py``; extra arguments are passed on, e.g.
``python -m exostab.web --server.port 8502``.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("streamlit_app.py")


def main(args: list[str] | None = None) -> int:
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        print('The web app needs its optional dependencies: pip install "exostab[web]"', file=sys.stderr)
        return 1
    sys.argv = ["streamlit", "run", str(SCRIPT), *(sys.argv[1:] if args is None else args)]
    stcli.main()  # a click command: it exits with Streamlit's exit code
    return 0


if __name__ == "__main__":
    sys.exit(main())
