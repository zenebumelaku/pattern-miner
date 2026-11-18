# Baseline comparison

## Run setup

Three datasets were used: `very-small-ugly.metta` (9 parsed atom lines), `small-ugly.metta` (20), and `II_surp_kb/kb1.metta` (164). The timeout was 30 seconds; the supported CLI was given a three-configuration budget for default, mock-fallback, and reference attempts. The CLI has no seed option, so three seeded runs could not be reproduced. `OPENAI_API_KEY` was unset; the real LLM was not called. The no-key path is the deterministic fallback generator, not a separate mock-client implementation.

`swipl` was missing from `PATH`, so all launched trials exited before mining. The columns for best successful runtime, mining memory, recall, and reaching a target are therefore unavailable, not zero. Target recall was not set because the failed sweep could not provide X/Y.

## very-small-ugly (9 parsed atom lines)

| Method | Best runtime | Memory | Recall vs reference | Trials to reach target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---|---|---|---|---|---|---|
| Default config (`min_support=3, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |
| Random search | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Optuna | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Standalone deterministic heuristic | no separate strategy/command | N/A | N/A | N/A | N/A | N/A | N/A |
| MOCK - not evidence of LLM value (deterministic no-key fallback) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 1 provider fallback; 0 API-error fallbacks | no API call; not recorded / not recorded / no charge |
| Reference (`min_support=1, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |

## small-ugly (20 parsed atom lines)

| Method | Best runtime | Memory | Recall vs reference | Trials to reach target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---|---|---|---|---|---|---|
| Default config (`min_support=3, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |
| Random search | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Optuna | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Standalone deterministic heuristic | no separate strategy/command | N/A | N/A | N/A | N/A | N/A | N/A |
| MOCK - not evidence of LLM value (deterministic no-key fallback) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 1 provider fallback; 0 API-error fallbacks | no API call; not recorded / not recorded / no charge |
| Reference (`min_support=1, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |

## II_surp_kb/kb1 (164 parsed atom lines)

| Method | Best runtime | Memory | Recall vs reference | Trials to reach target | Valid-config rate | Fallback count | LLM tokens / latency / cost |
|---|---|---|---|---|---|---|---|
| Default config (`min_support=3, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |
| Random search | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Optuna | not implemented | N/A | N/A | N/A | N/A | N/A | N/A |
| Standalone deterministic heuristic | no separate strategy/command | N/A | N/A | N/A | N/A | N/A | N/A |
| MOCK - not evidence of LLM value (deterministic no-key fallback) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 1 provider fallback; 0 API-error fallbacks | no API call; not recorded / not recorded / no charge |
| Reference (`min_support=1, depth=0`) | none (0/3 succeeded) | N/A | N/A | N/A | 3/3 (100%; client validation only) | 0 | N/A |

“Valid-config rate” means configurations accepted by the optimizer's client-side validator; it does not mean successful mining. The fallback count is one deterministic provider selection for each no-key invocation; the miner failures did not trigger additional LLM/API fallback behavior. No baseline, mock, or reference run produced patterns, so recall is not calculable.

## Failures and missing comparisons

- 24/24 manual-sweep trials, plus all default, reference, and deterministic-fallback trials, failed with `/Users/zeni/PeTTa/run.sh: line 11: swipl: command not found` (exit code 127 from the runner; optimizer CLI exit code 2 because no best run was available).
- No invalid JSON response was observed because the LLM endpoint was not contacted.
- No rejected configuration or miner timeout was observed in the comparison trials; process launch failed first.
- The checked-in CLI has no random-search or Optuna implementation/flag, no independent heuristic strategy selector, and no seed option. These were not run.
- No real LLM run occurred because `OPENAI_API_KEY` was unset. Mock-labelled rows are deterministic no-key fallbacks only and are explicitly not evidence of LLM value.
- The reference attempts failed, and the report parser does not expose pattern identities; recall and trials-to-target could not be calculated even from pattern counts alone.

## Verdict: partly (inconclusive)

The evidence does not establish or refute the hypothesis: the sweep and comparison runs never started the miner. The only observed configuration variation is process-launch overhead, which is not a valid proxy for mining runtime or memory. Random search and Optuna are absent from the existing CLI, and there is no seed control, so those comparisons cannot be reproduced without changing the existing optimizer, which was out of scope. The no-key path exercises a deterministic fallback, not an LLM or mock client, and no recall can be measured without a successful reference result. Thus the comparison is **partly complete as an execution audit but inconclusive about the hypothesis**.
