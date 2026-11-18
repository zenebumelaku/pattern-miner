"""Small optimizer around the PeTTa Pattern Miner.

The miner remains the source of symbolic results. This module only analyzes the
dataset, proposes configurations, launches PeTTa, parses its textual output,
and selects among measured runs.

Main responsibility: parse command-line options, run experiments, and write
optimizer reports.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .llm import configured_llm_provider, llm_api_key, llm_candidates
from .miner import analyze_dataset, deterministic_candidates, run_miner, validate_config
from .models import Config
from .search import optuna_candidates, random_candidates, recall_fraction, select_best


# Experiment-mode command: compare candidate-generation strategies.
def experiment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="prototype.py experiment",
        description="Run small baseline and candidate-selection experiments.",
    )
    parser.add_argument("--repo", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--petta", default=os.environ.get("PETTA", "petta"))
    parser.add_argument("--petta-venv", type=Path)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    parser.add_argument("--methods", nargs="+",
                        choices=["default", "random", "optuna", "deterministic", "llm-warmstart"],
                        default=["default", "random", "optuna", "deterministic", "llm-warmstart"])
    parser.add_argument("--recall-threshold", type=float, default=1.0)
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument(
        "--require-gemini",
        action="store_true",
        help="fail instead of falling back unless every LLM warm-start call is live Gemini",
    )
    parser.add_argument("--llm-mode", choices=["warmstart"], default="warmstart")
    parser.add_argument("--output", type=Path, default=Path("experiment-report.json"))
    args = parser.parse_args(argv)

    # Validate options that only apply to live Gemini experiments.
    if args.require_gemini and configured_llm_provider() != "gemini":
        parser.error("--require-gemini requires LLM_PROVIDER=gemini")
    if args.require_gemini and "llm-warmstart" not in args.methods:
        parser.error("--require-gemini requires the llm-warmstart method")

    # Establish the reference run used for recall comparisons.
    repo, dataset = args.repo.resolve(), args.dataset.resolve()
    profile = analyze_dataset(dataset)
    reference = run_miner(
        repo, args.petta, dataset, Config(1, 0, conj_exp=False),
        args.timeout, args.petta_venv,
    )
    reference_patterns = set(reference.patterns or [])

    # Evaluate every requested method and seed.
    method_reports: dict[str, Any] = {}
    fallback_count = 0
    for method in args.methods:
        seed_reports: list[dict[str, Any]] = []
        for seed in args.seeds:
            llm_metadata: dict[str, Any] = {"provider": "none"}
            if method == "default":
                configs = [Config(3, 0, conj_exp=True)]
            elif method == "random":
                configs = random_candidates(profile, args.trials, seed)
            elif method == "optuna":
                configs, llm_metadata = optuna_candidates(
                    profile, args.trials, seed, repo, args.petta, dataset,
                    args.timeout, args.petta_venv,
                )
            elif method == "deterministic":
                configs = deterministic_candidates(profile, args.trials)
                llm_metadata = {"provider": "deterministic-fallback", "fallback_count": 1}
            else:
                llm_key, requested_provider = llm_api_key()
                if args.mock_llm or not llm_key:
                    if args.require_gemini:
                        raise RuntimeError(
                            "Gemini is required, but GEMINI_API_KEY is missing or mock mode is enabled"
                        )
                    configs = deterministic_candidates(profile, args.trials)
                    llm_metadata = {
                        "provider": "MOCK - deterministic no-key fallback",
                        "requested_provider": requested_provider,
                        "fallback_count": 1,
                        "real_llm": False,
                    }
                else:
                    configs, llm_metadata = llm_candidates(profile, [], args.trials)
                    llm_metadata.setdefault(
                        "real_llm",
                        llm_metadata.get("provider") in {"gemini", "openai-compatible"},
                    )
                    if args.require_gemini and not (
                        llm_metadata.get("provider") == "gemini"
                        and llm_metadata.get("real_llm") is True
                    ):
                        raise RuntimeError(
                            "Gemini request did not complete as a live Gemini call: "
                            + json.dumps(llm_metadata, sort_keys=True)
                        )

            results = [
                run_miner(repo, args.petta, dataset, config, args.timeout, args.petta_venv)
                for config in configs
            ]
            eligible = []
            for result in results:
                if result.status != "ok":
                    continue
                recall = recall_fraction(
                    sorted(reference_patterns),
                    result.patterns or [],
                )
                if recall >= args.recall_threshold:
                    eligible.append((result, recall))
            best = min(eligible, key=lambda item: item[0].elapsed_seconds) if eligible else None
            fallback_count += llm_metadata.get("fallback_count", 0)
            seed_reports.append({
                "seed": seed,
                "llm": llm_metadata,
                "results": [asdict(result) for result in results],
                "best": asdict(best[0]) if best else None,
                "best_recall": best[1] if best else None,
                "fallback_count": llm_metadata.get("fallback_count", 0),
            })
        method_reports[method] = {
            "seeds": seed_reports,
            "valid_config_rate": sum(
                1 for seed_report in seed_reports
                for result in seed_report["results"]
                if validate_config(Config(**result["config"]), profile) == []
            ) / max(1, sum(len(seed_report["results"]) for seed_report in seed_reports)),
        }

    # Persist the experiment report and concise console summary.
    report = {
        "dataset": asdict(profile),
        "trials": args.trials,
        "timeout": args.timeout,
        "seeds": args.seeds,
        "recall_threshold": args.recall_threshold,
        "reference": asdict(reference),
        "methods": method_reports,
        "fallback_count": fallback_count,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "reference_status": reference.status,
        "methods": list(method_reports),
    }, indent=2))
    return 0


# Normal command: run configured candidates and select the best result.
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "experiment":
        return experiment_main(sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--petta", default=os.environ.get("PETTA", "petta"))
    parser.add_argument("--petta-venv", type=Path,
                        help="Python 3.11 venv used by SWI-Prolog Janus")
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--min-patterns", type=int, default=1)
    parser.add_argument("--config-file", type=Path,
                        help="JSON list of manual configurations; skips LLM proposals")
    parser.add_argument(
        "--require-gemini",
        action="store_true",
        help="fail unless the live proposal comes from Gemini",
    )
    parser.add_argument("--output", type=Path, default=Path("optimizer-report.json"))
    args = parser.parse_args()

    # Resolve the source dataset and configuration proposals.
    if args.require_gemini and args.config_file:
        parser.error("--require-gemini cannot be used with --config-file")
    repo, dataset = args.repo.resolve(), args.dataset.resolve()
    profile = analyze_dataset(dataset)
    if args.config_file:
        raw_configs = json.loads(args.config_file.read_text(encoding="utf-8"))
        configs = [Config(**item) for item in raw_configs[:args.trials]]
        llm = {"provider": "manual-config-file", "path": str(args.config_file.resolve())}
    else:
        configs, llm = llm_candidates(profile, [], args.trials)
        if args.require_gemini and not (
            llm.get("provider") == "gemini" and llm.get("real_llm") is True
        ):
            raise RuntimeError(
                "Gemini is required, but the proposal was not a live Gemini response: "
                + json.dumps(llm, sort_keys=True)
            )
    # Execute each candidate through the symbolic miner.
    results = [run_miner(repo, args.petta, dataset, config, args.timeout, args.petta_venv)
               for config in configs]
    best = select_best(results, args.max_seconds, args.min_patterns)
    # Write the selected result and all measurements.
    report = {"dataset": asdict(profile), "llm": llm, "results": [asdict(r) for r in results],
              "best": asdict(best) if best else None,
              "selection": {"max_seconds": args.max_seconds, "min_patterns": args.min_patterns}}
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "best": best.config if best else None,
                      "statuses": [r.status for r in results]}, indent=2))
    return 0 if best else 2
