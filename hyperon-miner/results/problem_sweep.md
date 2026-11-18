# Problem measurement: configuration sweep

## CLI inventory (Step 1)

Run from `hyperon-miner/`; all commands use `optimizer/prototype.py`.

1. Manual sweep: `python3 optimizer/prototype.py --repo . --dataset DATA.metta --petta "$PETTA" --petta-venv "$PETTA_VENV" --config-file CONFIGS.json --trials N --timeout S --output REPORT.json`.
2. Default configuration: there is no dedicated flag; use `--config-file` with a configuration such as the checked-in miner call, `min_support=3, depth=0`.
3. Random search: unavailable; no random-search command, strategy, or flag exists.
4. Optuna: unavailable; no Optuna integration or command exists.
5. Deterministic heuristic: `--trials N` without `--config-file` selects `deterministic_candidates` only through the no-key proposal fallback; no standalone strategy flag exists.
6. LLM warm start: the same no-config command calls the OpenAI-compatible endpoint when `OPENAI_API_KEY` is set; `OPENAI_MODEL` and `OPENAI_BASE_URL` are optional environment settings. Without the key, the code uses a deterministic fallback, not a mock client.
7. Reference for recall: no reference/recall command exists; a manual `min_support=1, depth=0` run can be made with `--config-file`, but the CLI only parses pattern counts/supports, not pattern identities for recall.
8. No `--seed` flag is present; `--trials` counts configurations, not repeatable seeded runs.

## Procedure and outcome

Used the existing CLI with `--timeout 30`, and the installed `/Users/zeni/PeTTa/run.sh` plus Python 3.11 venv. Three datasets spanning 9, 20, and 164 parsed atom lines were measured. Each has four `min_support` values crossed with `depth` 0 and 1 (24 configurations total). Every attempt failed before PeTTa started because the runner could not find `swipl`; consequently these timing and memory readings are launch-failure overhead, not miner cost or usable problem evidence.

| Dataset (parsed atom lines) | min_support | depth | Runtime (s) | Peak memory (MB) | Patterns | Status |
|---|---:|---:|---:|---:|---:|---|
| very-small-ugly (9) | 1 | 0 | 0.024247 | 1.136719 | 0 | failed |
| very-small-ugly (9) | 1 | 1 | 0.017981 | 0.007812 | 0 | failed |
| very-small-ugly (9) | 2 | 0 | 0.021366 | 0.000000 | 0 | failed |
| very-small-ugly (9) | 2 | 1 | 0.017464 | 0.000000 | 0 | failed |
| very-small-ugly (9) | 3 | 0 | 0.022989 | 0.003906 | 0 | failed |
| very-small-ugly (9) | 3 | 1 | 0.151287 | 0.007812 | 0 | failed |
| very-small-ugly (9) | 4 | 0 | 0.035796 | 0.007812 | 0 | failed |
| very-small-ugly (9) | 4 | 1 | 0.025124 | 0.000000 | 0 | failed |
| small-ugly (20) | 2 | 0 | 0.034588 | 1.164062 | 0 | failed |
| small-ugly (20) | 2 | 1 | 0.038369 | 0.000000 | 0 | failed |
| small-ugly (20) | 4 | 0 | 0.041641 | 0.000000 | 0 | failed |
| small-ugly (20) | 4 | 1 | 0.035130 | 0.003906 | 0 | failed |
| small-ugly (20) | 8 | 0 | 0.046621 | 0.000000 | 0 | failed |
| small-ugly (20) | 8 | 1 | 0.043894 | 0.000000 | 0 | failed |
| small-ugly (20) | 12 | 0 | 0.075795 | 0.000000 | 0 | failed |
| small-ugly (20) | 12 | 1 | 0.038548 | 0.000000 | 0 | failed |
| II_surp_kb/kb1 (164) | 5 | 0 | 0.043116 | 1.152344 | 0 | failed |
| II_surp_kb/kb1 (164) | 5 | 1 | 0.131025 | 0.000000 | 0 | failed |
| II_surp_kb/kb1 (164) | 10 | 0 | 0.150731 | 0.007812 | 0 | failed |
| II_surp_kb/kb1 (164) | 10 | 1 | 0.036294 | 0.000000 | 0 | failed |
| II_surp_kb/kb1 (164) | 20 | 0 | 0.037040 | 0.000000 | 0 | failed |
| II_surp_kb/kb1 (164) | 20 | 1 | 0.142472 | 0.003906 | 0 | failed |
| II_surp_kb/kb1 (164) | 40 | 0 | 0.046353 | 0.003906 | 0 | failed |
| II_surp_kb/kb1 (164) | 40 | 1 | 0.033027 | 0.000000 | 0 | failed |

Cost variation across configurations (reported process launch failure overhead):
- very-small-ugly runtime: 0.017464–0.151287 s (range 0.133823 s); reported peak-memory delta: 0.000000–1.136719 MB.
- small-ugly runtime: 0.034588–0.075795 s (range 0.041207 s); reported peak-memory delta: 0.000000–1.164062 MB.
- II_surp_kb/kb1 runtime: 0.033027–0.150731 s (range 0.117704 s); reported peak-memory delta: 0.000000–1.152344 MB.

These are not configuration-dependent mining costs: all 24 trials have status `failed`, zero patterns, and the same missing-`swipl` cause. The runner's reported memory is a child-process `ru_maxrss` delta and several entries are zero; these failure-only values should not be interpreted as miner peak memory.
