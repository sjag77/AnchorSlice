#!/usr/bin/env python3
"""
Stage 1 - build the evaluation sample set.

Pulls the first N contracts (by contractID) out of the DIVE raw data, pairs each
one with its ground-truth DASP label vector from DIVE_Labels.csv, and writes a
single samples.json that stage 2 consumes.

Usage:
    python3 prepare_samples.py --data-dir <dir with the unpacked Zenodo files> [-n 10]
"""

import argparse
import csv
import json
import os
import sys

csv.field_size_limit(sys.maxsize)

# The 8 DASP categories DIVE labels, in the column order used by DIVE_Labels.csv.
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


def find_file(root, *names):
    """Locate the first file under `root` whose basename matches one of `names`."""
    for dirpath, _dirnames, filenames in os.walk(root):
        if "__MACOSX" in dirpath:
            continue
        for fn in filenames:
            if fn in names:
                return os.path.join(dirpath, fn)
    return None


def load_labels(path):
    """contractID -> {category: 0|1}"""
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            cid = str(row["contractID"]).strip()
            out[cid] = {c: int(row[c]) for c in DASP}
    return out


def find_source_dir(root):
    """DIVE raw ships one .sol per contract under Raw/PRE/Source codes/<contractID>.sol"""
    for dirpath, dirnames, _filenames in os.walk(root):
        for d in dirnames:
            if d.lower().replace("_", " ") == "source codes":
                return os.path.join(dirpath, d)
    # a flat directory of <id>.sol also works
    for dirpath, _dirnames, filenames in os.walk(root):
        if any(fn.endswith(".sol") and fn[:-4].isdigit() for fn in filenames):
            return dirpath
    return None


def read_source(src_dir, cid):
    path = os.path.join(src_dir, f"{cid}.sol")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("-n", "--num", type=int, default=10)
    ap.add_argument("--ids-file", help="newline-separated contractIDs to use instead of the first N "
                                       "(e.g. the output of select_contracts.py)")
    ap.add_argument("--out", default="samples.json")
    ap.add_argument("--max-chars", type=int, default=120_000,
                    help="truncate any single contract source longer than this")
    args = ap.parse_args()

    labels_path = find_file(args.data_dir, "DIVE_Labels.csv")
    if not labels_path:
        sys.exit("DIVE_Labels.csv not found under --data-dir")
    labels = load_labels(labels_path)

    src_dir = os.environ.get("DIVE_SOURCE_DIR") or find_source_dir(args.data_dir)
    if not src_dir:
        sys.exit("contract source directory not found; set DIVE_SOURCE_DIR")

    if args.ids_file:
        order = [l.strip() for l in open(args.ids_file) if l.strip()]
        limit = len(order)
    else:
        order = sorted(labels, key=lambda x: int(x))
        limit = args.num

    samples, skipped = [], []
    for cid in order:
        if len(samples) >= limit:
            break
        src = read_source(src_dir, cid).strip()
        if not src:
            skipped.append(cid)
            continue
        truncated = len(src) > args.max_chars
        samples.append({
            "contractID": cid,
            "source": src[:args.max_chars],
            "source_chars": len(src),
            "truncated": truncated,
            "ground_truth": labels[cid],
        })

    with open(args.out, "w") as fh:
        json.dump({"dasp": DASP, "samples": samples}, fh, indent=2)

    print(f"labels file : {labels_path}")
    print(f"source dir  : {src_dir}")
    print(f"wrote {len(samples)} samples -> {args.out}"
          + (f"  (skipped {len(skipped)} with no source: {skipped})" if skipped else ""))
    for s in samples:
        pos = [c for c in DASP if s["ground_truth"][c]]
        print(f"  #{s['contractID']:>5}  {s['source_chars']:>8} chars"
              f"{' [truncated]' if s['truncated'] else ''}  labels={pos or ['(none)']}")


if __name__ == "__main__":
    main()
