"""Entry point that ``python -m exostab.web`` passes to ``streamlit run`` (the packaged copy of the repository's
``streamlit_app.py``). Streamlit runs it as a script, so it uses an absolute import."""

from exostab.web.app import main

main()
