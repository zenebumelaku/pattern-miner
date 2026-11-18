#!/usr/bin/env python3
"""Compatibility entry point for the PeTTa Pattern Miner optimizer.

Main responsibility: keep the original script path, public imports, and CLI
behavior working while the implementation lives in focused modules.
"""

from __future__ import annotations

import sys
import urllib
from pathlib import Path


# Main compatibility bootstrap for direct execution as optimizer/prototype.py.
if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


# Re-export the original public API while implementations stay modular.
from optimizer.cli import experiment_main, main
from optimizer.env import PROJECT_ENV_FILE, PROJECT_ROOT, load_project_env
from optimizer.llm import (
    SUPPORTED_LLM_PROVIDERS,
    configured_llm_provider,
    llm_api_key,
    llm_candidates,
)
from optimizer.miner import (
    MINIMAL_FREQUENT_IMPORTS,
    RESULT_BEGIN,
    RESULT_END,
    _metta_value,
    _text,
    analyze_dataset,
    deterministic_candidates,
    make_script,
    parse_pattern_set,
    parse_results,
    run_miner,
    validate_config,
)
from optimizer.models import Config, DatasetProfile, RunResult
from optimizer.search import optuna_candidates, random_candidates, recall_fraction, select_best


# Preserve the original script entry point.
if __name__ == "__main__":
    raise SystemExit(main())
