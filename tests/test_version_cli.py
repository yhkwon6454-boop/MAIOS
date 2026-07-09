from __future__ import annotations

import subprocess
import sys
import tomllib
from importlib.metadata import version as package_version
from pathlib import Path

import maios

ROOT = Path(__file__).resolve().parents[1]


def test_version_file_package_constant_and_pyproject_match():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert version == "1.3.0"
    assert maios.__version__ == version
    assert pyproject["project"]["version"] == version
    assert package_version("maios") == version


def test_cli_version_command_outputs_package_version():
    completed = subprocess.run(
        [sys.executable, "-m", "maios.cli", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == maios.__version__
    assert completed.stderr == ""
