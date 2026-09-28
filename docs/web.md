# Web app

The web app runs the same analysis as `exostab check` in a browser: search a system, edit its parameters, try
"what if" changes, and download the report and figures.

## Using it

1. **Pick a system** in the sidebar. The search box filters as you type. Data come from the NASA Exoplanet
   Archive (downloaded once a day), or from the offline snapshot of 22 systems.
2. **Edit parameters** in the table if you want: period, mass, eccentricity, argument of periastron. Leave ω
   empty to draw it at random. The published uncertainties are kept for the Monte Carlo draws, and every change
   is listed in the report.
3. **What if?** Use the sliders to scale one planet's mass, set its eccentricity, or move it to a different period
   ratio with the planet inside it.
4. **Choose a time budget** (5–120 s) and press **Run**. The app measures how fast this system integrates and
   picks the run length and number of draws that fit (see [`--budget`](cli.md)).
5. **Read the result.** It shows the overall verdict, the three indicators with their explanations, the
   data-completion rules that were applied, and interactive figures (orbits, MEGNO over time, all draws).
6. **Download** `report.json`, `orbits.png` and `megno.png`, or copy the **shareable link**. The link encodes the
   system, your edits, the seed and the exact run length, so whoever opens it gets the same run.

Results are cached by a SHA-256 hash of every input, so opening the same link again on the same server is
instant. On the hosted version the integrations run in a single process, so a given budget covers fewer orbits
and draws than the command line on a multi-core computer.

## Running it locally

```bash
pip install "exostab[web]"
```

```bash
streamlit run streamlit_app.py
```

Run the second command from a clone of the repository, which contains `streamlit_app.py`. Then open
http://localhost:8501.

## Hosting

The repository is ready for [Streamlit Community Cloud](https://streamlit.io/cloud), which hosts public apps
from public GitHub repositories for free. Its documented resources are 0.078–2 CPU cores and 690 MB–2.7 GB of
memory, and apps without traffic for 12 hours go to sleep until someone wakes them. Deployment uses:

- entry point `streamlit_app.py`;
- dependencies from the root `requirements.txt` (`streamlit==1.64.0` and `.[web]`);
- Python 3.12, chosen under "Advanced settings";
- settings from `.streamlit/config.toml`.

Hugging Face Spaces was the planned fallback, but since July 2026 Streamlit/Docker Spaces need a paid plan
(checked 2026-09-28).
