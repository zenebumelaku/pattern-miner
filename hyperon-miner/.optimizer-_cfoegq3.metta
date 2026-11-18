!(import! &self experiments/utils/common-utils)
!(import! &self experiments/utils/index_to_var)
!(import! &self experiments/utils/constants)
!(import! &self experiments/utils/TruthValue)
!(import! &self experiments/utils/sort)
!(import! &self experiments/utils/variable-combinations)
!(import! &self experiments/utils/remove_useless_clauses)
!(import! &self experiments/utils/surp-utils/blk-abstractness)
!(import! &self experiments/frequent-pattern-miner/valuation)
!(import! &self experiments/frequent-pattern-miner/shallow-abstractions)
!(import! &self experiments/frequent-pattern-miner/specialization)
!(import! &self experiments/frequent-pattern-miner/candidate)
!(import! &self experiments/frequent-pattern-miner/conjunction-expansion)
!(import! &self experiments/frequent-pattern-miner/frequent-pattern-miner-generic)
!(import! &self experiments/pattern-miner/pattern-miner)
;; This is a starter script to run the pattern miner on your own data.
;;
;; USAGE:
;; 1. Ensure PeTTa is installed.
;; 2. Edit the dataset import below to point to your data.
;; 3. Run this file using the PeTTa run script: sh <path-to-petta>/run.sh run_miner.metta

;; --- 1. Import Dependencies (Do not edit unless you know what you are doing) ---
;; Basic Utilities

;; Mathematical & Statistical Utilities

;; Truth Values & Probability Logic

;; Surprisingness Modules

;; Frequent Pattern Miner Components

;; Main Miner Entry Point


;; --- 2. Load Your Dataset ---
;; Replace the path below with your own data file
!(import! &db /Users/zeni/Desktop/projects/pattern/hyperon-miner/experiments/data/very-small-ugly.metta)

;; Create a space for results
!(bind! &res (new-space))


;; --- 3. Run Miner ---
;; The miner function takes 9 arguments:
;; (pattern-miner <output-space> <input-db> <init-pattern> <min-support> <depth> <mode> <normalization> <db-ratio> <conj-exp>)
;;
;; PARAMETERS EXPLAINED:
;; ---------------------
;; 1. <output-space>:  (&res) The place where results will be stored.
;; 2. <input-db>:      (&db) The dataset you imported above.
;; 3. <init-pattern>:  ($x) The initial pattern used by the frequent miner.
;; 4. <min-support>:   (Integer) The minimum number of times a pattern must occur to be considered "frequent".
;;                     Example: 10 means the pattern must appear at least 10 times.
;; 5. <depth>:         (Integer) Controls how complex the mined patterns are.
;;                     0 -> Standard Pairs/Triplets (e.g., A implies B). Result usually has 2 conjuncts.
;;                     1 -> Basic Chain (e.g., A implies B, B implies C). Result has 3 conjuncts.
;; 6. <mode>:          (Atom) What to calculate?
;;                     none      -> Only find frequent patterns. Do not calculate Surprisingness.
;;                     isurp     -> Calculate information-theoretic surprisingness.
;;                     isurp-old -> Use the legacy surprisingness algorithm.
;;                     jsd       -> Use Jensen-Shannon Divergence for surprisingness.
;; 7. <normalization>: (Boolean/Atom) Normalize surprisingness scores?
;;                     True  -> Scale scores between 0 and 1. (Recommended for 'isurp')
;;                     False -> raw scores.
;;                     none  -> Use this if <mode> is 'none'.
;; 8. <db-ratio>:      (Number/Atom) Ratio of relevant samples to total DB size.
;;                     Used to adjust probability estimates.
;;                     0.2   -> A typical starting value (20% sample assumption).
;;                     none  -> Use this if <mode> is 'none'.
;; 9. <conj-exp>:      (Boolean) Enable Conjunction Expansion?
;;                     True  -> Allows combining smaller patterns into larger ones (required for depth > 0).
;;                     False -> Stick to basic specialized patterns.

;; EXAMPLE CONFIGURATION:
!(pattern-miner &res &db $x 1 0 none none none False)


;; --- 4. View Results ---
!(println! "OPTIMIZER_RESULTS_BEGIN")
!(get-atoms &res)
!(println! "OPTIMIZER_RESULTS_END")

