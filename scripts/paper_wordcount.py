"""Count the words of paper/paper.md as JOSS does roughly (body only: no front matter, comments or references).

python scripts/paper_wordcount.py [--check]   # --check fails outside the 750-1750 word range
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "paper" / "paper.md"
LOW, HIGH = 750, 1750


def count(text: str) -> int:
    body = text.split("---", 2)[2] if text.startswith("---") else text
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = body.split("# References")[0]
    body = re.sub(r"\[@[^\]]*\]", " ", body)  # citations are not counted
    return len(re.findall(r"[A-Za-z0-9][\w'’.\-/]*", body))


def main() -> None:
    n = count(PAPER.read_text(encoding="utf-8"))
    print(f"paper.md: {n} words (JOSS range {LOW}-{HIGH})")
    if "--check" in sys.argv and not LOW <= n <= HIGH:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
