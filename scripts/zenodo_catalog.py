"""Publish a new version of the catalog dataset on Zenodo (used by the weekly catalog workflow).

    ZENODO_TOKEN=... ZENODO_CATALOG_RECORD=<record id> [ZENODO_URL=https://sandbox.zenodo.org] \
        python scripts/zenodo_catalog.py catalog/

One-time setup (by the maintainer, in the Zenodo web interface): upload a first catalog as a new "Dataset"
record, publish it, and note its record id; create a personal access token with the scopes deposit:write and
deposit:actions. Then store the token as the repository secret ZENODO_TOKEN and the record id as the repository
variable ZENODO_CATALOG_RECORD. Test first against https://sandbox.zenodo.org (separate account and token; its
DOIs start with 10.5072 and never resolve publicly) by setting the variable ZENODO_URL.

Steps (Zenodo's documented "legacy" deposit API, https://developers.zenodo.org/):
1. GET /api/records/{id} follows the redirect from a concept or older record to the latest version.
2. POST /api/deposit/depositions/{latest}/actions/newversion; the new draft is at links.latest_draft.
3. Delete the draft's files and PUT the new files into its bucket (links.bucket).
4. PUT the metadata with a new version (the catalog date) and publication date.
5. POST .../actions/publish.
Every request is retried on HTTP 429 and 5xx with back-off. All versions share one concept DOI.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

FILES = ("catalog.csv", "catalog.parquet", "catalog_meta.json")


class ZenodoError(RuntimeError):
    pass


class Zenodo:
    def __init__(
        self, base_url: str, token: str, session: requests.Session | None = None, pause: float = 2.0
    ):
        self.base = base_url.rstrip("/")
        self.s = session or requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        self.pause = pause

    def request(self, method: str, url: str, expect: tuple[int, ...], **kw: Any) -> requests.Response:
        if url.startswith("/"):
            url = self.base + url
        for attempt in range(5):
            r = self.s.request(method, url, timeout=120, **kw)
            if r.status_code in expect:
                return r
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(self.pause * 2**attempt)
                continue
            break
        raise ZenodoError(f"{method} {url} -> HTTP {r.status_code}: {r.text[:500]}")

    def latest_record_id(self, record_id: str) -> str:
        r = self.request("GET", f"/api/records/{record_id}", (200,), allow_redirects=True)
        return str(r.json()["id"])

    def new_version(self, record_id: str) -> dict[str, Any]:
        r = self.request("POST", f"/api/deposit/depositions/{record_id}/actions/newversion", (201,))
        draft_url = r.json()["links"]["latest_draft"]
        return dict(self.request("GET", draft_url, (200,)).json())

    def replace_files(self, draft: dict[str, Any], folder: Path) -> None:
        for f in draft.get("files", []):
            self.request("DELETE", f"/api/deposit/depositions/{draft['id']}/files/{f['id']}", (204,))
        bucket = draft["links"]["bucket"]
        for name in FILES:
            with (folder / name).open("rb") as fh:
                self.request("PUT", f"{bucket}/{name}", (200, 201), data=fh)

    def set_version(self, draft: dict[str, Any], version: str, date: str) -> None:
        metadata = dict(draft["metadata"])
        metadata.update(version=version, publication_date=date)
        self.request(
            "PUT",
            f"/api/deposit/depositions/{draft['id']}",
            (200,),
            data=json.dumps({"metadata": metadata}),
            headers={"Content-Type": "application/json"},
        )

    def publish(self, draft: dict[str, Any]) -> dict[str, Any]:
        r = self.request("POST", f"/api/deposit/depositions/{draft['id']}/actions/publish", (202,))
        return dict(r.json())


def publish_catalog(zenodo: Zenodo, record_id: str, folder: Path) -> dict[str, Any]:
    meta = json.loads((folder / "catalog_meta.json").read_text(encoding="utf-8"))
    day = meta["created_utc"][:10]
    missing = [f for f in FILES if not (folder / f).exists()]
    if missing:
        raise ZenodoError(f"missing catalog files: {missing}")
    latest = zenodo.latest_record_id(record_id)
    draft = zenodo.new_version(latest)
    zenodo.replace_files(draft, folder)
    zenodo.set_version(draft, version=day, date=day)
    return zenodo.publish(draft)


def main() -> None:
    token = os.environ.get("ZENODO_TOKEN")
    record = os.environ.get("ZENODO_CATALOG_RECORD")
    if not token or not record:
        raise SystemExit("set ZENODO_TOKEN and ZENODO_CATALOG_RECORD")
    base = os.environ.get("ZENODO_URL", "https://zenodo.org")
    published = publish_catalog(
        Zenodo(base, token), record, Path(sys.argv[1] if len(sys.argv) > 1 else "catalog")
    )
    print(f"published {published.get('doi_url') or published.get('links', {}).get('html')}")


if __name__ == "__main__":
    main()
