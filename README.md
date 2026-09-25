# AnchorSlice

**Anchor-guided static slicing for token-efficient smart contract vulnerability detection.**

AnchorSlice is a purely lexical pre-processing stage that shrinks a Solidity contract to the
fragments that could host each [DASP Top 10](https://dasp.co) vulnerability category *before* the
source reaches a detector. Regular expressions and brace matching decide what survives, so the
filter itself costs no model calls:

1. strip comments and blank lines
2. collapse unmodified library code (SafeMath, IERC20, Ownable, …) to one-line stubs
3. match per-category anchor regexes line by line
4. expand each hit to its innermost enclosing brace block (capped), merge overlaps, and tag each
   block with the categories whose anchors fired
5. rescue pass and guards: a category with no block but an anchor inside collapsed boilerplate gets
   a small window; minified, legacy-style or very small contracts are sent whole

## Headline result

200 contracts, 1,600 label cells, 463 labelled vulnerabilities, Claude Opus 5, one call per
contract. Three arms separate what each component of AnchorSlice contributes. **Arm A** is ordinary
practice: the complete contract with a one-line instruction per category. **Arm B** keeps the
complete contract but replaces that instruction with the anchor-derived decision rules. **Arm C** is
AnchorSlice: the slice and the decision rules together.

| | A · complete source, one-line instruction | B · complete source, decision rules | C · AnchorSlice | C vs B |
|---|---|---|---|---|
| Tokens | 2,092,914 | 2,470,113 | 937,754 | **−62.0%** |
| Cost | $17.75 | $17.52 | $6.45 | **−63.2%** |
| Wall clock | 4,151 s | 5,363 s | 1,673 s | **−68.8%** |
| F1 vs DIVE labels | 0.342 | 0.695 | 0.693 | −0.002 |
| Agreement | 0.642 | 0.797 | 0.801 | +0.004 |
| Cohen's κ | 0.097 | 0.547 | 0.549 | +0.002 |
| Missed vulnerabilities | 314 | 92 | 104 | +12 |
| False positives | 259 | 233 | 214 | −19 |

The two components do different jobs, and the paired McNemar test over 1,600 cells says so. The
decision rules buy the accuracy: A → B is p ≈ 7.1 × 10⁻²⁴. The slicer buys the efficiency at no
detection cost: B → C is p = 0.57, indistinguishable, while removing 62.0% of the tokens. Against
ordinary practice the pair doubles the F1-score while spending 55.2% fewer tokens
(p ≈ 3.7 × 10⁻²⁶). On the 130 contracts that played no part in developing the method the result is
unchanged (F1 0.689). **Evidence retention is 463/463 = 1.00**, verified before any model call, at
56.5% of source characters and 7.6 ms per contract.

## Repository layout

```
dive-llm-eval/
├── slice.py                     the slicer as first published
├── slice2.py                    current slicer (tightened anchors, retention guards)
├── run_eval.py                  query the detector per contract, score against DIVE
├── select_stratified.py         sampling (--exclude keeps rounds disjoint)
├── prepare_samples.py           pair sources with DIVE labels
├── compare_ab.py, score.py, gen_tables.py     analysis
├── PROMPT.md                    exact CLI call, system prompts and JSON schema
├── selected_ids_200new.txt      200 label-balanced contracts, selected but not yet evaluated
├── data/                        DIVE labels, tool results, contract sources per round
└── results/
    ├── pilot/                   first 10-contract runs (Opus 5 vs Fable 5)
    ├── exp70/                   50 + 20 contract runs; slicing isolated under a fixed prompt
    ├── exp200/                  the 200-contract experiment reported in the paper
    └── exploration/             prompt-calibration and Sonnet runs, earlier HTML reports
```

## Requirements

- Python 3.8+ — standard library only, nothing to `pip install`.
- For `run_eval.py`: the [Claude Code](https://claude.com/claude-code) CLI, signed in. No API key is
  read by the scripts. A 200-contract arm costs roughly $6 (sliced) to $18 (complete source).

The detector call is hermetic: `--tools ""` disables all tool access and `--json-schema` forces a
validated label vector, so the model sees only the prompt. See [PROMPT.md](dive-llm-eval/PROMPT.md).

## Reproducing

All commands run from `dive-llm-eval/`.

```bash
# 1. Inspect the slicer on one contract (no model calls)
python3 slice2.py data/src50/19288.sol

# 2. The three arms of the 200-contract experiment (results already in results/exp200/final200/)
python3 run_eval.py --samples results/exp200/samples_200.json \
    --out armA.json --model opus --prompt brief --resume
python3 run_eval.py --samples results/exp200/samples_200.json \
    --out armB.json --model opus --prompt calibrated5 --resume
python3 run_eval.py --samples results/exp200/samples_200.json \
    --out armC.json --model opus --prompt calibrated5 --slice --slicer slice2 --resume

# 3. Compare any pair of arms
python3 compare_ab.py armB.json armC.json

# 4. Redraw the paper figures
python3 make_figures.py
```

`run_eval.py --resume` continues an interrupted run without repeating completed contracts.

## Data

Contract sources and labels are a subset of **DIVE**, redistributed for reproducibility. DIVE labels
are the consensus of six static analyzers (MAIAN, Mythril, Semgrep, Slither, Solhint, VeriSmart)
mapped to DASP categories 1–8, so they are a tool consensus rather than audited ground truth. Use of
the data is governed by the [Zenodo record](https://doi.org/10.5281/zenodo.18519253); please cite:

> S. J. Alsunaidi, H. Aljamaan, and M. Hammoudeh, "DIVE: A multi-label smart contract vulnerability
> dataset," *Scientific Data*, vol. 13, art. 664, 2026.

`data/DIVE_Raw_Data.zip` (547 MB) is the upstream archive and is git-ignored; re-download it from the
Zenodo record to extract further contracts.

## Authors

Sajad Aghanasiri, Sina Zaker, Alireza Shameli-Sendi — Faculty of Computer Science and Engineering,
Shahid Beheshti University, Tehran, Iran.

## License

Code is released under the [Apache License 2.0](LICENSE). The DIVE data under `dive-llm-eval/data/`
remains under its original license.
