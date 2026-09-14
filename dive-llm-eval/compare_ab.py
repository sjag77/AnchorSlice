#!/usr/bin/env python3
"""A/B comparison of two run_eval.py result files (baseline vs sliced)."""
import argparse, json, math

DASP = ["Reentrancy", "Access Control", "Arithmetic", "Unchecked Return Values",
        "DoS", "Bad Randomness", "Front Running", "Time manipulation"]

def kappa(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    if not n: return 0.0
    po = (tp + tn) / n
    pe = ((tp+fp)*(tp+fn) + (fn+tn)*(fp+tn)) / (n*n)
    return 0.0 if pe == 1 else (po - pe) / (1 - pe)

def cells(recs):
    """per-category (tp, fp, fn, tn) over the record set"""
    out = {c: [0,0,0,0] for c in DASP}
    for r in recs:
        for c in DASP:
            g, p = r["ground_truth"][c], r["prediction"][c]
            out[c][0 if (g and p) else 1 if (p and not g) else 2 if (g and not p) else 3] += 1
    return out

def metrics(recs):
    cl = cells(recs)
    tp = sum(v[0] for v in cl.values()); fp = sum(v[1] for v in cl.values())
    fn = sum(v[2] for v in cl.values()); tn = sum(v[3] for v in cl.values())
    n = tp+fp+fn+tn
    prec = tp/(tp+fp) if tp+fp else 0.0
    rec  = tp/(tp+fn) if tp+fn else 0.0
    return {
        "cells": cl, "n": n,
        "agreement": (tp+tn)/n,
        "hamming": (fp+fn)/n,
        "exact": sum(1 for r in recs if r["agreement"] == 8) / len(recs),
        "precision": prec, "recall": rec,
        "f1": 2*prec*rec/(prec+rec) if prec+rec else 0.0,
        "kappa": kappa(tp, fp, fn, tn),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "mean_agree": sum(r["agreement"] for r in recs)/len(recs),
    }

def d(a, b, pct=False, pp=False, inv=False):
    """format a delta, marking improvement"""
    x = b - a
    good = (x < 0) if inv else (x > 0)
    mark = "" if abs(x) < 1e-9 else (" +" if good else " -")
    s = f"{x*100:+.1f} pp" if pp else (f"{x:+.1%}" if pct else f"{x:+.4f}")
    return f"{s}{mark}"

def load(p):
    j = json.load(open(p))
    ids = {r["contractID"] for r in j["records"]}
    return j, j["records"], ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline"); ap.add_argument("sliced")
    a = ap.parse_args()
    A, ra, ia = load(a.baseline)
    B, rb, ib = load(a.sliced)
    common = ia & ib
    if len(common) < max(len(ia), len(ib)):
        print(f"! restricting to {len(common)} contracts present in both "
              f"({len(ia)} baseline, {len(ib)} sliced)\n")
    ra = [r for r in ra if r["contractID"] in common]
    rb = [r for r in rb if r["contractID"] in common]
    ra.sort(key=lambda r: r["contractID"]); rb.sort(key=lambda r: r["contractID"])
    ma, mb = metrics(ra), metrics(rb)

    W = 78
    print("=" * W)
    print(f"A/B: {a.baseline}  vs  {a.sliced}")
    print(f"     {len(common)} contracts | model {A['summary']['model']} "
          f"effort={A['summary']['effort']} prompt={A['summary']['prompt_variant']}")
    print("=" * W)

    print("\n--- ACCURACY " + "-"*(W-13))
    print(f"{'metric':<24}{'baseline':>12}{'sliced':>12}{'delta':>16}")
    rows = [("Label agreement", "agreement", True, False),
            ("Hamming loss",    "hamming",   True, True),
            ("Exact match (8/8)","exact",    True, False),
            ("Precision",       "precision", True, False),
            ("Recall",          "recall",    True, False),
            ("F1",              "f1",        True, False),
            ("Cohen's kappa",   "kappa",     False, False)]
    for name, k, pct, inv in rows:
        fa = f"{ma[k]:.1%}" if pct else f"{ma[k]:.4f}"
        fb = f"{mb[k]:.1%}" if pct else f"{mb[k]:.4f}"
        print(f"{name:<24}{fa:>12}{fb:>12}{d(ma[k], mb[k], pct=pct, inv=inv):>16}")
    print(f"{'Mean agree /8':<24}{ma['mean_agree']:>12.2f}{mb['mean_agree']:>12.2f}"
          f"{mb['mean_agree']-ma['mean_agree']:>+15.2f}")
    print(f"\n{'confusion':<24}{'TP':>7}{'FP':>7}{'FN':>7}{'TN':>7}")
    print(f"{'  baseline':<24}{ma['tp']:>7}{ma['fp']:>7}{ma['fn']:>7}{ma['tn']:>7}")
    print(f"{'  sliced':<24}{mb['tp']:>7}{mb['fp']:>7}{mb['fn']:>7}{mb['tn']:>7}")
    print(f"{'  delta':<24}{mb['tp']-ma['tp']:>+7}{mb['fp']-ma['fp']:>+7}"
          f"{mb['fn']-ma['fn']:>+7}{mb['tn']-ma['tn']:>+7}")

    print("\n--- PER CATEGORY " + "-"*(W-17))
    print(f"{'category':<24}{'DIVE+':>6}{'agree A':>9}{'agree B':>9}{'d':>7}"
          f"{'FP A':>6}{'FP B':>6}{'FN A':>6}{'FN B':>6}")
    for c in DASP:
        ca, cb = ma["cells"][c], mb["cells"][c]
        na, nb_ = sum(ca), sum(cb)
        aa, ab = (ca[0]+ca[3])/na, (cb[0]+cb[3])/nb_
        print(f"{c:<24}{ca[0]+ca[2]:>6}{aa:>9.3f}{ab:>9.3f}{(ab-aa)*100:>+6.1f}"
              f"{ca[1]:>6}{cb[1]:>6}{ca[2]:>6}{cb[2]:>6}")

    print("\n--- COST " + "-"*(W-9))
    def tk(s, key): return s["tokens"][key]
    ta, tb = A["summary"], B["summary"]
    print(f"{'metric':<24}{'baseline':>14}{'sliced':>14}{'delta':>18}")
    for name, key in [("Input tokens","input_tokens"), ("Output tokens","output_tokens"),
                      ("Cache write","cache_creation_input_tokens"),
                      ("Cache read","cache_read_input_tokens"),
                      ("TOTAL tokens","total_tokens")]:
        va, vb = tk(ta,key), tk(tb,key)
        print(f"{name:<24}{va:>14,}{vb:>14,}{f'{vb-va:+,} ({(vb-va)/va:+.1%})' if va else '':>18}")
    for name, va, vb, f in [("Cost (USD)", ta["cost_usd"], tb["cost_usd"], "${:.4f}"),
                            ("Wall clock (s)", ta["timing"]["run_wall_seconds"],
                             tb["timing"]["run_wall_seconds"], "{:.1f}")]:
        print(f"{name:<24}{f.format(va):>14}{f.format(vb):>14}"
              f"{f'{(vb-va)/va:+.1%}':>18}")
    ca_, cb_ = ta["cost_usd"]/len(ra), tb["cost_usd"]/len(rb)
    print(f"{'Cost / contract':<24}{'$'+format(ca_,'.4f'):>14}{'$'+format(cb_,'.4f'):>14}"
          f"{f'{(cb_-ca_)/ca_:+.1%}':>18}")

    print("\n--- EFFICIENCY " + "-"*(W-15))
    dt = (tb["tokens"]["total_tokens"] - ta["tokens"]["total_tokens"]) / ta["tokens"]["total_tokens"]
    da_ = mb["agreement"] - ma["agreement"]
    print(f"tokens {dt:+.1%}, agreement {da_*100:+.1f} pp")
    print(f"agreement per 100k tokens: baseline {ma['agreement']*100/(ta['tokens']['total_tokens']/1e5):.2f}"
          f"  sliced {mb['agreement']*100/(tb['tokens']['total_tokens']/1e5):.2f}")

    print("\n--- PER-CONTRACT SHIFTS " + "-"*(W-24))
    ba = {r["contractID"]: r for r in ra}
    bb = {r["contractID"]: r for r in rb}
    diff = sorted(((bb[i]["agreement"] - ba[i]["agreement"], i) for i in common),
                  reverse=True)
    better = [x for x in diff if x[0] > 0]; worse = [x for x in diff if x[0] < 0]
    print(f"improved {len(better)}  |  unchanged {len(diff)-len(better)-len(worse)}  "
          f"|  regressed {len(worse)}")
    for tag, lst in (("best", better[:5]), ("worst", worse[-5:])):
        for dv, i in lst:
            print(f"  {tag:<6} {i:>7}  {ba[i]['agreement']}/8 -> {bb[i]['agreement']}/8  ({dv:+d})")
    print("=" * W)

if __name__ == "__main__":
    main()
