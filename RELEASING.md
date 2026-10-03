# Releasing exostab

This file is for maintainers. It lists the one-time account setup for each place exostab is published, and the
steps to cut a release. Every service below is optional except GitHub itself: a release that only reaches
GitHub (and Zenodo) is complete.

## Already set up

- **Documentation** on GitHub Pages: Settings → Pages → Source "GitHub Actions", and the repository variable
  `DEPLOY_DOCS` = `true`. `.github/workflows/docs.yml` deploys https://mimitoz62.github.io/exostab/ on every push
  to `main` and after every weekly catalog.
- **Private vulnerability reporting**, which `SECURITY.md` and the issue template point to.

## PyPI (optional)

`.github/workflows/release.yml` uploads to PyPI with trusted publishing (no API token is stored), but only when
the repository variable `PUBLISH_PYPI` is `true`. Set it up before the tag whose version should be the first on
PyPI; a version already released on GitHub is not uploaded afterwards.

1. Create an account at https://pypi.org/account/register/ and turn on two-factor authentication (PyPI
   requires it for uploads).
2. Open https://pypi.org/manage/account/publishing/ and add a pending publisher for GitHub with exactly:
   - PyPI project name: `exostab`
   - Owner: `mimitoz62`
   - Repository name: `exostab`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

   A pending publisher does not reserve the name; the project is created by the first upload.
3. On GitHub: Settings → Secrets and variables → Actions → Variables → New repository variable `PUBLISH_PYPI`
   with the value `true`.
4. Optional: Settings → Environments → New environment `pypi` → Required reviewers → yourself. Each upload then
   waits for your approval. (Without this step GitHub creates the environment, with no rules, at the first
   upload.)

To pause PyPI uploads, delete the variable or set it to anything other than `true`.

## Zenodo (software DOI)

Zenodo archives every published GitHub release, pre-releases included, and gives it a DOI. Its metadata (title,
authors with ORCID, license, keywords) come from `CITATION.cff`.

1. Log in at https://zenodo.org with "Log in with GitHub" and authorize Zenodo.
2. Open https://zenodo.org/account/settings/github/, press "Sync now" if the repository is not listed, and switch
   on `mimitoz62/exostab`. Do this before the first release: earlier releases are not archived.
3. Publish a release (below). The record appears on the same page a few minutes later.
4. After the first release, add the concept DOI (the one that always resolves to the latest version) to
   `README.md` ("Citing exostab") and as `doi:` in `CITATION.cff`.

Do not publish GitHub pre-releases for testing: Zenodo would archive them as versions of exostab.

## Streamlit Community Cloud (web app)

1. Log in at https://share.streamlit.io with "Continue with GitHub" and authorize Streamlit.
2. Create app → "Deploy a public app from GitHub", with:
   - Repository: `mimitoz62/exostab`, branch `main`
   - Main file path: `streamlit_app.py`
   - App URL: `exostab` (https://exostab.streamlit.app, if the name is still free)
   - Advanced settings → Python version: 3.12. No secrets are needed.
3. Deploy. Dependencies come from `requirements.txt` (`streamlit==1.64.0` and `.[web]`), settings from
   `.streamlit/config.toml`. The app redeploys on every push to `main`.
4. Add the app's URL to `README.md` and `docs/web.md`.

## Weekly catalog

`.github/workflows/catalog.yml` runs every Monday at 04:23 UTC with no setup: it recomputes the catalog, commits
`catalog.csv`, `catalog.parquet` and `catalog_meta.json` to the branch `catalog-data`, and starts the docs
workflow so the catalog page is updated. The full log is in the run's `catalog` artifact (`build.log`).

- To run it now: Actions → Weekly catalog → Run workflow, with limit `0` (all systems). A smaller limit
  publishes a partial catalog until the next full run.
- Optional DOI for the catalog (a Zenodo dataset, separate from the software DOI):
  1. After the first full catalog exists, create a new upload on Zenodo with its three files (from the branch
     `catalog-data`), resource type "Dataset", and publish it. Note its record id (the number in
     `https://zenodo.org/records/<id>`).
  2. Zenodo → Applications → Personal access tokens → New token with the scopes `deposit:write` and
     `deposit:actions`.
  3. On GitHub: repository secret `ZENODO_TOKEN` = the token; repository variable `ZENODO_CATALOG_RECORD` = the
     record id. From then on every weekly run publishes a new version of that record
     (`scripts/zenodo_catalog.py`).
  4. Try it on https://sandbox.zenodo.org first (separate account, token and record): also set the variable
     `ZENODO_URL` = `https://sandbox.zenodo.org`, run the workflow, then delete `ZENODO_URL` and switch the
     token and record id to the real ones.

## Cutting a release

1. Check that CI and the nightly validation suite pass on `main` (Actions tab). The release workflow runs only
   the fast suite.
2. Choose the version `X.Y.Z` ([semantic versioning](https://semver.org/)) and set it in three places:
   - `src/exostab/__init__.py`: `__version__ = "X.Y.Z"`;
   - `CITATION.cff`: `version: "X.Y.Z"` and `date-released: "YYYY-MM-DD"` (the release date);
   - `CHANGELOG.md`: move the entries under "Unreleased" to a new section `## [X.Y.Z] - YYYY-MM-DD`, and copy
     the file to `docs/changelog.md`.
3. Commit, push to `main` and wait for CI to pass.
4. Tag and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "exostab X.Y.Z"
   git push origin vX.Y.Z
   ```

5. The Release workflow then:
   - checks that the tag, `__version__` and `CITATION.cff` give the same version, that `CITATION.cff` has a
     `date-released`, and that `CHANGELOG.md` has a section for the version;
   - builds the wheel and sdist and tests the wheel (ruff, mypy, fast suite, CLI) on Ubuntu and macOS with
     Python 3.10 and 3.14;
   - uploads to PyPI if `PUBLISH_PYPI` is `true`;
   - creates the GitHub release with the CHANGELOG section as notes; Zenodo archives it.
6. If the workflow fails before anything is published, fix the problem on `main`, delete the tag
   (`git push --delete origin vX.Y.Z` and `git tag -d vX.Y.Z`) and tag again. Once a version is on PyPI its
   number cannot be used again: release `X.Y.Z+1` instead.
