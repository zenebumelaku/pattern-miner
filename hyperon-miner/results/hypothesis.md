# Hypothesis

## Status: blocked before preregistration

The required manual sweep was executed, but all 24 configurations failed before the miner started (`swipl: command not found`). There are no successful runtime or pattern-recall measurements from which to choose a meaningful speedup threshold **X** or recall threshold **Y**. Assigning numeric values now would fabricate a hypothesis basis, so no hypothesis is preregistered and Step 4 cannot test the requested claim.

The requested fixed budget of **N = 3 candidate trials** was used for the supported baseline and mock-fallback attempts. This is the assignment's small budget, not a value inferred from sweep results. No result from those failures is treated as support for or against LLM value.

To unblock the hypothesis, install or expose SWI-Prolog (`swipl`) in the environment, rerun the sweep successfully, then set X and Y from the measured runtime/recall distribution before running the comparisons.
