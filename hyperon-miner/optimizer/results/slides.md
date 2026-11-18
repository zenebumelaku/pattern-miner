# Problem

- Objective: use an LLM to improve one miner configuration-selection aspect.
- Three real datasets: 9, 20, and 60 parsed atom lines.
- Manual sweep runtime: 2.116–12.619, 2.181–12.254, and 2.184–7.736 seconds.
- Reference patterns: 18, 32, and 86.
- 30-second timeout and 1-trial fixed budget.

# Hypothesis

- N = 1 trial per seed.
- X = 10% faster than default and random search.
- Y = 20% reference-pattern recall.
- Seeds: 11, 22, and 33.
- Metric: fastest run meeting the recall threshold.

# Architecture

- Profiler sends dataset summary statistics to the proposal boundary.
- Existing PeTTa miner remains the symbolic source.
- Validator accepts or rejects parameter sets.
- Timeout/crash/failed trial is recorded.
- LLM returns JSON parameters only, never patterns.

# Prototype

- Experiment methods: default, random, Optuna, deterministic, and warm start.
- Smoke test: 4.486 seconds and 2 parsed patterns.
- Valid-config rate: 3/3 for every method and dataset.
- No real API key was available.
- Comparison used mock/deterministic warm-start rows.

# Baseline

- Very-small: Optuna 2.168 seconds; mock 2.604 seconds at 100% recall.
- Small: Optuna 4.211 seconds; mock 2.975 seconds at 100% recall.
- Ugly: no random or Optuna qualifying result.
- Deterministic 100% recall: 2.363–5.351 seconds across datasets.
- All table values come from 30-second runs.

# Results

- Verdict: PARTLY.
- Mock recall: 100% on all 18 seed/dataset comparisons.
- Mock was faster than the one qualifying small Optuna result.
- It was slower than qualifying very-small random/Optuna results.
- Real LLM value remains untested; no real API call occurred.
