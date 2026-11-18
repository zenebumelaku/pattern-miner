"""Dataset analysis and PeTTa execution.

Main responsibility: validate datasets and configurations, generate temporary
PeTTa scripts, execute the miner, and parse measured results.
"""

from __future__ import annotations

import os
import re
import resource
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Config, DatasetProfile, RunResult


# Minimal PeTTa imports used for frequent-pattern runs.
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

# Markers used to isolate machine-readable PeTTa results.
RESULT_BEGIN = "OPTIMIZER_RESULTS_BEGIN"
RESULT_END = "OPTIMIZER_RESULTS_END"


# Dataset profiling.
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


# Configuration validation.
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


# Values and temporary scripts passed to PeTTa.
def _metta_value(value: Any) -> str:
    return ("True" if value else "False") if isinstance(value, bool) else str(value)


def _text(value: str | bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


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
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".metta", prefix=".optimizer-", dir=repo,
        delete=False, encoding="utf-8",
    )
    handle.write(template)
    handle.close()
    return Path(handle.name)


# Result parsing.
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


def parse_pattern_set(output: str) -> list[str]:
    if RESULT_BEGIN in output:
        output = output.split(RESULT_BEGIN, 1)[1]
    patterns: list[str] = []
    for match in re.finditer(
        r"\(supportOf\s+(.+?)\s+[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?\)",
        output,
        re.DOTALL,
    ):
        pattern = re.sub(r"\s+", " ", match.group(1)).strip()
        if pattern:
            patterns.append(pattern)
    return sorted(set(patterns))


# PeTTa execution and result collection.
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
        output = proc.stdout + "\n" + proc.stderr
        count, support, surprise = parse_results(output, True)
        patterns = parse_pattern_set(output)
        return RunResult(asdict(config), "ok" if proc.returncode == 0 else "failed",
                         elapsed, max(0.0, after - before) * multiplier, count,
                         support, surprise, proc.stdout, proc.stderr,
                         None if proc.returncode == 0 else f"exit code {proc.returncode}",
                         patterns if proc.returncode == 0 else [])
    except subprocess.TimeoutExpired as exc:
        return RunResult(asdict(config), "timeout", time.perf_counter() - started, None,
                         0, [], [], _text(exc.stdout), _text(exc.stderr), "timeout")
    except OSError as exc:
        return RunResult(asdict(config), "failed", time.perf_counter() - started, None,
                         0, [], [], "", "", f"could not start PeTTa: {exc}")
    finally:
        script.unlink(missing_ok=True)


# Deterministic baseline candidate generation. This is intentionally separate
# from the live LLM proposal path and is useful for reproducible comparisons.
def deterministic_candidates(profile: DatasetProfile, limit: int) -> list[Config]:
    upper = max(1, profile.atom_lines)
    supports = sorted({1, max(1, upper // 20), max(1, upper // 10), max(1, upper // 4)})
    configs = [Config(s, depth, conj_exp=(depth > 0))
               for s in supports for depth in (0, 1)]
    return configs[:limit]
