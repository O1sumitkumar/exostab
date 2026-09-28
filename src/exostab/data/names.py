"""Matching user-typed system names to archive host names."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping, Sequence

from .archive import Row

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


class SystemNotFoundError(LookupError):
    """No archive system matches the name."""

    def __init__(self, query: str, suggestions: Sequence[str]):
        self.query = query
        self.suggestions = list(suggestions)
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(f"No multi-planet system named {query!r} in the archive table.{hint}")


def normalize(name: str) -> str:
    """Case-, space- and punctuation-insensitive key: "TRAPPIST-1" and "trappist 1" both give "trappist1"."""
    return _NON_ALNUM.sub("", name.lower())


def resolve_host(query: str, hosts: Mapping[str, Sequence[Row]]) -> str:
    """Host name for ``query``, which may be a host name ("Kepler-11") or a planet name ("Kepler-11 b")."""
    key = normalize(query)
    by_key = {normalize(h): h for h in hosts}
    if key in by_key:
        return by_key[key]
    for host, rows in hosts.items():
        if any(normalize(str(r["pl_name"])) == key for r in rows):
            return host
    close = difflib.get_close_matches(key, list(by_key), n=5, cutoff=0.75)
    raise SystemNotFoundError(query, [by_key[c] for c in close])


def all_names(hosts: Iterable[str]) -> list[str]:
    return sorted(hosts, key=str.lower)
