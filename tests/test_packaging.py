"""Repository and packaging checks: ignored files, release metadata, sdist contents and workflows."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout"
)
def test_coverage_data_files_are_ignored() -> None:
    # [tool.coverage.run] parallel = true leaves .coverage.<host>.pid<N>.<random> files behind.
    names = [".coverage", ".coverage.host.local.pid1544.XoShmcrx.HYzE0XwvftFh"]
    r = subprocess.run(
        ["git", "check-ignore", "--no-index", *names], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert r.stdout.split() == names
