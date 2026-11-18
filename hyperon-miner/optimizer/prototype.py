#!/usr/bin/env python3
"""Small optimizer around the PeTTa Pattern Miner.

The miner remains the source of symbolic results. This module only analyzes the
dataset, proposes configurations, launches PeTTa, parses its textual output,
and selects among measured runs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import resource
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


MINIMAL_FREQUENT_IMPORTS = (
    "experiments/utils/common-utils",
    "experiments/utils/index_to_var",
    "experiments/utils/constants",
    "experiments/utils/TruthValue",
    "experiments/utils/sort",
    "experiments/utils/variable-combinations",
    "experiments/utils/remove_useless_clauses",
    "experiments/utils/surp-utils/blk-abstractness",
    "experiments/frequent-pattern-miner/valuation",
    "experiments/frequent-pattern-miner/shallow-abstractions",
    "experiments/frequent-pattern-miner/specialization",
    "experiments/frequent-pattern-miner/candidate",
    "experiments/frequent-pattern-miner/conjunction-expansion",
    "experiments/frequent-pattern-miner/frequent-pattern-miner-generic",
    "experiments/pattern-miner/pattern-miner",
)
RESULT_BEGIN = "OPTIMIZER_RESULTS_BEGIN"
RESULT_END = "OPTIMIZER_RESULTS_END"


@dataclass(frozen=True)
class Config:
    min_support: int
    depth: int
    mode: str = "none"
    normalization: str = "none"
    db_ratio: str = "none"
    conj_exp: bool = True
    init_pattern: str = "$x"


@dataclass
class DatasetProfile:
    path: str
    atom_lines: int
    link_lines: int
    predicates: dict[str, int]
    distinct_symbols: int
    bytes: int


@dataclass
class RunResult:
    config: dict[str, Any]
    status: str
    elapsed_seconds: float
    peak_memory_mb: float | None
    pattern_count: int
    support_values: list[float]
    surprisingness_values: list[float]
    stdout: str
    stderr: str
    error: str | None = None


def analyze_dataset(path: Path) -> DatasetProfile:
    predicates: dict[str, int] = {}
    symbols: set[str] = set()
    atom_lines = link_lines = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("!"):
            continue
        atom_lines += 1
        match = re.match(r"\(?\s*([A-Za-z_][\w-]*)\b(.*)", line)
        if not match:
            continue
        predicate, remainder = match.groups()
        predicates[predicate] = predicates.get(predicate, 0) + 1
        symbols.add(predicate)
        symbols.update(re.findall(r"\b[A-Za-z_][\w-]*\b", remainder))
        if predicate.lower() in {"link", "inheritance", "evaluation", "member"}:
            link_lines += 1
    return DatasetProfile(
        str(path), atom_lines, link_lines, dict(sorted(predicates.items())),
        len(symbols), path.stat().st_size,
    )


def validate_config(config: Config, profile: DatasetProfile) -> list[str]:
    errors: list[str] = []
    if config.min_support < 1:
        errors.append("min_support must be at least 1")
    if config.depth < 0:
        errors.append("depth cannot be negative")
    if config.mode not in {"none", "isurp", "isurp-old", "jsd"}:
        errors.append("mode must be none, isurp, isurp-old, or jsd")
    if config.mode == "none" and config.normalization != "none":
        errors.append("normalization must be none when mode is none")
    if config.mode == "none" and config.db_ratio != "none":
        errors.append("db_ratio must be none when mode is none")
    if config.mode != "none" and config.normalization not in {"True", "False", "none"}:
        errors.append("normalization must be True, False, or none")
    if config.mode != "none" and config.db_ratio != "none":
        try:
            ratio = float(config.db_ratio)
            if not 0 < ratio <= 1:
                errors.append("db_ratio must be in (0, 1]")
        except ValueError:
            errors.append("db_ratio must be numeric or none")
    if profile.atom_lines and config.min_support > profile.atom_lines:
        errors.append("min_support exceeds the number of input atom lines")
    if config.depth > 0 and not config.conj_exp:
        errors.append("depth greater than zero requires conjunction expansion")
    return errors


def _metta_value(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def make_script(repo: Path, dataset: Path, config: Config) -> Path:
    template = (repo / "run_miner.metta").read_text(encoding="utf-8")
    if config.mode == "none":
        body_lines = [
            line for line in template.splitlines()
            if not re.fullmatch(r"!\(import! &self [^)]+\)", line.strip())
        ]
        imports = [f"!(import! &self {module})" for module in MINIMAL_FREQUENT_IMPORTS]
        template = "\n".join(imports + body_lines) + "\n"
    dataset_expr = dataset.resolve().as_posix()
    template = re.sub(r"!\(import! &db [^\n]+\)",
                      f"!(import! &db {dataset_expr})", template, count=1)
    call = ("!(pattern-miner &res &db "
            f"{config.init_pattern} {config.min_support} {config.depth} "
            f"{config.mode} {_metta_value(config.normalization)} "
            f"{config.db_ratio} {_metta_value(config.conj_exp)})")
    template = re.sub(r"!\(pattern-miner &res &db[^\n]+\)", call, template, count=1)
    template = template.replace(
        "!(get-atoms &res)",
        f"!(println! \"{RESULT_BEGIN}\")\n"
        f"!(get-atoms &res)\n!(println! \"{RESULT_END}\")",
        1,
    )
    handle = tempfile.NamedTemporaryFile("w", suffix=".metta", prefix=".optimizer-",
                                         dir=repo, delete=False, encoding="utf-8")
    handle.write(template)
    handle.close()
    return Path(handle.name)


def parse_results(output: str, result_section_only: bool = False) -> tuple[int, list[float], list[float]]:
    if result_section_only:
        if RESULT_BEGIN not in output:
            return 0, [], []
        # PeTTa may flush get-atoms results after the end marker. The begin
        # marker is the reliable boundary after all translated source output.
        output = output.split(RESULT_BEGIN, 1)[1]
    support = [float(x) for x in re.findall(r"supportOf[\s\S]*?\s([0-9]+(?:\.[0-9]+)?)\)?", output)]
    surprise = [float(x) for x in re.findall(
        r"surprisingnessOf[\s\S]*?\s([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?)\)?", output)]
    # Count result atoms, not debug messages. Support and surprisingness outputs
    # are mutually exclusive in the repository's documented result format.
    count = len(support) if support else len(surprise)
    return count, support, surprise


def run_miner(repo: Path, petta: str, dataset: Path, config: Config,
              timeout: int, petta_venv: Path | None = None) -> RunResult:
    errors = validate_config(config, analyze_dataset(dataset))
    if errors:
        return RunResult(asdict(config), "invalid", 0.0, None, 0, [], [], "", "", "; ".join(errors))
    script = make_script(repo, dataset, config)
    command = ["sh", petta] if petta.endswith(".sh") else [petta]
    started = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    environment = os.environ.copy()
    if petta_venv:
        environment["VIRTUAL_ENV"] = str(petta_venv.resolve())
    try:
        proc = subprocess.run(command + [str(script)], cwd=repo, env=environment,
                              capture_output=True, text=True, timeout=timeout)
        elapsed = time.perf_counter() - started
        after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        # macOS reports bytes; Linux reports KiB.
        multiplier = 1 / (1024 * 1024) if os.uname().sysname == "Darwin" else 1 / 1024
        count, support, surprise = parse_results(proc.stdout + "\n" + proc.stderr, True)
        return RunResult(asdict(config), "ok" if proc.returncode == 0 else "failed",
                         elapsed, max(0.0, after - before) * multiplier, count,
                         support, surprise, proc.stdout, proc.stderr,
                         None if proc.returncode == 0 else f"exit code {proc.returncode}")
    except subprocess.TimeoutExpired as exc:
        return RunResult(asdict(config), "timeout", time.perf_counter() - started, None,
                         0, [], [], _text(exc.stdout), _text(exc.stderr), "timeout")
    except OSError as exc:
        return RunResult(asdict(config), "failed", time.perf_counter() - started, None,
                         0, [], [], "", "", f"could not start PeTTa: {exc}")
    finally:
        script.unlink(missing_ok=True)


def deterministic_candidates(profile: DatasetProfile, limit: int) -> list[Config]:
    upper = max(1, profile.atom_lines)
    supports = sorted({1, max(1, upper // 20), max(1, upper // 10), max(1, upper // 4)})
    configs = [Config(s, depth, conj_exp=(depth > 0))
               for s in supports for depth in (0, 1)]
    return configs[:limit]


def llm_candidates(profile: DatasetProfile, previous: list[RunResult], limit: int) -> tuple[list[Config], dict[str, Any]]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return deterministic_candidates(profile, limit), {"provider": "deterministic-fallback"}
    prompt = {
        "dataset": asdict(profile),
        "previous_runs": [asdict(run) | {"stdout": "", "stderr": ""} for run in previous],
        "schema": {"configurations": [{"min_support": 1, "depth": 0,
                                        "mode": "none", "normalization": "none",
                                        "db_ratio": "none", "conj_exp": True,
                                        "init_pattern": "$x"}]},
        "instruction": "Return JSON only. Suggest valid PeTTa miner configurations; do not invent mining results.",
    }
    body = json.dumps({"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                       "temperature": 0, "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": "You are a cautious experiment planner."},
                                    {"role": "user", "content": json.dumps(prompt)}]}).encode()
    request = urllib.request.Request(
        os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"),
        data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
        content = payload["choices"][0]["message"]["content"]
        items = json.loads(content).get("configurations", [])
        configs = [Config(**item) for item in items[:limit]]
        usage = payload.get("usage", {})
        return configs, {"provider": "openai-compatible", "model": body and json.loads(body)["model"],
                         "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")}
    except Exception as exc:
        return deterministic_candidates(profile, limit), {"provider": "fallback-after-llm-error", "error": str(exc)}


def select_best(results: list[RunResult], max_seconds: float | None, min_patterns: int) -> RunResult | None:
    eligible = [r for r in results if r.status == "ok" and r.pattern_count >= min_patterns
                and (max_seconds is None or r.elapsed_seconds <= max_seconds)]
    return min(eligible, key=lambda r: (r.elapsed_seconds, -max(r.surprisingness_values or [0]))) if eligible else None


def main() -> int:
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
    parser.add_argument("--output", type=Path, default=Path("optimizer-report.json"))
    args = parser.parse_args()
    repo, dataset = args.repo.resolve(), args.dataset.resolve()
    profile = analyze_dataset(dataset)
    if args.config_file:
        raw_configs = json.loads(args.config_file.read_text(encoding="utf-8"))
        configs = [Config(**item) for item in raw_configs[:args.trials]]
        llm = {"provider": "manual-config-file", "path": str(args.config_file.resolve())}
    else:
        configs, llm = llm_candidates(profile, [], args.trials)
    results = [run_miner(repo, args.petta, dataset, config, args.timeout, args.petta_venv)
               for config in configs]
    best = select_best(results, args.max_seconds, args.min_patterns)
    report = {"dataset": asdict(profile), "llm": llm, "results": [asdict(r) for r in results],
              "best": asdict(best) if best else None,
              "selection": {"max_seconds": args.max_seconds, "min_patterns": args.min_patterns}}
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "best": best.config if best else None,
                      "statuses": [r.status for r in results]}, indent=2))
    return 0 if best else 2


if __name__ == "__main__":
    raise SystemExit(main())

