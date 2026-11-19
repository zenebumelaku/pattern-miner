# Hypothesis

Within a fixed live-LLM budget, Gemini warm-start should improve mining
coverage over the project's default `min_support=3, depth=0` configuration
while preserving the reference pattern recall. Runtime is measured and
reported as a secondary objective.

The fresh rerun supports the hypothesis: the live Gemini support-1 proposal
returned 18 patterns on every PeTTa run versus 2 for the default baseline, with
100% recall of the 18-pattern reference set. The median runtime trade-off was
13.09 seconds versus 12.04 seconds.

## Acceptance rule

The LLM is considered to enhance mining only when its successful proposal has
at least the default baseline's reference recall and strictly more measured
patterns. Missing credentials, fallback proposals, invalid configurations,
timeouts, and non-improving pattern counts do not pass.

## Failure path

- Missing credentials in live mode: fail before recording LLM evidence.
- Transient provider status: bounded retry, then fail the live run.
- Invalid JSON or invalid configuration: fail the live run.
- Explicit `--allow-llm-fallback`: deterministic fallback for offline development only.
- Miner timeout or nonzero process exit: recorded as timeout or failed.
