"""Repository and packaging checks: ignored files, release metadata, sdist contents and workflows."""

from __future__ import annotations

import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from packaging.version import Version

from exostab import __version__

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_citation_names_the_package_version() -> None:
    # GitHub's "Cite this repository" and Zenodo read CITATION.cff. A release must cite itself (release.yml
    # checks the same for the tag); a development version may still cite the release before it.
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    cited, version = Version(str(cff["version"])), Version(__version__)
    if version.is_prerelease:  # for example 1.1.0.dev0
        assert cited <= version
    else:
        assert cited == version
    datetime.date.fromisoformat(str(cff["date-released"]))


def pyproject() -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pytest depends on tomli before Python 3.11
        import tomli as tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_sdist_ships_what_the_tests_load() -> None:
    # The sdist contains tests/, so packagers run them from it; these are the project files the tests read.
    include = pyproject()["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    needed = ["src/exostab", "tests", "examples", "scripts", "streamlit_app.py"]
    assert [path for path in needed if path not in include] == []


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


@pytest.mark.skipif(not WORKFLOWS.is_dir(), reason="workflows are not in the sdist")
def test_workflow_pipelines_keep_the_exit_status() -> None:
    # A step without `shell:` runs as `bash -e {0}`, without pipefail, so `cmd | tail` succeeds even when cmd
    # fails. `shell: bash` runs `bash --noprofile --norc -eo pipefail {0}`.
    pipe = re.compile(r"(?<!\|)\|(?!\|)")
    unsafe = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = workflow.get("defaults", {}).get("run", {}).get("shell")
        for job_id, job in workflow["jobs"].items():
            shell = job.get("defaults", {}).get("run", {}).get("shell", default)
            for step in job.get("steps", []):
                if pipe.search(step.get("run", "")) and step.get("shell", shell) != "bash":
                    unsafe.append(f"{path.name}: {job_id}: {step.get('name') or step['run'][:60]}")
    assert unsafe == []
