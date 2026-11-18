# Hyperon Miner Configuration Optimizer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PeTTa](https://img.shields.io/badge/PeTTa-Symbolic_Miner-7C3AED)
![SWI-Prolog](https://img.shields.io/badge/SWI--Prolog-10.0.2-EF7C00?logo=prolog&logoColor=white)
![Optuna](https://img.shields.io/badge/Optuna-Experiment_Search-1A73E8)
![OpenAI](https://img.shields.io/badge/OpenAI-Compatible_LLM-412991?logo=openai&logoColor=white)

**An empirical LLM-assisted prototype for finding faster Hyperon/PeTTa miner configurations while preserving symbolic mining behavior.**

</div>

---

## Assignment Overview

This project investigates the question:

> **How can an LLM be integrated with Hyperon Miner to improve usability, correctness, or performance while preserving verifiable symbolic behavior?**

The prototype addresses **performance**: it proposes miner configurations, executes them through the existing PeTTa miner, validates symbolic results, and measures runtime and memory. The LLM is a configuration planner only—it never generates patterns or rewrites the miner.

### Research Goal

Find whether LLM warm start can find a low-runtime, valid miner configuration within a small fixed trial budget while maintaining measured recall against a reference run.

---

## What This Prototype Does

- Profiles an input `.metta` dataset.
- Validates the nine-argument miner configuration.
- Executes the existing Hyperon/PeTTa implementation unchanged.
- Measures elapsed runtime and process memory delta.
- Parses support values and symbolic pattern identities.
- Compares candidate pattern sets against a reference pattern set.
- Reports default, random, Optuna, deterministic, and LLM warm-start methods.
- Provides deterministic fallback behavior when no API key or mock mode is used.

The prototype does **not** replace symbolic mining with an LLM. PeTTa remains the source of all pattern results.

---

## Architecture

```mermaid
flowchart LR
    A[MeTTa Dataset] --> B[Dataset Profiler]
    B --> C{Configuration Method}
    C -->|Default| D[3 / 0]
    C -->|Random| E[Seeded Candidates]
    C -->|Optuna| F[Optuna Trials]
    C -->|Deterministic| G[Fallback Candidates]
    C -->|LLM Warm Start| H[JSON Configurations]
    D --> I[Configuration Validator]
    E --> I
    F --> I
    G --> I
    H --> I
    I -->|Valid| J[Temporary MeTTa Script]
    J --> K[Existing PeTTa Miner]
    K --> L[Pattern and Support Parser]
    L --> M[Recall Comparison]
    M --> N[JSON Experiment Report]
```

### LLM Boundary

The proposal service receives dataset summary statistics and previous run metadata only.

It must return JSON parameter sets such as:

```json
{
  "configurations": [
    {
      "min_support": 3,
      "depth": 0,
      "mode": "none",
      "normalization": "none",
      "db_ratio": "none",
      "conj_exp": true,
      "init_pattern": "$x"
    }
  ]
}
```

The LLM never receives or invents pattern identities, support values, or mining results.

### Failure Handling

- No API key: deterministic fallback.
- Mock mode: deterministic fallback labeled `MOCK`.
- LLM/network/JSON error: deterministic fallback with fallback metadata.
- Invalid configuration: recorded as `invalid`.
- PeTTa timeout: recorded as `timeout`.
- Miner crash or nonzero exit: recorded as `failed`.

---

## Experiment Protocol

The recorded experiment used:

| Setting | Value |
|---|---|
| Trial budget | 1 trial per method per seed |
| Seeds | `11`, `22`, `33` |
| Timeout | 30 seconds |
| Recall threshold | 20% |
| Datasets | 9, 20, and 60 parsed atom lines |
| Reference config | `min_support=1`, `depth=0` |

The baseline methods are:

- Default configuration
- Seeded random search
- Optuna
- Deterministic heuristic
- LLM warm start

> **LLM status:** No `OPENAI_API_KEY` was available. All warm-start rows in the recorded evidence are labeled **MOCK** and use the deterministic no-key fallback. They are not evidence of real LLM value.

---

## Measured Results

### Smoke Test

A one-config smoke test completed successfully in **4.486 seconds** and parsed **2 patterns**.

The raw symbolic output contained:

```text
(supportOf (, (Inheritance $_0 $_1) (Inheritance $_0 $_2)) 21)
(supportOf (, (Inheritance $_0 $_1) (Inheritance $_2 $_1)) 27)
```

### Configuration Sweep

| Dataset | Runtime range | Reference patterns |
|---|---:|---:|
| Very-small: 9 atoms | 2.116–12.619 s | 18 |
| Small: 20 atoms | 2.181–12.254 s | 32 |
| Ugly/man/soda-drinker: 60 atoms | 2.184–7.736 s | 86 |

### Comparison Verdict

**Verdict: PARTLY**

- The mock warm-start method achieved **100% measured recall** in all 18 seed/dataset comparisons.
- It was faster than the sole qualifying small-dataset Optuna result:
  **2.975 s versus 4.211 s**.
- It was slower than qualifying very-small random and Optuna results.
- Default, random, and Optuna lacked qualifying results on several datasets.
- Real LLM performance remains untested.

Full evidence is available in [`results/`](../results/):

- [Problem sweep](../results/problem_sweep.md)
- [Testable hypothesis](../results/hypothesis.md)
- [Baseline comparison](../results/comparison.md)
- [Architecture](../results/architecture.md)
- [Presentation slides](../results/slides.md)

---

## Running the Prototype

### Prerequisites

- Python 3.11
- PeTTa
- SWI-Prolog available on `PATH`
- Optuna for Optuna experiments

On macOS, expose the installed SWI-Prolog executable before running experiments:

```bash
export PATH="/Applications/SWI-Prolog.app/Contents/MacOS:$PATH"
```

Verify the environment:

```bash
swipl --version
python3 --version
```

### Manual Configuration Run

```bash
cd hyperon-miner

.venv/bin/python optimizer/prototype.py \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --petta-venv .venv \
  --trials 3 \
  --timeout 30 \
  --output optimizer-report.json
```

### Manual Configuration File

```bash
.venv/bin/python optimizer/prototype.py \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --petta-venv .venv \
  --config-file optimizer/manual-baseline.json \
  --trials 2 \
  --timeout 30 \
  --output optimizer/manual-report.json
```

### Experiment Mode

```bash
.venv/bin/python optimizer/prototype.py experiment \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --petta-venv .venv \
  --trials 1 \
  --timeout 30 \
  --seeds 11 22 33 \
  --methods default random optuna deterministic llm-warmstart \
  --recall-threshold 0.20 \
  --mock-llm \
  --llm-mode warmstart \
  --output experiment-report.json
```

### Real OpenAI-Compatible Provider

Set a provider key and optional endpoint/model:

```bash
export OPENAI_API_KEY="your-api-key"
export LLM_PROVIDER="openai"
export OPENAI_MODEL="gpt-4o-mini"
# Optional:
export OPENAI_BASE_URL="https://api.openai.com/v1/chat/completions"
```

Then run without `--mock-llm`. Provider usage and errors are recorded only in the experiment report.

### Gemini Provider

Gemini is the default provider and uses the native `generateContent` API. For a
consistent project-wide setup, copy the repository's `.env.example` to `.env` and
replace the placeholder key. Both CLI modes load that file, and explicit shell
variables take precedence. You can also export the variables directly:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export GEMINI_MODEL="gemini-3.1-flash-lite"
unset GEMINI_BASE_URL
```

Run without `--mock-llm`. Verify the report says `"provider": "gemini"` before
counting the run as live LLM evidence. If a request fails, the report records
the model, endpoint, and provider error details; fallback measurements are not
live Gemini results. Add `--require-gemini` to fail on a missing key, mock mode,
provider error, or fallback instead of silently recording a non-live result. Use
that flag for runs intended to produce Gemini evidence across every seed.

---

## Miner Configuration

The existing implementation accepts:

```text
(pattern-miner output-space input-space init-pattern
               min-support depth mode normalization
               db-ratio conj-exp)
```

The default experiment configuration is:

```text
min_support=3
depth=0
mode=none
normalization=none
db_ratio=none
conj_exp=true
init_pattern=$x
```

---

## Testing

Run the optimizer test suite from `hyperon-miner/`:

```bash
.venv/bin/python -m unittest discover -s optimizer -p 'test_*.py' -v
```

The suite covers configuration validation, output parsing, pattern-set parsing, script generation, fallback behavior, fake-PeTTa execution, timeout serialization, and CLI report creation.

---

## Limitations

- Runtime and memory are process-level measurements, not isolated algorithm-only profiles.
- Memory values are child-process high-water-mark deltas.
- Recall is set-based; it does not model pattern support ranking.
- The no-key experiment is deterministic and not evidence of real LLM quality.
- Random, Optuna, and warm-start methods currently use a small one-trial budget.
- The prototype does not modify or replace the PeTTa symbolic miner.
- PeTTa startup and interpreter behavior are included in measured runtimes.

---

## Repository Structure

```text
optimizer/
├── prototype.py        Backward-compatible CLI entry point
├── cli.py              Normal and experiment CLI workflows
├── miner.py            Dataset analysis, script generation, and PeTTa runs
├── llm.py              LLM configuration proposals and fallback logic
├── search.py           Candidate generation and result selection
├── models.py           Shared configuration and result data models
├── env.py              Project .env loading
├── test_prototype.py   Unit and CLI tests
├── README.md           Assignment and usage documentation
└── *.json              Configuration and report examples

results/
├── problem_sweep.md
├── hypothesis.md
├── comparison.md
├── architecture.md
└── slides.md
```
