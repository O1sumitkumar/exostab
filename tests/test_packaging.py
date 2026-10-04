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
    # GitHub's "Cite this repository" and Zenodo read CITATION.cff. A release must cite itself with its release
    # date (release.yml checks the same for the tag). A development version may still cite the release before
    # it, with that release's date, or cite itself without a date: it has not been released.
    cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    cited, version = Version(str(cff["version"])), Version(__version__)
    if version.is_prerelease and cited == version:  # for example 1.1.0.dev0
        assert "date-released" not in cff
        return
    if version.is_prerelease:
        assert cited < version
    else:
        assert cited == version
    datetime.date.fromisoformat(str(cff["date-released"]))


def test_a_release_version_has_a_changelog_section() -> None:
    # release.yml refuses a tag whose version has no "## [X.Y.Z]" section in CHANGELOG.md. Checked on every
    # commit, so that main never claims a release version (with a release date in CITATION.cff) before its
    # changelog section exists; a development version collects its entries under "Unreleased".
    headings = [
        line
        for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]
    wanted = "[Unreleased]" if Version(__version__).is_prerelease else f"[{__version__}]"
    assert any(wanted in heading for heading in headings)


def pyproject() -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pytest depends on tomli before Python 3.11
        import tomli as tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_sdist_ships_what_the_tests_load() -> None:
    # The sdist contains tests/, so packagers run them from it; these are the project files the tests read.
    include = pyproject()["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    needed = ["src/exostab", "tests", "examples", "scripts", "streamlit_app.py", "docs/cli.md"]
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
def test_documents_named_in_workflows_exist() -> None:
    # The workflows point maintainers to setup instructions (RELEASING.md, DECISIONS.md, ...).
    names = {
        name for path in WORKFLOWS.glob("*.yml") for name in re.findall(r"\b[A-Z]+\.md\b", path.read_text())
    }
    assert names and [name for name in sorted(names) if not (ROOT / name).is_file()] == []


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
