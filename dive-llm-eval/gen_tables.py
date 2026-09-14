#!/usr/bin/env python3
"""
Emit the report's data-dependent table bodies as HTML fragments.

Every number on the page comes from here rather than being typed by hand, so the
figures cannot drift from the JSON they claim to summarise.

Writes three fragments to --outdir:
    frag_sample.html     sample composition, per category
    frag_predictors.html six analyzers + each Opus run, scored against DIVE
    frag_percat.html     per-category breakdown for one Opus run

Usage:
    python3 gen_tables.py --ids selected_ids_50.txt \
        --runs results_50_calibrated.json:calibrated --percat calibrated
"""

import argparse
import csv
import json
import os
import sys

csv.field_size_limit(sys.maxsize)

DASP = ["Reentrancy", "Access Control", "Arithmetic", "Unchecked Return Values",
        "DoS", "Bad Randomness", "Front Running", "Time manipulation"]
TOOLS = ["MAIAN", "Mythril", "Semgrep", "Slither", "Solhint", "VeriSmart"]

# dataset-wide prevalence, all 22,330 contracts
FULL_RATE = {"Reentrancy": .511, "Access Control": .749, "Arithmetic": .427,
             "Unchecked Return Values": .265, "DoS": .169, "Bad Randomness": .028,
             "Front Running": .027, "Time manipulation": .283}

NOTE = {
    "MAIAN": "barely ran; no positives",
    "Mythril": "full coverage — the only tool comparable cell-for-cell",
    "Semgrep": "near-silent",
    "Slither": "partial coverage",
    "Solhint": "a style linter, not a security analyzer",
    "VeriSmart": "barely ran; no positives",
}


def prf(tp, fp, fn, n_pos):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / n_pos if n_pos else None
    f1 = 2 * p * r / (p + r) if p and r else 0.0
    return p, r, f1


def cell(v, nd=3, cls=""):
    txt = "n/a" if v is None else f"{v:.{nd}f}"
    c = cls or ("nr" if v is None else "")
    return f'<td class="num-col {c}">{txt}</td>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="selected_ids_50.txt")
    ap.add_argument("--runs", nargs="+", required=True, help="results.json:label")
    ap.add_argument("--percat", help="which run label to break down per category")
    ap.add_argument("--tools-csv", default="data/Labels/Tool_Results.csv")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    ids = [l.strip() for l in open(args.ids) if l.strip()]
    tr = {r["contractID"]: r for r in csv.DictReader(open(args.tools_csv))}
    runs = {}
    for spec in args.runs:
        path, _, label = spec.partition(":")
        runs[label or path] = {r["contractID"]: r for r in
                               json.load(open(path))["records"] if "prediction" in r}

    first = next(iter(runs.values()))
    gt = {(cid, c): int(first[cid]["ground_truth"][c]) for cid in ids for c in DASP}
    n_pos = sum(gt.values())
    n_cells = len(ids) * len(DASP)

    # ---- fragment 1: sample composition ----
    out = []
    for c in DASP:
        p = sum(gt[(cid, c)] for cid in ids)
        out.append(f'        <tr><td class="name">{c}</td>'
                   f'<td class="num-col">{p}</td><td class="num-col">{len(ids)-p}</td>'
                   f'<td class="num-col">{p/len(ids):.0%}</td>'
                   f'<td class="num-col dim">{FULL_RATE[c]:.1%}</td></tr>')
    out.append(f'        <tr class="total"><td class="name">All eight</td>'
               f'<td class="num-col">{n_pos}</td><td class="num-col">{n_cells-n_pos}</td>'
               f'<td class="num-col">{n_pos/n_cells:.0%}</td>'
               f'<td class="num-col dim">30.7%</td></tr>')
    open(os.path.join(args.outdir, "frag_sample.html"), "w").write("\n".join(out))

    # ---- fragment 2: predictor comparison ----
    out, summary = [], {}
    for t in TOOLS:
        tp = fp = fn = ran = 0
        for cid in ids:
            for i, c in enumerate(DASP, 1):
                v = tr[cid].get(f"{t}_{i}")
                if v in (None, ""):
                    continue
                ran += 1
                v = int(v)
                g = gt[(cid, c)]
                tp += g == 1 and v == 1
                fp += g == 0 and v == 1
                fn += g == 1 and v == 0
        p, r, f1 = prf(tp, fp, fn, n_pos)
        summary[t] = (tp, fp, fn, p, r, f1)
        out.append(
            f'        <tr><td>{t}</td><td class="num-col">{ran}</td>'
            f'<td class="num-col dim">{n_cells-ran}</td>'
            f'<td class="num-col">{tp}</td><td class="num-col">{fp}</td><td class="num-col">{fn}</td>'
            f'{cell(p, 3, "circ")}{cell(r)}{cell(f1, 3, "circ")}'
            f'<td class="name dim">{NOTE[t]}</td></tr>')
    for label, R in runs.items():
        tp = fp = fn = 0
        for cid in ids:
            for c in DASP:
                v, g = int(R[cid]["prediction"][c]), gt[(cid, c)]
                tp += g == 1 and v == 1
                fp += g == 0 and v == 1
                fn += g == 1 and v == 0
        p, r, f1 = prf(tp, fp, fn, n_pos)
        summary[f"Opus·{label}"] = (tp, fp, fn, p, r, f1)
        out.append(
            f'        <tr class="total"><td>Opus 5 · {label}</td>'
            f'<td class="num-col">{n_cells}</td><td class="num-col dim">0</td>'
            f'<td class="num-col">{tp}</td><td class="num-col">{fp}</td><td class="num-col">{fn}</td>'
            f'{cell(p)}{cell(r)}{cell(f1)}'
            f'<td class="name dim">source only, no tools</td></tr>')
    open(os.path.join(args.outdir, "frag_predictors.html"), "w").write("\n".join(out))

    # ---- fragment 3: per-category for one run ----
    if args.percat:
        R = runs[args.percat]
        out = []
        for c in DASP:
            tp = sum(1 for cid in ids if gt[(cid, c)] == 1 and int(R[cid]["prediction"][c]) == 1)
            fp = sum(1 for cid in ids if gt[(cid, c)] == 0 and int(R[cid]["prediction"][c]) == 1)
            fn = sum(1 for cid in ids if gt[(cid, c)] == 1 and int(R[cid]["prediction"][c]) == 0)
            p, r, f1 = prf(tp, fp, fn, tp + fn)
            out.append(f'        <tr><td class="name">{c}</td>'
                       f'<td class="num-col">{tp+fn}</td><td class="num-col">{tp+fp}</td>'
                       f'<td class="num-col">{tp}</td><td class="num-col">{fp}</td>'
                       f'<td class="num-col">{fn}</td>'
                       f'{cell(p, 2)}{cell(r, 2)}{cell(f1, 2)}</tr>')
        open(os.path.join(args.outdir, "frag_percat.html"), "w").write("\n".join(out))

    print(f"contracts {len(ids)}  cells {n_cells}  DIVE-positive {n_pos} ({n_pos/n_cells:.1%})\n")
    print(f"{'predictor':<20}{'TP':>5}{'FP':>5}{'FN':>5}{'prec':>8}{'rec':>8}{'F1':>8}")
    for k, (tp, fp, fn, p, r, f1) in summary.items():
        ps = f"{p:.3f}" if p is not None else "n/a"
        print(f"{k:<20}{tp:>5}{fp:>5}{fn:>5}{ps:>8}{r:>8.3f}{f1:>8.3f}")
    print("\nfragments written to", args.outdir)


if __name__ == "__main__":
    main()
