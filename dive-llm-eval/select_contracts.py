#!/usr/bin/env python3
"""
Pick a small contract set that exercises every DASP category in both directions.

A set made only of heavily-labelled contracts is a bad benchmark: with no negative
cells, precision is undefined and a model that answers all-1s scores perfectly. So
the selection enforces two constraints at once:

  * every category appears POSITIVE in at least `--min-pos` chosen contracts
  * every category appears NEGATIVE in at least `--min-neg` chosen contracts

Greedy set-cover on the combined (category, polarity) universe, tie-broken toward
smaller source files to keep token cost down.

Usage:
    python3 select_contracts.py --labels data/Labels/DIVE_Labels.csv \
        --index data/sol_index.tsv --min-pos 2 --min-neg 2
"""

import argparse
import csv

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
    ap.add_argument("--index", default="data/sol_index.tsv",
                    help="TSV of contractID <TAB> source size in bytes")
    ap.add_argument("--min-pos", type=int, default=2)
    ap.add_argument("--min-neg", type=int, default=2)
    ap.add_argument("--max-bytes", type=int, default=30000,
                    help="skip contracts whose source is larger than this")
    ap.add_argument("--min-bytes", type=int, default=1200,
                    help="skip stubs; DIVE contains empty contracts like 'contract HiL2{}' "
                         "which are trivially all-negative and worthless as evidence")
    ap.add_argument("--out", default="selected_ids.txt")
    args = ap.parse_args()

    size = {}
    for line in open(args.index):
        cid, sz = line.split()
        size[cid] = int(sz)

    rows = []
    for r in csv.DictReader(open(args.labels)):
        cid = r["contractID"].strip()
        sz = size.get(cid, 1 << 30)
        if sz > args.max_bytes or sz < args.min_bytes:
            continue
        rows.append((cid, {c: int(r[c]) for c in DASP}))

    # Universe: each category must be hit `min_pos` times positive and `min_neg`
    # times negative. Track remaining need per (category, polarity).
    need = {(c, 1): args.min_pos for c in DASP}
    need.update({(c, 0): args.min_neg for c in DASP})

    chosen, remaining = [], list(rows)
    while any(v > 0 for v in need.values()):
        best, best_score = None, None
        for cid, lab in remaining:
            gain = sum(1 for c in DASP if need[(c, lab[c])] > 0)
            if gain == 0:
                continue
            # maximise newly-covered slots, then prefer the smaller contract
            score = (gain, -size[cid])
            if best_score is None or score > best_score:
                best, best_score = (cid, lab), score
        if best is None:
            print("! could not fully cover the universe with the given constraints")
            break
        cid, lab = best
        chosen.append(best)
        remaining.remove(best)
        for c in DASP:
            k = (c, lab[c])
            if need[k] > 0:
                need[k] -= 1

    with open(args.out, "w") as fh:
        fh.write("\n".join(cid for cid, _ in chosen) + "\n")

    print(f"selected {len(chosen)} contracts -> {args.out}\n")
    hdr = "".join(f"{c[:11]:>12}" for c in DASP)
    print(f"{'contract':>9}{'bytes':>8}{hdr}")
    for cid, lab in chosen:
        cells = "".join(f"{lab[c]:>12}" for c in DASP)
        print(f"{cid:>9}{size[cid]:>8}{cells}")
    pos = "".join(f"{sum(l[c] for _, l in chosen):>12}" for c in DASP)
    neg = "".join(f"{sum(1 - l[c] for _, l in chosen):>12}" for c in DASP)
    print(f"{'POS':>9}{'':>8}{pos}")
    print(f"{'NEG':>9}{'':>8}{neg}")
    print(f"\ntotal source bytes: {sum(size[cid] for cid, _ in chosen):,}")


if __name__ == "__main__":
    main()
