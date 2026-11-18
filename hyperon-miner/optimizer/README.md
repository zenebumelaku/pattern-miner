# Configuration Optimizer

This prototype searches for faster valid configurations for the existing
Hyperon/PeTTa pattern miner. It profiles a dataset, validates configurations,
runs PeTTa, and records runtime, memory, and pattern results.

The optimizer does not generate patterns or replace the symbolic miner. PeTTa
remains the source of the mining results.

## Requirements

- Python 3.11
- PeTTa and SWI-Prolog on `PATH`
- Optional: Optuna for Optuna-based search

From `hyperon-miner/`, install the Python dependencies:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

Run the optimizer with a dataset and PeTTa executable:

```bash
.venv/bin/python optimizer/prototype.py \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --petta-venv .venv \
  --trials 3 \
  --timeout 30 \
  --output optimizer-report.json
```

Use a manual configuration file with `--config-file`:

```bash
.venv/bin/python optimizer/prototype.py \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --config-file optimizer/manual-baseline.json \
  --output manual-report.json
```

Run a comparison between search methods:

```bash
.venv/bin/python optimizer/prototype.py experiment \
  --repo . \
  --dataset experiments/data/very-small-ugly.metta \
  --petta /path/to/PeTTa/run.sh \
  --trials 1 \
  --methods default random optuna deterministic llm-warmstart \
  --output experiment-report.json
```

The LLM method requires provider credentials. Gemini is the default; an
OpenAI-compatible provider can be selected with `LLM_PROVIDER` and its API
environment variables. Use `--allow-llm-fallback` only for offline testing.

## Configuration

The miner call is:

```text
(pattern-miner output-space input-space init-pattern min-support depth
               mode normalization db-ratio conj-exp)
```

Example configuration:

```text
min_support=3
depth=0
mode=none
normalization=none
db_ratio=none
conj_exp=true
init_pattern=$x
```

## Tests

```bash
.venv/bin/python -m unittest discover -s optimizer -p 'test_*.py' -v
```

## Main files

- `miner.py` — dataset profiling, configuration validation, PeTTa execution,
  and result parsing.
- `cli.py` — normal and experiment command-line workflows.
- `search.py` — candidate generation and result selection.
- `llm.py` — LLM configuration proposals and fallback handling.
- `models.py` — shared configuration and result models.
- `test_prototype.py` — unit and CLI tests.
