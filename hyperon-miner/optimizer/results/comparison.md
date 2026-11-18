# Live LLM comparison

This report is the evidence summary for
[live-llm-experiment.json](../live-llm-experiment.json). It used one trial per
seed, seeds `11`, `22`, and `33`, a 20-second PeTTa timeout, and a 20% recall
threshold against the `min_support=1, depth=0` reference run.

## very-small-ugly

The reference run produced 18 patterns. The deterministic baseline and live
LLM warm-start measurements were:

| Method | Seed | Provider | Configuration | Status | Runtime (s) | Recall | LLM tokens |
|---|---:|---|---|---|---:|---:|---:|
| Deterministic baseline | 11 | baseline | support 1, depth 0 | ok | 3.622 | 100% | N/A |
| Deterministic baseline | 22 | baseline | support 1, depth 0 | ok | 3.803 | 100% | N/A |
| Deterministic baseline | 33 | baseline | support 1, depth 0 | ok | 4.498 | 100% | N/A |
| LLM warm start | 11 | Gemini | support 1, depth 1 | ok | 9.487 | 0% | 182 / 150 |
| LLM warm start | 22 | Gemini | support 1, depth 1 | ok | 8.591 | 0% | 182 / 150 |
| LLM warm start | 33 | Gemini | support 1, depth 1 | ok | 8.234 | 0% | 182 / 150 |

All three warm-start metadata records report `provider=gemini`,
`model=gemini-3.1-flash-lite`, `real_llm=true`, and `fallback_count=0`.

## Interpretation

- The LLM boundary was exercised with real provider calls; no deterministic
  proposal was substituted for an LLM response.
- The selected depth-1 configuration produced two patterns in each run, but
  neither matched the depth-0 reference pattern set, so it did not meet the 20%
  recall floor.
- The deterministic baseline recovered all reference patterns in all three
  seeds.
- This small run does not support a claim that the LLM improves runtime or
  recall. It was slower than the deterministic baseline in all three seeds.
  More trials and a prompt that explicitly balances depth against reference
  recall are needed.
