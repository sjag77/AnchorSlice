#!/usr/bin/env python3
"""
Score every predictor - the six analyzers and each Opus run - against the DIVE label.

Precision, recall and F1 are computed against DIVE as the reference. For the six tools
that is circular by construction (DIVE's label is derived from their output), so their
precision is reported but should not be read as accuracy. Only the Opus columns are
scored against a reference they had no hand in creating.

Blank cells in Tool_Results.csv mean the tool did not run; they are excluded from that
tool's TP/FP/FN rather than counted as negatives. Recall is reported two ways: over the
cells the tool actually ran, and over every DIVE-positive cell in the sample.

Usage:
    python3 score.py --ids selected_ids_50.txt results_50_examples.json:examples \
        results_50_calibrated.json:calibrated
"""

import argparse
import csv
import json
import sys

csv.field_size_limit(sys.maxsize)

DASP = [
    "Reentrancy", "Access Control", "Arithmetic", "Unchecked Return Values",
    "DoS", "Bad Randomness", "Front Running", "Time manipulation",
]
TOOLS = ["MAIAN", "Mythril", "Semgrep", "Slither", "Solhint", "VeriSmart"]


def prf(tp, fp, fn, n_pos):
    p = tp / (tp + fp) if tp + fp else None
    r_ran = tp / (tp + fn) if tp + fn else None
    r_all = tp / n_pos if n_pos else None
    f1 = 2 * p * r_all / (p + r_all) if p and r_all else 0.0
    return p, r_ran, r_all, f1


def fmt(x, w=8, nd=3):
    return f"{'n/a':>{w}}" if x is None else f"{x:>{w}.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="results.json:label pairs")
    ap.add_argument("--ids", default="selected_ids_50.txt")
    ap.add_argument("--tools-csv", default="data/Labels/Tool_Results.csv")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    ids = [l.strip() for l in open(args.ids) if l.strip()]
    tr = {r["contractID"]: r for r in csv.DictReader(open(args.tools_csv))}

    runs = {}
    for spec in args.runs:
        path, _, label = spec.partition(":")
        runs[label or path] = {r["contractID"]: r
                               for r in json.load(open(path))["records"] if "prediction" in r}

    gt = {(cid, c): int(next(iter(runs.values()))[cid]["ground_truth"][c])
          for cid in ids for c in DASP}
    n_pos = sum(gt.values())
    n_cells = len(ids) * len(DASP)

    print(f"contracts: {len(ids)}   label cells: {n_cells}   "
          f"DIVE-positive: {n_pos} ({n_pos/n_cells:.1%})\n")

    rows = []
    for t in TOOLS:
        tp = fp = fn = ran = 0
        for cid in ids:
            for i, c in enumerate(DASP, 1):
                v = tr[cid].get(f"{t}_{i}")
                if v in (None, ""):
                    continue
                ran += 1
                v, g = int(v), gt[(cid, c)]
                tp += g == 1 and v == 1
                fp += g == 0 and v == 1
                fn += g == 1 and v == 0
        rows.append((t, "tool", ran, tp, fp, fn) + prf(tp, fp, fn, n_pos))

    for label, R in runs.items():
        tp = fp = fn = 0
        for cid in ids:
            for c in DASP:
                v, g = int(R[cid]["prediction"][c]), gt[(cid, c)]
                tp += g == 1 and v == 1
                fp += g == 0 and v == 1
                fn += g == 1 and v == 0
        rows.append((f"Opus·{label}", "llm", n_cells, tp, fp, fn) + prf(tp, fp, fn, n_pos))

    hdr = (f"{'predictor':<18}{'ran':>6}{'TP':>5}{'FP':>5}{'FN':>5}"
           f"{'prec':>8}{'rec(ran)':>10}{'rec(all)':>10}{'F1':>8}")
    print(hdr)
    print("-" * len(hdr))
    for name, kind, ran, tp, fp, fn, p, rr, ra, f1 in rows:
        mark = " *" if kind == "tool" else ""
        print(f"{name:<18}{ran:>6}{tp:>5}{fp:>5}{fn:>5}"
              f"{fmt(p)}{fmt(rr,10)}{fmt(ra,10)}{f1:>8.3f}{mark}")
    print("\n* precision/F1 circular: DIVE's label is derived from these tools.")

    # agreement + per-category for the LLM runs
    for label, R in runs.items():
        agree = sum(1 for cid in ids for c in DASP
                    if int(R[cid]["prediction"][c]) == gt[(cid, c)])
        exact = sum(1 for cid in ids
                    if all(int(R[cid]["prediction"][c]) == gt[(cid, c)] for c in DASP))
        print(f"\n=== Opus·{label} ===")
        print(f"agreement {agree}/{n_cells} = {agree/n_cells:.3f}   exact 8/8: {exact}/{len(ids)}")
        print(f"{'category':<24}{'DIVE+':>7}{'LLM+':>6}{'TP':>4}{'FP':>4}{'FN':>4}{'prec':>8}{'rec':>7}{'F1':>7}")
        for c in DASP:
            tp = sum(1 for cid in ids if gt[(cid, c)] == 1 and int(R[cid]["prediction"][c]) == 1)
            fp = sum(1 for cid in ids if gt[(cid, c)] == 0 and int(R[cid]["prediction"][c]) == 1)
            fn = sum(1 for cid in ids if gt[(cid, c)] == 1 and int(R[cid]["prediction"][c]) == 0)
            p, _, r, f1 = prf(tp, fp, fn, tp + fn)
            print(f"{c:<24}{tp+fn:>7}{tp+fp:>6}{tp:>4}{fp:>4}{fn:>4}{fmt(p)}{fmt(r,7,2)}{f1:>7.2f}")

    if args.json_out:
        json.dump({"rows": [dict(zip(
            ["name", "kind", "ran", "tp", "fp", "fn", "precision", "recall_ran",
             "recall_all", "f1"], r)) for r in rows],
            "n_pos": n_pos, "n_cells": n_cells}, open(args.json_out, "w"), indent=2)


if __name__ == "__main__":
    main()
