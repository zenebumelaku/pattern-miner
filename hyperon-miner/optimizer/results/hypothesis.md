# Hypothesis

Within a fixed budget of `N=1` trial per seed, LLM warm start must find a
configuration at least `X=10%` faster than the default configuration and random
search while recovering at least `Y=20%` of the reference patterns. The metric
is the best runtime among configurations whose measured pattern-set recall is
at least 20%; a method with no qualifying result has no best runtime.

The live comparison was run on three seeds (`11`, `22`, `33`) with a 20-second
PeTTa timeout. Every warm-start row was a real Gemini request using
`gemini-3.1-flash-lite`, with `real_llm=true` and zero LLM fallbacks. The
provider selected a depth-1 configuration; all three miner runs completed, but
none met the recall threshold. The result is therefore inconclusive rather
than evidence of an LLM speedup.
