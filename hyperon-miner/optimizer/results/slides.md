# Live Gemini + PeTTa mining enhancement

## Problem

- Objective: use an LLM to propose PeTTa miner configurations.
- Symbolic results remain owned by the existing PeTTa miner.
- Mining coverage is primary; runtime and set-based reference recall are also measured.

## Protocol

- Dataset: `experiments/data/very-small-ugly.metta` (9 atom lines).
- Default baseline: `min_support=3`, `depth=0`, `conj_exp=true` (2 patterns).
- Reference: `min_support=1`, `depth=0`, `conj_exp=false` (18 patterns).
- Provider: live Gemini `gemini-3.1-flash-lite`, zero fallback.
- Every returned configuration was executed by PeTTa.

## Live result

- Gemini returned three valid configurations.
- The selected support-1 depth-0 proposal produced 18 patterns on three runs.
- The default baseline produced 2 patterns on three runs.
- Reference recall was 100% for the selected proposal and 0% for the default baseline.
- Median runtimes were 13.09s for Gemini and 12.04s for the baseline.

## Verdict

The live Gemini proposal passes the mining-enhancement gate: 18 patterns versus
2, a 16-pattern gain and 9x coverage increase. It has a small median runtime
trade-off, which is reported rather than hidden.

## Acceptance rule

`LLM enhancement = successful live run AND preserved reference recall AND more patterns than the default baseline`.
