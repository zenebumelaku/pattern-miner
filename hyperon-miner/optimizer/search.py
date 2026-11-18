"""Candidate search and result selection.

Main responsibility: generate deterministic, random, or Optuna candidates and
select the fastest eligible measured result.
"""

from __future__ import annotations

import random
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .miner import deterministic_candidates, run_miner
from .models import Config, DatasetProfile, RunResult


# Select the fastest result that meets the requested constraints.
def select_best(results: list[RunResult], max_seconds: float | None, min_patterns: int) -> RunResult | None:
    eligible = [r for r in results if r.status == "ok" and r.pattern_count >= min_patterns
                and (max_seconds is None or r.elapsed_seconds <= max_seconds)]
    return min(eligible, key=lambda r: (r.elapsed_seconds, -max(r.surprisingness_values or [0]))) if eligible else None


# Generate seeded random configurations.
def random_candidates(profile: DatasetProfile, limit: int, seed: int) -> list[Config]:
    rng = random.Random(seed)
    upper = max(1, profile.atom_lines)
    candidates: list[Config] = []
    seen: set[tuple[int, int]] = set()
    while len(candidates) < limit:
        support = rng.randint(1, upper)
        depth = rng.randint(0, 1)
        key = (support, depth)
        if key not in seen:
            seen.add(key)
            candidates.append(Config(support, depth, conj_exp=(depth > 0)))
    return candidates


# Use Optuna when installed, otherwise use the deterministic fallback.
def optuna_candidates(profile: DatasetProfile, limit: int, seed: int,
                      repo: Path, petta: str, dataset: Path, timeout: int,
                      petta_venv: Path | None) -> tuple[list[Config], dict[str, Any]]:
    try:
        import optuna
    except ImportError:
        return deterministic_candidates(profile, limit), {
            "provider": "fallback-after-optuna-unavailable",
            "fallback_count": 1,
        }

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)

    def objective(trial: Any) -> float:
        upper = max(1, profile.atom_lines)
        support = trial.suggest_int("min_support", 1, upper)
        depth = trial.suggest_int("depth", 0, 1)
        config = Config(support, depth, conj_exp=(depth > 0))
        result = run_miner(repo, petta, dataset, config, timeout, petta_venv)
        trial.set_user_attr("config", asdict(config))
        trial.set_user_attr("status", result.status)
        if result.status == "ok" and result.pattern_count > 0:
            return result.elapsed_seconds
        return float(timeout * 100)

    study.optimize(objective, n_trials=limit)
    configs = [
        Config(**trial.user_attrs["config"])
        for trial in study.trials
        if "config" in trial.user_attrs
    ]
    return configs[:limit], {
        "provider": "optuna",
        "seed": seed,
        "fallback_count": 0,
    }


# Compare candidate patterns with the reference result.
def recall_fraction(reference: list[str], candidate: list[str]) -> float:
    if not reference:
        return 1.0 if not candidate else 0.0
    return len(set(reference).intersection(candidate)) / len(set(reference))
