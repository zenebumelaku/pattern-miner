# Live LLM experiment summary

## Problem

- Objective: use an LLM to propose PeTTa miner configurations.
- Symbolic results remain owned by the existing PeTTa miner.
- Evaluation uses measured runtime and set-based recall against a reference run.

## Protocol

- Dataset: `experiments/data/very-small-ugly.metta` (9 atom lines).
- Reference: `min_support=1`, `depth=0` (18 patterns).
- One trial per seed; seeds `11`, `22`, and `33`.
- PeTTa timeout: 20 seconds; recall threshold: 20%.
- Provider: live Gemini `gemini-3.1-flash-lite`.

## Live result

- Gemini returned valid JSON on all three provider calls.
- All three LLM records report `real_llm=true` and zero LLM fallback.
- Gemini selected `min_support=1`, `depth=1` for the one-trial runs.
- All seeds completed with two patterns and 0% reference recall in 8.234–9.487 seconds.
- The deterministic baseline completed in 3.622–4.498 seconds with 100% recall.

## Verdict

The live run is inconclusive. It proves the real provider-to-miner path is
working, but this prompt/configuration budget did not produce a qualifying LLM
configuration or a performance improvement.
