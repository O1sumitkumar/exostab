"""Scripts used by the workflows: catalog page, release notes, Zenodo upload, snapshot builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def small_catalog(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from exostab.catalog.build import CatalogSettings, build_catalog

    out = tmp_path_factory.mktemp("catalog")
    build_catalog(CatalogSettings(orbits=100, draws=1, jobs=2), out, limit=4, offline=True)
    return out


def test_catalog_page(small_catalog: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    page = load("catalog_page")
    monkeypatch.setattr(page, "OUT", tmp_path / "catalog.md")
    text = page.render(small_catalog)
    assert 'id="catalog-table"' in text and text.count("<tr>") == 1 + 4
    assert "data/catalog.csv" in text and "Overall verdicts" in text
    assert "verdict-" in text
    placeholder = page.render(None)
    assert "No catalog has been published yet" in placeholder and "data/catalog.csv" not in placeholder
    monkeypatch.setattr("sys.argv", ["catalog_page.py", str(small_catalog)])
    page.main()
    assert (tmp_path / "catalog.md").read_text().startswith("# Stability catalog")


def test_cell_formatting() -> None:
    page = load("catalog_page")
    row = {
        "status": "ok",
        "nbody_regular": "3",
        "nbody_chaotic": "1",
        "nbody_unstable": "0",
        "overall": "stable",
        "amd_beta_max": "inf",
        "hill_min_separation": "",
        "megno_nominal": "2.0",
        "t_end_yr": "1234.5",
    }
    assert page._cell("draws_summary", row) == ("3/1/0", "3")
    assert page._cell("amd_beta_max", row) == ("∞", "1e308")
    assert page._cell("hill_min_separation", row)[0] == "—"
    assert page._cell("t_end_yr", row)[0] == "1,234"
    assert page._cell("overall", {**row, "status": "timeout", "overall": ""})[0] == "timeout"


def test_release_notes(small_catalog: Path) -> None:
    notes = load("catalog_release_notes").notes(small_catalog)
    assert "4 multi-planet systems" in notes and "NASA Exoplanet Archive" in notes


class FakeResponse:
    def __init__(self, status: int, body: Any = None):
        self.status_code = status
        self._body = body or {}
        self.text = json.dumps(self._body)

    def json(self) -> Any:
        return self._body


class FakeSession:
    """Answers like Zenodo's legacy deposit API and records every call."""

    def __init__(self, fail_first: int = 0):
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, str]] = []
        self.fail_first = fail_first

    def request(self, method: str, url: str, **kw: Any) -> FakeResponse:
        self.calls.append((method, url))
        if self.fail_first:
            self.fail_first -= 1
            return FakeResponse(503)
        z = "https://sandbox.zenodo.org"
        if method == "GET" and url == f"{z}/api/records/100":
            return FakeResponse(200, {"id": 105})
        if method == "POST" and url.endswith("/api/deposit/depositions/105/actions/newversion"):
            return FakeResponse(201, {"links": {"latest_draft": f"{z}/api/deposit/depositions/106"}})
        if method == "GET" and url.endswith("/depositions/106"):
            return FakeResponse(
                200,
                {
                    "id": 106,
                    "files": [{"id": "f1"}],
                    "metadata": {"title": "t", "version": "old"},
                    "links": {"bucket": f"{z}/api/files/b1"},
                },
            )
        if method == "DELETE":
            return FakeResponse(204)
        if method == "PUT" and "/api/files/b1/" in url:
            return FakeResponse(201)
        if method == "PUT" and url.endswith("/depositions/106"):
            assert json.loads(kw["data"])["metadata"]["version"] == "2026-09-28"
            return FakeResponse(200)
        if method == "POST" and url.endswith("/depositions/106/actions/publish"):
            return FakeResponse(202, {"doi_url": "https://doi.org/10.5072/zenodo.106"})
        return FakeResponse(404)


def test_zenodo_new_version_sequence(tmp_path: Path) -> None:
    z = load("zenodo_catalog")
    for f in ("catalog.csv", "catalog.parquet"):
        (tmp_path / f).write_text("x")
    (tmp_path / "catalog_meta.json").write_text(json.dumps({"created_utc": "2026-09-28T04:00:00+00:00"}))
    session = FakeSession(fail_first=1)
    client = z.Zenodo("https://sandbox.zenodo.org/", "TOKEN", session=session, pause=0)  # type: ignore[arg-type]
    published = z.publish_catalog(client, "100", tmp_path)
    assert published["doi_url"].endswith("106")
    assert session.headers["Authorization"] == "Bearer TOKEN"
    methods = [m for m, _ in session.calls]
    assert methods == ["GET", "GET", "POST", "GET", "DELETE", "PUT", "PUT", "PUT", "PUT", "POST"]


def test_zenodo_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    z = load("zenodo_catalog")
    client = z.Zenodo("https://sandbox.zenodo.org", "T", session=FakeSession(), pause=0)  # type: ignore[arg-type]
    with pytest.raises(z.ZenodoError, match="HTTP 404"):
        client.latest_record_id("999")
    (tmp_path / "catalog_meta.json").write_text(json.dumps({"created_utc": "2026-09-28"}))
    with pytest.raises(z.ZenodoError, match="missing catalog files"):
        z.publish_catalog(client, "100", tmp_path)
    monkeypatch.delenv("ZENODO_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        z.main()


def test_make_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from exostab.data import load_rows

    snap = load("make_snapshot")
    rows, _ = load_rows(offline=True)
    monkeypatch.setattr(snap, "fetch_rows", lambda where: rows)
    monkeypatch.setattr(snap, "OUT", tmp_path)
    snap.main()
    meta = json.loads((tmp_path / "snapshot.json").read_text())
    assert meta["n_systems"] == len(snap.SYSTEMS) and meta["n_rows"] == len(rows)
    monkeypatch.setattr(snap, "SYSTEMS", ["Not-A-System"])
    with pytest.raises(SystemExit, match="not in the archive"):
        snap.main()
