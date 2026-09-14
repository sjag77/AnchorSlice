# AnchorSlice

**Anchor-guided static slicing for token-efficient smart contract vulnerability detection with large language models.**

AnchorSlice is a purely lexical pre-processing stage that shrinks a Solidity contract to the
fragments that could host each [DASP Top 10](https://dasp.co) vulnerability category *before* the
source is shown to an LLM. Regular expressions and brace matching decide what survives, so the
filter itself costs no model calls:

1. strip comments and blank lines
2. collapse unmodified library code (SafeMath, IERC20, Ownable, …) to one-line stubs
3. match per-category anchor regexes line by line
4. expand each hit to its innermost enclosing brace block (capped), merge overlaps, and tag each
   block with the categories whose anchors fired
5. rescue pass: a category with no block but an anchor inside collapsed boilerplate gets a small window

The repository holds the slicer, the evaluation harness that queries Claude through the Claude
Code CLI, every raw result file, and the source of the accompanying IEEE-format manuscript.

## Headline result

Paired A/B on 50 contracts from the [DIVE dataset](https://doi.org/10.5281/zenodo.18519253)
(400 label cells, 119 positives), Claude Opus 5 at `effort=high`, same prompt and schema in both arms.

| Metric | Arm A: full source | Arm B: AnchorSlice | Change |
|---|---|---|---|
| Total tokens | 913,958 | 396,438 | **−56.6 %** |
| Wall clock | 1,019.6 s | 818.5 s | −19.7 % |
| Cost | $3.41 | $3.36 | −1.4 % |
| Recall | 47.9 % | 63.0 % | +15.1 pp |
| Precision | 38.5 % | 41.4 % | +2.9 pp |
| F1 | 42.7 % | 50.0 % | +7.3 pp |
| Cohen's κ | 0.145 | 0.220 | +0.075 |
| Label agreement | 61.8 % | 62.5 % | +0.7 pp |
| Exact match (8/8) | 0 / 50 | 2 / 50 | +2 |

The slicer keeps 60.2 % of source characters and retains evidence for all 119 labelled category
instances. Caveats, discussed in the manuscript: the quality gains are **not statistically
significant** (McNemar exact p = 0.761), the anchors were tuned on the same 50 contracts, each arm
was run once, and the DoS anchor is over-broad (DoS agreement fell 14 pp).

## Repository layout

```
AnchorSlice_manuscript.pages     manuscript (Apple Pages)
dive-llm-eval/
├── slice.py                     AnchorSlice itself (stdlib only)
├── select_stratified.py         seeded, stratified 50-contract sample  -> selected_ids_50.txt
├── select_contracts.py          5-contract set-cover smoke-test set    -> selected_ids.txt
├── prepare_samples.py           pair source with DIVE labels           -> samples*.json
├── run_eval.py                  query Claude per contract, score vs DIVE -> results*.json
├── compare_ab.py                paired A/B report of two result files
├── score.py                     score the six analyzers and each LLM run against DIVE
├── gen_tables.py                emit HTML table fragments for the reports
├── PROMPT.md                    exact CLI call, system prompts, and JSON schema
├── data/
│   ├── Labels/                  DIVE_Labels.csv, Tool_Results.csv
│   ├── sol_index.tsv            per-contract source size for all 22,330 contracts
│   ├── src50/                   sources for the 50-contract A/B sample
│   ├── cover_src/               sources for the 5-contract set-cover sample
│   └── Source codes/            sources for contracts 1–15
├── results_50_calibrated.json   Arm A (full source)      + run50_calibrated.log
├── results_50_sliced.json       Arm B (AnchorSlice)      + run50_sliced.log
├── results_cover_*.json         prompt variants (brief / examples / calibrated) on the 5-contract set
├── results.json, results_fable.json   early pilot: Opus 5 vs Fable 5 on contracts 1–10
├── sliced_50.json               slice.py output for the 50-contract sample
├── ab_report.html, report.html, technical_report.html, DIVE_static_slicing_report.pdf
└── paper/                       build_paper.py / emit_docx.py -> AnchorSlice_manuscript.{rtf,docx}
```

`dive-llm-eval/README.md` documents the earlier pilot study (first 10 contracts, Opus 5 vs Fable 5).

## Requirements

- Python 3.8+ — every script uses only the standard library, so there is nothing to `pip install`.
- For `run_eval.py` only: the [Claude Code](https://claude.com/claude-code) CLI (`claude`),
  signed in. No API key is read by the scripts. Each 50-contract run costs roughly $3.40.

The model call is hermetic: `--tools ""` disables all tool access and `--json-schema` forces a
validated label vector back, so the model sees only the prompt. See [PROMPT.md](dive-llm-eval/PROMPT.md).

## Reproducing

All commands run from `dive-llm-eval/`.

```bash
# 1. Check the slicer: per-category recall and size reduction on data/src50
python3 slice.py --self-check
python3 slice.py data/src50/19288.sol          # view one sliced contract

# 2. Build the sample (the committed selected_ids_50.txt / samples_50.json are already the ones used)
python3 select_stratified.py -n 50 --seed 20260827
DIVE_SOURCE_DIR=data/src50 python3 prepare_samples.py --data-dir data \
    --ids-file selected_ids_50.txt --out samples_50.json

# 3. Run both arms (calls Claude; ~15–17 min and ~$3.40 each). --resume continues an interrupted run.
python3 run_eval.py --samples samples_50.json --out results_50_calibrated.json --prompt calibrated
python3 run_eval.py --samples samples_50.json --out results_50_sliced.json    --prompt calibrated --slice

# 4. Analyse
python3 compare_ab.py results_50_calibrated.json results_50_sliced.json
python3 score.py --ids selected_ids_50.txt results_50_calibrated.json:full results_50_sliced.json:sliced
python3 gen_tables.py --ids selected_ids_50.txt --runs results_50_sliced.json:sliced --percat sliced

# 5. Rebuild the manuscript
cd paper && python3 build_paper.py && python3 emit_docx.py
```

Step 4 needs no model access and reproduces every number above from the committed result files.
`DIVE_SOURCE_DIR` is required in step 2 because `prepare_samples.py` otherwise picks up
`data/Source codes/`, which only holds contracts 1–15.

## Data

Contract sources and labels are a subset of **DIVE**, redistributed here for reproducibility. DIVE
labels are the union of six static analyzers (MAIAN, Mythril, Semgrep, Slither, Solhint, VeriSmart)
mapped to DASP categories 1–8, so they are a tool consensus rather than audited ground truth.
Use of the data is governed by the license of the
[Zenodo record](https://doi.org/10.5281/zenodo.18519253); please cite:

> S. J. Alsunaidi, H. Aljamaan, and M. Hammoudeh, "DIVE: A multi-label smart contract vulnerability
> dataset," *Scientific Data*, vol. 13, art. 664, 2026.

To fetch the full dataset, see [dive-llm-eval/README.md](dive-llm-eval/README.md#getting-the-data).

## Authors

Sajad Aghanasiri, Sina Zaker, Alireza Shameli-Sendi — Faculty of Computer Science and Engineering,
Shahid Beheshti University, Tehran, Iran.

## License

Code is released under the [Apache License 2.0](LICENSE). The DIVE data under `dive-llm-eval/data/`
remains under its original license.
