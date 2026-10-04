"""Matching user-typed system names to archive host names."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping, Sequence

from .archive import Row

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


class SystemNotFoundError(LookupError):
    """No archive system matches the name."""

    def __init__(self, query: str, suggestions: Sequence[str], *, where: str = "the archive table"):
        self.query = query
        self.suggestions = list(suggestions)
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(f"No multi-planet system named {query!r} in {where}.{hint}")


class AmbiguousNameError(SystemNotFoundError):
    """The name matches more than one system once case and punctuation are ignored."""

    def __init__(self, query: str, matches: Mapping[str, str]):
        self.query = query
        self.suggestions = list(matches)
        what = " and ".join(matches.values())
        LookupError.__init__(
            self,
            f"{query!r} is ambiguous: it matches {what}. Type the name exactly as the archive writes it.",
        )


def normalize(name: str) -> str:
    """Case-, space- and punctuation-insensitive key: "TRAPPIST-1" and "trappist 1" both give "trappist1"."""
    return _NON_ALNUM.sub("", name.lower())


def resolve_host(query: str, hosts: Mapping[str, Sequence[Row]]) -> str:
    """Host name for ``query``, which may be a host name ("Kepler-11") or a planet name ("Kepler-11 b").

    An exact host or planet name wins. Otherwise case, spaces and punctuation are ignored; a planet name can
    then coincide with another host's name ("55 cnc b": the planet 55 Cnc b of 55 Cnc, or the companion star
    55 Cnc B), and such a query raises :class:`AmbiguousNameError` instead of picking one.
    """
    exact = query.strip()
    if exact in hosts:
        return exact
    with_planet = [h for h, rows in hosts.items() if any(str(r["pl_name"]) == exact for r in rows)]
    if len(with_planet) == 1:
        return with_planet[0]
    key = normalize(query)
    matches: dict[str, str] = {}  # host -> what matched, for the error message
    for host, rows in hosts.items():
        if normalize(host) == key:
            matches[host] = f"the host {host!r}"
            continue
        planet = next((str(r["pl_name"]) for r in rows if normalize(str(r["pl_name"])) == key), None)
        if planet is not None:
            matches[host] = f"the planet {planet!r} of {host!r}"
    if len(matches) == 1:
        return next(iter(matches))
    if matches:
        raise AmbiguousNameError(query, matches)
    by_key = {normalize(h): h for h in hosts}
    close = difflib.get_close_matches(key, list(by_key), n=5, cutoff=0.75)
    raise SystemNotFoundError(query, [by_key[c] for c in close])


def all_names(hosts: Iterable[str]) -> list[str]:
    return sorted(hosts, key=str.lower)
