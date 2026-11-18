# Hypothesis

Within a fixed budget of `N=1` trial per seed, LLM warm start must find a configuration at least `X=10%` faster than the default configuration and random search while recovering at least `Y=20%` of the reference patterns. The metric is the best runtime among configurations whose measured pattern-set recall is at least 20%; a method with no qualifying result has no best runtime.

The thresholds use the sweep spread and the low-cost depth-0 region: runtime differed by 5.552–10.503 seconds across the three datasets, and `N=1` keeps the baseline comparison within the short timeout. The 20% recall threshold is a measurable preregistered floor based on reference pattern counts of 18, 32, and 86.

The comparison was run on three seeds (`11`, `22`, `33`) with a 30-second timeout. There was no real `OPENAI_API_KEY`, and the LLM warm-start rows are explicitly MOCK values from the deterministic no-key fallback.
