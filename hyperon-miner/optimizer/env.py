"""Project environment loading for the optimizer.

Main responsibility: load local ``.env`` settings without overriding values
already supplied by the shell.
"""

from __future__ import annotations

import os
from pathlib import Path


# Locate the project and its optional local environment file.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"


# Parse simple environment assignments without overriding shell settings.
def load_project_env(path: Path = PROJECT_ENV_FILE) -> None:
    """Load simple KEY=VALUE settings without overriding the shell environment."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[name] = value


# Load project settings when the optimizer package is imported.
load_project_env()
