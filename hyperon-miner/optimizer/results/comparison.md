# Live Gemini + PeTTa mining enhancement

This is a fresh live rerun recorded in
[gemini-petta-rerun.json](./gemini-petta-rerun.json). Gemini was called directly
with model `gemini-3.1-flash-lite`; the response was valid JSON, used no
fallback, and supplied three valid PeTTa configurations. Every configuration
shown below was executed by PeTTa against
`experiments/data/very-small-ugly.metta`.

The assignment baseline is the project default configuration:
`min_support=3, depth=0, conj_exp=true`. The mining-enhancement gate requires a
successful live proposal to preserve the reference recall and return more
patterns than that default. Runtime is reported as a secondary metric because
pattern coverage is the primary mining objective. The gate is implemented by
`enhances_mining_over_baseline` in [`search.py`](../search.py).

## Fresh rerun

| Method | Configuration | PeTTa runs | Patterns | Reference recall | Runtime (s) | Status |
|---|---|---:|---:|---:|---:|---|
| Default baseline | support 3, depth 0, conj-exp true | 3 | 2 each | 0% | 14.11, 7.50, 12.04 (median 12.04) | ok |
| Live Gemini proposal | support 1, depth 0, conj-exp false | 3 | 18 each | 100% | 13.09, 16.15, 8.33 (median 13.09) | ok |
| Live Gemini proposal | support 1, depth 1, conj-exp true | 1 | 2 | 0% | 39.49 | ok |
| Live Gemini proposal | support 2, depth 1, conj-exp true | 1 | 2 | 0% | 13.94 | ok |

## Result

The live Gemini proposal enhanced the mining result:

- pattern coverage increased from 2 to 18 patterns, a gain of 16 patterns and
  a 9x increase;
- the selected proposal recovered 100% of the 18-pattern reference set;
- all PeTTa executions completed successfully with no LLM fallback;
- the proposal's median runtime was 1.05 seconds slower than the default
  baseline, so this is a coverage improvement with a small runtime trade-off,
  not a claimed speedup.

The depth-1 proposals were measured and rejected because they produced only two
patterns with 0% reference recall. The selected support-1 depth-0 proposal is
the evidence that the live LLM improved the mining output rather than merely
being called.
