#!/usr/bin/env python3
"""
Draw a stratified sample of N contracts.

Pure set cover (select_contracts.py) produces a bimodal set - a few heavily-labelled
contracts plus a few all-negative ones - which is fine for a 5-contract smoke test but
distorts base rates at N=50. This script instead takes a seeded random sample and then
repairs it: any category with fewer than `--min-per-cat` positives or negatives has
contracts swapped in until the floor is met. The result stays close to DIVE's natural
prevalence while guaranteeing every category is measurable in both directions.

Usage:
    python3 select_stratified.py -n 50 --seed 20260827
"""

import argparse
import csv
import random

DASP = [
    "Reentrancy",
    "Access Control",
    "Arithmetic",
    "Unchecked Return Values",
    "DoS",
    "Bad Randomness",
    "Front Running",
    "Time manipulation",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="data/Labels/DIVE_Labels.csv")
    ap.add_argument("--index", default="data/sol_index.tsv")
    ap.add_argument("-n", "--num", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260827)
    ap.add_argument("--min-per-cat", type=int, default=5,
                    help="minimum positives AND negatives required per category")
    ap.add_argument("--min-bytes", type=int, default=1200, help="skip empty stub contracts")
    ap.add_argument("--max-bytes", type=int, default=30000, help="cap token cost per contract")
    ap.add_argument("--out", default="selected_ids_50.txt")
    args = ap.parse_args()

    size = {}
    for line in open(args.index):
        cid, sz = line.split()
        size[cid] = int(sz)

    pool = {}
    for r in csv.DictReader(open(args.labels)):
        cid = r["contractID"].strip()
        sz = size.get(cid, 1 << 30)
        if args.min_bytes <= sz <= args.max_bytes:
            pool[cid] = {c: int(r[c]) for c in DASP}

    rng = random.Random(args.seed)
    chosen = set(rng.sample(sorted(pool), args.num))

    def count(cat, polarity):
        return sum(1 for c in chosen if pool[c][cat] == polarity)

    # Repair: swap out the least informative member for one that fixes a shortfall.
    for _ in range(4000):
        gaps = [(c, p) for c in DASP for p in (0, 1) if count(c, p) < args.min_per_cat]
        if not gaps:
            break
        cat, pol = gaps[0]
        cands = [c for c in pool if c not in chosen and pool[c][cat] == pol]
        if not cands:
            print(f"! no candidate left for {cat}={pol}")
            break
        add = rng.choice(cands)
        # drop whichever current member breaks the fewest floors if removed
        drop = min(
            (c for c in chosen if pool[c][cat] != pol),
            key=lambda c: sum(1 for k in DASP
                              if count(k, pool[c][k]) - 1 < args.min_per_cat),
            default=None,
        )
        if drop is None:
            break
        chosen.discard(drop)
        chosen.add(add)

    ids = sorted(chosen, key=int)
    with open(args.out, "w") as fh:
        fh.write("\n".join(ids) + "\n")

    print(f"selected {len(ids)} contracts -> {args.out}   (seed={args.seed})\n")
    print(f"{'category':<24}{'pos':>6}{'neg':>6}{'rate':>9}{'dataset rate':>15}")
    all_rows = [r for r in csv.DictReader(open(args.labels))]
    for c in DASP:
        p = sum(pool[i][c] for i in ids)
        full = sum(int(r[c]) for r in all_rows) / len(all_rows)
        print(f"{c:<24}{p:>6}{len(ids)-p:>6}{p/len(ids):>9.1%}{full:>15.1%}")
    tot = sum(sum(pool[i][c] for c in DASP) for i in ids)
    print(f"\ntotal positive cells: {tot} of {len(ids)*8}"
          f"   ({tot/(len(ids)*8):.1%})")
    print(f"mean labels/contract: {tot/len(ids):.2f}   (dataset: 2.46)")
    print(f"total source bytes  : {sum(size[i] for i in ids):,}")


if __name__ == "__main__":
    main()
