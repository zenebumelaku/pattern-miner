"""Data models shared by the optimizer modules.

Main responsibility: define the immutable configuration and serializable
dataset/run result structures exchanged between optimizer components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Immutable configuration supplied to a miner run.
@dataclass(frozen=True)
class Config:
    min_support: int
    depth: int
    mode: str = "none"
    normalization: str = "none"
    db_ratio: str = "none"
    conj_exp: bool = True
    init_pattern: str = "$x"


# Dataset statistics used to plan and validate experiments.
@dataclass
class DatasetProfile:
    path: str
    atom_lines: int
    link_lines: int
    predicates: dict[str, int]
    distinct_symbols: int
    bytes: int


# Serialized outcome of a single miner configuration.
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
    patterns: list[str] | None = None
