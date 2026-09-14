# DIVE vs. Claude Opus 5 — label assessment harness

> **Pilot study notes.** This file documents the first 10-contract run (Opus 5 vs Fable 5).
> For AnchorSlice, the 50-contract A/B evaluation, and reproduction steps, see the
> [top-level README](../README.md).

Assesses the ground-truth vulnerability labels in the
[DIVE dataset](https://doi.org/10.5281/zenodo.18519253) against an independent
LLM auditor (Claude Opus 5), driven through the Claude Code CLI in headless mode.

DIVE's labels are the **union of six static analyzers** (MAIAN, Mythril, Semgrep,
Slither, Solhint, VeriSmart) via the MultiTagging framework, mapped onto DASP
Top-10 categories 1–8. This harness asks whether a strong LLM, reading only the
Solidity source, arrives at the same verdicts — and where it doesn't, which tool
drove the difference.

## Layout

| File | Purpose |
|---|---|
| `prepare_samples.py` | Pairs the first *N* contracts' `.sol` source with their `DIVE_Labels.csv` row → `samples.json` |
| `run_eval.py` | Runs each contract past Opus 5, scores agreement, reports time + tokens → `results.json` |
| `data/Labels/` | `DIVE_Labels.csv`, `Tool_Results.csv` from the Zenodo record |
| `data/Source codes/` | Per-contract `<contractID>.sol`, from `DIVE_Raw_Data.zip` → `Raw/PRE/Source codes/` |

## Getting the data

```bash
BASE=https://zenodo.org/api/records/18519253/files
curl -L -o DIVE_Labels.zip   "$BASE/DIVE_Labels.zip/content"      # 254 KB
curl -L -o DIVE_Raw_Data.zip "$BASE/DIVE_Raw_Data.zip/content"    # 547 MB

unzip -q DIVE_Labels.zip -d data
# extract only the source files you need — the archive also holds ~4 GB of opcode JSONL
for i in $(seq 1 10); do
  unzip -oqj DIVE_Raw_Data.zip "Raw/PRE/Source codes/$i.sol" -d "data/Source codes"
done
```

## Running

```bash
python3 prepare_samples.py --data-dir data -n 10
python3 run_eval.py --samples samples.json --out results.json --model opus --effort high
```

The model call is deliberately hermetic: `--tools ""` disables all tool access, so
Opus sees nothing but the contract source in its prompt — it cannot look the answer
up or read the labels off disk. `--json-schema` forces a validated label vector back,
so there is no output parsing to get wrong.

Requires the `claude` CLI, authenticated (`claude` handles auth; no API key needed).

## What it reports

Per contract: wall-clock seconds, the CLI's `duration_ms` / `duration_api_ms`,
input / output / cache-write / cache-read tokens, and cost. Summed into a totals
block, alongside per-DASP-category agreement, precision/recall/F1 measured
*against DIVE* (not against truth — neither side is ground truth here), and
Cohen's κ for chance-corrected agreement.

## Result of the first-10 run

Opus 5 at `effort=high`, 10 contracts, 224.7 s wall (22.5 s/contract),
137,362 tokens, $0.92.

Overall label agreement **76.3 %** (61/80 cells), but **0/10** contracts matched on
all eight categories. The disagreement is not noise — it is systematic:

| Category | DIVE + | Opus + | κ |
|---|---|---|---|
| Reentrancy | 5 | 0 | 0.00 |
| DoS | 8 | 0 | 0.00 |
| Access Control | 3 | 1 | 0.41 |
| Arithmetic | 2 | 1 | 0.62 |
| Unchecked Return Values | 3 | 2 | 0.74 |
| Front Running | 1 | 3 | 0.41 |
| Time manipulation | 1 | 1 | 1.00 |
| Bad Randomness | 0 | 0 | n/a |

**Every** DIVE-positive / Opus-negative cell traces to Slither, Solhint, or Mythril
firing (see `Tool_Results.csv` provenance in the analysis). Contract 9 is the clean
illustration: DIVE marks it Reentrancy=1, but its `transfer()` updates both balances
*before* the external `tokenFallback` call and only emits an event afterward —
textbook checks-effects-interactions. That is Slither's informational-severity
`reentrancy-events` detector, not an exploitable reentrancy.

In the other direction, Opus flagged the ERC-20 `approve()` allowance race as Front
Running on contracts 6 and 9, where no tool in the suite fires at all.

## Second run: Fable 5 (`results_fable.json`)

Same 10 contracts, same prompt and schema, `--model fable --effort high`.

| Metric | Opus 5 | Fable 5 |
|---|---|---|
| Label agreement vs DIVE | **0.7625** | 0.7250 |
| Hamming loss | 0.2375 | 0.2750 |
| Exact match 8/8 | 0/10 | 0/10 |
| Wall clock | 224.7 s | 528.9 s |
| Per contract | 22.5 s | 52.9 s |
| Total tokens | 137,362 | 140,345 |
| Output tokens | 13,184 | 16,741 |
| Cost | $0.92 | $2.01 |

Fable 5 cost 2.2× more and took 2.4× longer for *slightly lower* agreement with DIVE.
Its wall-clock total is skewed by one outlier — contract 5 took 307 s while emitting
only 1,373 output tokens, i.e. a stalled call, not deep reasoning. Excluding it,
Fable averages ~25 s/contract, close to Opus.

### The result that matters: the two models agree with each other, not with DIVE

| Comparison | Agreement |
|---|---|
| Opus 5 vs DIVE | 0.762 |
| Fable 5 vs DIVE | 0.725 |
| **Opus 5 vs Fable 5** | **0.963** |

Two independently-run frontier models converge on 77/80 label cells while agreeing
with DIVE on only ~58–61. Both flagged **zero** Reentrancy and **zero** DoS across all
ten contracts, against DIVE's 5 and 8. That rules out model-specific unreliability as
the explanation: the divergence is a property of DIVE's labeling process — the union
of six analyzers with no severity filter — not of the auditor reading the code.

All three cells where the models split are near-misses on the hardest contracts,
and in each Opus matched DIVE while Fable did not:

| Contract | Category | DIVE | Opus | Fable |
|---|---|---|---|---|
| 6 | Access Control | 1 | 1 | 0 |
| 6 | Time manipulation | 1 | 1 | 0 |
| 10 | Front Running | 1 | 1 | 0 |

Fable is the more conservative labeler overall (6 positives across 80 cells vs Opus's 8).

### Caveat on the sample

The first 10 contracts by `contractID` are **not** a representative sample. DoS is
positive in 8/10 of them versus **16.9 %** dataset-wide; Access Control is 3/10
versus **74.9 %** dataset-wide. Treat the per-category numbers above as an
illustration of *where* DIVE and an LLM diverge, not as an estimate of how often.
For a prevalence-valid estimate, sample randomly and use a few hundred contracts.

### Dataset-wide label prevalence (all 22,330 contracts)

| Category | Positives | Rate |
|---|---|---|
| Access Control | 16,723 | 74.9 % |
| Reentrancy | 11,400 | 51.1 % |
| Arithmetic | 9,542 | 42.7 % |
| Time manipulation | 6,322 | 28.3 % |
| Unchecked Return Values | 5,911 | 26.5 % |
| DoS | 3,781 | 16.9 % |
| Bad Randomness | 634 | 2.8 % |
| Front Running | 606 | 2.7 % |

Mean 2.46 labels per contract; 2,686 contracts (12 %) carry no label at all.
