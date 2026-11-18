# Runtime Validation Report

**Generated**: 2026-11-18
**Target**: `optimizer/prototype.py` and its optimizer modules

## Summary

| Check | Status | Details |
|---|---|---|
| Unit tests | PASS | 15 optimizer tests passed |
| Live provider request | PASS | Gemini returned valid JSON with 291 tokens in the direct smoke request |
| Live experiment | PASS | Three provider calls completed with `provider=gemini`, `real_llm=true`, and zero LLM fallbacks |
| PeTTa reference run | PASS | Reference configuration completed and produced 18 patterns |
| Strict live-mode enforcement | PASS | Missing credentials and provider failures stop the run instead of recording fallback evidence |

## Live experiment evidence

The reproducible report is [live-llm-experiment.json](optimizer/live-llm-experiment.json).
It used one trial for each of seeds `11`, `22`, and `33` on
`very-small-ugly.metta`, with a 20-second PeTTa timeout.

- Gemini model: `gemini-3.1-flash-lite`.
- LLM proposal: `min_support=1`, `depth=1`.
- All three seeds completed in 8.234–9.487 seconds with two patterns and 0% reference recall.
- The deterministic baseline completed in 3.622–4.498 seconds with 100% recall.

The result is a real provider experiment, but it is inconclusive as a quality
or performance claim.
