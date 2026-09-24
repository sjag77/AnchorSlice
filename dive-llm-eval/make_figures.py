#!/usr/bin/env python3
"""Draw the manuscript figures from the 200-contract results.

    python3 make_figures.py            # -> ../manuscript/fig{1,2,3}*.png (and the conference copy)

Fig. 1  the two arms of the experiment, with what each stage keeps
Fig. 2  per-category F1, ordinary practice against the pipeline
Fig. 3  resource use per contract
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = [os.path.join(HERE, '..', 'manuscript'), os.path.join(HERE, '..', 'manuscript_conference')]

INK, MUTE, RULE = '#1b2733', '#5a6672', '#c8d0d6'
SLICE, BASE, WARM = '#1f6f8b', '#9fb3bf', '#c2683a'
plt.rcParams.update({'font.family': 'serif',
                     'font.serif': ['Times New Roman', 'DejaVu Serif'],
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTE, 'ytick.color': MUTE, 'axes.edgecolor': RULE})

def save(fig, name):
    for d in OUT:
        if os.path.isdir(d):
            fig.savefig(os.path.join(d, name), dpi=400, bbox_inches='tight',
                        facecolor='white', pad_inches=0.04)
    plt.close(fig)
    print('wrote', name)

# ------------------------------------------------------------------ Fig. 1
def box(ax, x, y, w, h, text, face='white', edge=INK, lw=1.1, fs=9.5, weight='normal'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.008,rounding_size=0.012',
                                linewidth=lw, edgecolor=edge, facecolor=face, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs,
            color=INK, zorder=3, linespacing=1.35, fontweight=weight)

def arrow(ax, x1, y, x2, color=MUTE, lw=1.1):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle='-|>', mutation_scale=9,
                                 linewidth=lw, color=color, zorder=1,
                                 shrinkA=0, shrinkB=0))

def figure_pipeline():
    fig, ax = plt.subplots(figsize=(7.4, 2.75))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    # --- Arm A
    ax.text(0.005, 0.95, 'Arm A · ordinary practice', fontsize=10, fontweight='bold', color=INK)
    box(ax, 0.005, 0.66, 0.175, 0.20, '200 contracts\n2,311,110 chars', face='#f4f7f8')
    arrow(ax, 0.185, 0.76, 0.655)
    ax.text(0.42, 0.80, 'complete source · 100%', fontsize=9, style='italic',
            color=MUTE, ha='center')
    box(ax, 0.66, 0.66, 0.15, 0.20, 'detector\n(Opus 5)', face='#f4f7f8')
    arrow(ax, 0.815, 0.76, 0.845)
    box(ax, 0.85, 0.66, 0.145, 0.20, '8 DASP\nlabels', face='#f4f7f8')
    ax.text(0.995, 0.60, '10,465 tokens · $0.089 · 20.8 s per contract',
            fontsize=8.6, color=MUTE, ha='right')

    ax.plot([0.005, 0.995], [0.50, 0.50], color=RULE, lw=0.8, ls=(0, (4, 3)))

    # --- Arm B
    ax.text(0.005, 0.40, 'Arm B · AnchorSlice pipeline', fontsize=10, fontweight='bold', color=SLICE)
    box(ax, 0.005, 0.11, 0.175, 0.20, '200 contracts\n2,311,110 chars', face='#f4f7f8')
    stages = [('S1 · strip\ncomments', 0.205), ('S2 · collapse\nlibrary code', 0.375),
              ('S3 · anchor\nwindows + tags', 0.545)]
    prev = 0.18
    for label, x in stages:
        arrow(ax, prev, 0.21, x, color=SLICE)
        box(ax, x, 0.11, 0.155, 0.20, label, edge=SLICE, lw=1.3, face='white')
        prev = x + 0.155
    arrow(ax, prev, 0.21, 0.72, color=SLICE)
    box(ax, 0.725, 0.11, 0.13, 0.20, 'detector\n(Opus 5)', face='#f4f7f8')
    arrow(ax, 0.858, 0.21, 0.878)
    box(ax, 0.88, 0.11, 0.115, 0.20, '8 DASP\nlabels', face='#f4f7f8')

    ax.annotate('56.5% of characters kept · evidence retention 463/463',
                xy=(0.60, 0.09), xytext=(0.60, 0.015), fontsize=8.8, color=SLICE,
                ha='center', style='italic')
    ax.text(0.005, 0.015, '4,689 tokens · $0.032 · 8.4 s per contract',
            fontsize=8.6, color=SLICE, ha='left', fontweight='bold')
    save(fig, 'fig1_pipeline.png')

# ------------------------------------------------------------------ Fig. 2
CATS = ['Reentrancy', 'Access Control', 'Unchecked Return\nValues', 'DoS',
        'Bad Randomness', 'Arithmetic', 'Time manipulation', 'Front Running']
F1_A = [0.19, 0.41, 0.46, 0.17, 0.58, 0.44, 0.67, 0.09]
F1_B = [0.82, 0.83, 0.74, 0.47, 0.62, 0.52, 0.58, 0.00]
POS = [98, 144, 38, 26, 16, 84, 42, 15]

def figure_per_category():
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    y = range(len(CATS))
    h = 0.38
    for i, (a, b) in enumerate(zip(F1_A, F1_B)):
        ax.barh(i + h / 2, a, height=h, color=BASE, edgecolor='none', zorder=2)
        ax.barh(i - h / 2, b, height=h, color=SLICE if b >= a else WARM, edgecolor='none', zorder=2)
        ax.text(a + 0.012, i + h / 2, f'{a:.2f}', va='center', fontsize=8, color=MUTE)
        ax.text(max(b, 0.006) + 0.012, i - h / 2, f'{b:.2f}', va='center', fontsize=8,
                color=SLICE if b >= a else WARM, fontweight='bold')
    ax.set_yticks(list(y))
    ax.set_yticklabels([f'{c}\n({p} positives)' for c, p in zip(CATS, POS)], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0); ax.set_xlabel('F1-score against the DIVE labels', fontsize=9.5)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.xaxis.grid(True, color=RULE, lw=0.6, zorder=0); ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.bar(0, 0, color=BASE, label='Arm A · complete source, simple prompt')
    ax.bar(0, 0, color=SLICE, label='Arm B · AnchorSlice, calibrated prompt')
    ax.bar(0, 0, color=WARM, label='Arm B, where it regressed')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), fontsize=8.6,
              frameon=False, ncol=3, columnspacing=1.6, handlelength=1.4)
    save(fig, 'fig2_per_category.png')

# ------------------------------------------------------------------ Fig. 3
def figure_resources():
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.05))
    panels = [('Tokens per contract', 10465, 4689, '{:,.0f}', '−55.2%'),
              ('Cost per contract (USD)', 0.089, 0.032, '{:.3f}', '−63.7%'),
              ('Seconds per contract', 20.8, 8.4, '{:.1f}', '−59.7%'),
              ('F1-score', 0.342, 0.693, '{:.3f}', '+103%')]
    for ax, (title, a, b, fmt, delta) in zip(axes, panels):
        gain = b > a
        ax.bar([0], [a], width=0.55, color=BASE, zorder=2)
        ax.bar([1], [b], width=0.55, color=SLICE, zorder=2)
        for x, v in ((0, a), (1, b)):
            ax.text(x, v, fmt.format(v), ha='center', va='bottom', fontsize=8.6,
                    color=INK, fontweight='bold' if x else 'normal')
        ax.set_title(title, fontsize=9, pad=12)
        ax.text(0.5, 1.0, delta, transform=ax.transAxes, ha='center', va='bottom',
                fontsize=9.5, color=SLICE if gain or delta.startswith('−') else WARM,
                fontweight='bold')
        ax.set_xticks([0, 1]); ax.set_xticklabels(['A', 'B'], fontsize=9)
        ax.set_ylim(0, max(a, b) * 1.32)
        ax.set_yticks([])
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis='x', length=0)
    fig.subplots_adjust(wspace=0.35)
    save(fig, 'fig3_resources.png')

if __name__ == '__main__':
    figure_pipeline(); figure_per_category(); figure_resources()
