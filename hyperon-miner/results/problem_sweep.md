# Problem measurement: manual configuration sweep

## Setup

The smoke test passed at Step 0. SWI-Prolog 10.0.2 was exposed through `/Applications/SWI-Prolog.app/Contents/MacOS`; a one-config run on `very-small-ugly.metta` completed in 4.486 seconds and parsed 2 patterns. Raw support lines included `(supportOf (, (Inheritance $_0 $_1) (Inheritance $_0 $_2)) 21)` and `(supportOf (, (Inheritance $_0 $_1) (Inheritance $_2 $_1)) 27)`.

The sweep used three real datasets and a 30-second timeout:

| Dataset | Parsed atom lines | Support values | Depth |
|---|---:|---|---|
| `experiments/data/very-small-ugly.metta` | 9 | 1, 2, 3 | 0, 1 |
| `experiments/data/small-ugly.metta` | 20 | 2, 4, 8 | 0, 1 |
| `experiments/data/ugly_man_sodaDrinker.metta` | 60 | 5, 10, 20 | 0, 1 |

## Manual sweep

| Dataset | min_support | depth | Runtime (s) | Peak memory (MB) | Patterns | Status |
|---|---:|---:|---:|---:|---:|---|
| very-small-ugly | 1 | 0 | 3.956 | 30.7578125 | 18 | ok |
| very-small-ugly | 1 | 1 | 12.619 | 0.03515625 | 2 | ok |
| very-small-ugly | 2 | 0 | 2.116 | 0.0000000 | 6 | ok |
| very-small-ugly | 2 | 1 | 5.225 | 0.01171875 | 2 | ok |
| very-small-ugly | 3 | 0 | 2.193 | 0.0078125 | 6 | ok |
| very-small-ugly | 3 | 1 | 4.970 | 0.0000000 | 2 | ok |
| small-ugly | 2 | 0 | 2.181 | 30.82421875 | 12 | ok |
| small-ugly | 2 | 1 | 7.894 | 0.07421875 | 2 | ok |
| small-ugly | 4 | 0 | 3.391 | 0.0000000 | 8 | ok |
| small-ugly | 4 | 1 | 12.254 | 0.0000000 | 2 | ok |
| small-ugly | 8 | 0 | 2.464 | 0.0000000 | 1 | ok |
| small-ugly | 8 | 1 | 4.913 | 0.0078125 | 2 | ok |
| ugly-man-sodaDrinker | 5 | 0 | 3.147 | 30.80078125 | 6 | ok |
| ugly-man-sodaDrinker | 5 | 1 | 7.736 | 1.69140625 | 2 | ok |
| ugly-man-sodaDrinker | 10 | 0 | 2.522 | 0.0000000 | 6 | ok |
| ugly-man-sodaDrinker | 10 | 1 | 5.922 | 0.00390625 | 2 | ok |
| ugly-man-sodaDrinker | 20 | 0 | 2.184 | 0.0000000 | 2 | ok |
| ugly-man-sodaDrinker | 20 | 1 | 3.840 | 0.0234375 | 2 | ok |

Runtime variation: very-small-ugly ranged from 2.116 to 12.619 seconds (10.503-second range); small-ugly ranged from 2.181 to 12.254 seconds (10.073-second range); ugly-man-sodaDrinker ranged from 2.184 to 7.736 seconds (5.552-second range).

## Reference runs

| Dataset | Reference config | Runtime (s) | Patterns | Status |
|---|---|---:|---:|---|
| very-small-ugly | min_support=1, depth=0 | 2.470 | 18 | ok |
| small-ugly | min_support=1, depth=0 | 2.860 | 32 | ok |
| ugly-man-sodaDrinker | min_support=1, depth=0 | 2.583 | 86 | ok |

The reference pattern sets are the pattern-identity sets used for recall comparison.
