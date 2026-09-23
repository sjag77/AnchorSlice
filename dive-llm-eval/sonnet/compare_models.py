#!/usr/bin/env python3
"""Four-way comparison: {Opus, Sonnet} x {full source, AnchorSlice} on the 50-contract sample."""
import json, math, sys
RUNS = {'Opus full': 'results_50_calibrated.json', 'Opus sliced': 'results_50_sliced.json',
        'Sonnet full': 'sonnet/results_50_sonnet_full.json', 'Sonnet sliced': 'sonnet/results_50_sonnet_sliced.json'}
D = {k: json.load(open(v)) for k, v in RUNS.items()}
R = {k: {r['contractID']: r for r in d['records'] if 'prediction' in r} for k, d in D.items()}
ids = sorted(set.intersection(*(set(r) for r in R.values())), key=int)
C = D['Opus full']['summary']['per_category'].keys()

def cells(k):
    return [(c, cat, R[k][c]['ground_truth'][cat], R[k][c]['prediction'][cat]) for c in ids for cat in C]
def metrics(cs):
    tp = sum(g and p for *_, g, p in cs); fp = sum(p and not g for *_, g, p in cs)
    fn = sum(g and not p for *_, g, p in cs); tn = len(cs) - tp - fp - fn; n = len(cs)
    pr = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
    po = (tp + tn) / n; pe = ((tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)) / n / n
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, acc=po, p=pr, r=rc, f1=f1, k=(po - pe) / (1 - pe) if pe < 1 else 0)
def mcnemar(a, b):
    ca = {(c, t): g == p for c, t, g, p in cells(a)}; cb = {(c, t): g == p for c, t, g, p in cells(b)}
    x = sum(ca[k] and not cb[k] for k in ca); y = sum(cb[k] and not ca[k] for k in ca); n = x + y
    p = min(1, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n) if n else 1
    return x, y, p

print(f"{len(ids)} contracts, {len(ids)*8} label cells\n")
print('== Detection (micro, vs DIVE) ==')
print(f"{'run':15}{'agree':>7}{'prec':>7}{'rec':>7}{'F1':>7}{'kappa':>7}{'TP':>5}{'FP':>5}{'FN':>5}{'exact':>7}")
for k in RUNS:
    m = metrics(cells(k)); ex = sum(all(R[k][c]['prediction'][t] == R[k][c]['ground_truth'][t] for t in C) for c in ids)
    print(f"{k:15}{m['acc']:7.3f}{m['p']:7.3f}{m['r']:7.3f}{m['f1']:7.3f}{m['k']:7.3f}{m['tp']:5}{m['fp']:5}{m['fn']:5}{ex:5}/50")

print('\n== Resources ==')
print(f"{'run':15}{'tokens':>10}{'tok/ctr':>9}{'output':>9}{'wall s':>9}{'s/ctr':>7}{'cost $':>8}")
for k, d in D.items():
    s = d['summary']; t = s['tokens']
    print(f"{k:15}{t['total_tokens']:10,}{t['total_tokens']/50:9,.0f}{t['output_tokens']:9,}{s['timing']['run_wall_seconds']:9.1f}"
          f"{s['timing']['run_wall_seconds']/50:7.1f}{s['cost_usd']:8.2f}")

print('\n== Paired McNemar tests (cells correct only in A / only in B) ==')
for a, b in [('Opus full', 'Opus sliced'), ('Sonnet full', 'Sonnet sliced'), ('Opus full', 'Sonnet full'), ('Opus sliced', 'Sonnet sliced')]:
    x, y, p = mcnemar(a, b); print(f"{a:14} vs {b:14}: {x:3} / {y:3}   p = {p:.3f}")

print('\n== Per-category F1 (agreement) ==')
print(f"{'category':25}" + ''.join(f"{k:>15}" for k in RUNS))
for cat in C:
    row = f"{cat:25}"
    for k in RUNS:
        m = metrics([x for x in cells(k) if x[1] == cat]); row += f"{m['f1']:8.2f} ({m['acc']:.2f})"
    print(row)
print(f"{'DIVE positives':25}" + ''.join(f"{'':>15}" for _ in RUNS))
print('\n== Per-category predicted positives (DIVE+ in brackets) ==')
for cat in C:
    pos = sum(R['Opus full'][c]['ground_truth'][cat] for c in ids)
    print(f"{cat:25}[{pos:2}] " + '  '.join(f"{k.split()[0][0]}{k.split()[1][0]}={sum(R[k][c]['prediction'][cat] for c in ids):2}" for k in RUNS))

print('\n== Inter-model agreement (share of 400 cells with identical labels) ==')
ks = list(RUNS)
for i in range(4):
    for j in range(i + 1, 4):
        a, b = ks[i], ks[j]
        print(f"{a:14} ~ {b:14}: {sum(R[a][c]['prediction'][t] == R[b][c]['prediction'][t] for c in ids for t in C)/400:.3f}")
