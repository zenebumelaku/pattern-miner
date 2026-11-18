# Baseline comparison

All methods used 3 seeds (`11`, `22`, `33`), a 1-trial budget, a 30-second timeout, and the preregistered 20% recall threshold. Pattern recall was computed by set intersection against the `min_support=1, depth=0` reference run.

## very-small-ugly

| Method | Best runtime (s) | Memory (MB) | Recall vs reference | Trials to target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---:|---:|---:|---:|---:|---:|---|
| Default | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Random | 2.519 | 0.0000000 | 33.3% | 1 | 3/3 | 0 | N/A |
| Optuna | 2.168 | 0.0000000 | 33.3% | 1 | 3/3 | 0 | N/A |
| Deterministic heuristic | 2.987 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | N/A |
| MOCK LLM warm start | 2.604 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | 0 / not recorded / no charge |

## small-ugly

| Method | Best runtime (s) | Memory (MB) | Recall vs reference | Trials to target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---:|---:|---:|---:|---:|---:|---|
| Default | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Random | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Optuna | 4.211 | 0.0000000 | 25.0% | 1 | 3/3 | 0 | N/A |
| Deterministic heuristic | 2.363 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | N/A |
| MOCK LLM warm start | 2.975 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | 0 / not recorded / no charge |

## ugly-man-sodaDrinker

| Method | Best runtime (s) | Memory (MB) | Recall vs reference | Trials to target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---:|---:|---:|---:|---:|---:|---|
| Default | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Random | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Optuna | N/A | N/A | N/A | N/A | 3/3 | 0 | N/A |
| Deterministic heuristic | 5.351 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | N/A |
| MOCK LLM warm start | 6.906 | 0.0000000 | 100.0% | 1 | 3/3 | 3 | 0 / no real call / no charge |

## Failures and limitations

- No invalid JSON response occurred.
- No rejected configuration occurred; valid-config rate was 3/3 for every method and dataset.
- No timeout or miner crash occurred in the comparison runs.
- The deterministic no-key path was used for every LLM-warm-start row.
- The deterministic heuristic and mock warm start are separate labels in the report, but both returned the same one-trial no-key fallback result.
- The default and some random/Optuna runs did not meet the 20% recall threshold, so their best runtime is unavailable rather than zero.
- The real LLM was not used because `OPENAI_API_KEY` was unset.

## Verdict: partly

The mock warm-start method achieved 100% measured recall in all 18 seed/dataset rows, but it is not evidence of real LLM value. It was faster than the sole qualifying small-dataset Optuna result (2.975 vs 4.211 seconds) but slower than qualifying very-small Optuna and random results. Default, random, and Optuna had no qualifying result on several datasets, so the fixed 10% speedup claim cannot be established consistently. The 20% recall result is symbolic and set-based, while runtime and memory are single-process measurements with three seeds.
