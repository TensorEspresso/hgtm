#!/usr/bin/env python3
"""Generate HS2 hierarchy visualization — multi-level parent-child edges.

Canvas width adapts to the densest tier so node labels never collide.
"""

import json
import sys
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

BG = '#0d1117'
TITLE_COLOR = '#e6edf3'
NODE_ROOT = '#1c2541'
NODE_T1 = '#1a2332'
NODE_T2 = '#1c3a5e'
NODE_T3 = '#1a4a5e'
TEXT = '#ffffff'
EDGE_OWNS = '#39d353'
EDGE_MANAGES = '#58a6ff'
EDGE_PARTNERS = '#f85149'

# data-units per character of node label (heuristic for sans-serif,
# scale-invariant because figsize and xlim are scaled together)
CHAR_W = 0.062
LABEL_PAD = 0.6      # horizontal gap reserved between adjacent labels
MIN_NODE_SPACING = 2.4
MIN_ROW_WIDTH = 16.0
MIN_CANVAS_W = 18.0


def row_width(names, min_spacing=MIN_NODE_SPACING):
    """Width a row of n named nodes needs so labels don't collide."""
    if not names:
        return MIN_ROW_WIDTH
    per = min_spacing + LABEL_PAD
    longest = max(len(n) for n in names)
    per = max(per, longest * CHAR_W + LABEL_PAD)
    return max(MIN_ROW_WIDTH, len(names) * per)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_hierarchy.py <system_dir>")
        sys.exit(1)

    system_dir = sys.argv[1]
    json_path = os.path.join(system_dir, 'hierarchy.json')
    output_path = os.path.join(system_dir, 'hierarchy.png')

    with open(json_path) as f:
        data = json.load(f)

    entities = {e['id']: e for e in data['entities']}
    relationships = data['relationships']

    tier1, tier2, tier3 = [], [], []
    root_id = None
    for e in data['entities']:
        if e.get('tier') == 0:
            root_id = e['id']
    for rel in relationships:
        t = entities[rel['target']].get('tier')
        if t == 1:
            tier1.append((rel, entities[rel['target']]))
        elif t == 2:
            tier2.append((rel, entities[rel['target']]))
        elif t == 3:
            tier3.append((rel, entities[rel['target']]))

    tier1.sort(key=lambda x: x[1]['name'])
    tier2.sort(key=lambda x: x[1]['name'])
    tier3.sort(key=lambda x: x[1]['name'])

    w1 = row_width([e['name'] for _r, e in tier1])
    w2 = row_width([e['name'] for _r, e in tier2], min_spacing=2.6)
    w3 = row_width([e['name'] for _r, e in tier3], min_spacing=1.8)
    canvas_w = max(MIN_CANVAS_W, w1, w2, w3) + 2.0
    canvas_h = 13.0

    fig, ax = plt.subplots(1, 1, figsize=(canvas_w, canvas_h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-1, canvas_w + 1)
    ax.set_ylim(-1, canvas_h)
    ax.axis('off')

    tier_labels = {
        0: 'Health System',
        1: 'Hospitals / Medical Centers',
        2: 'Specialty Centers / Ambulatory Care',
        3: 'Clinics / Provider Practices'
    }

    system_name = entities[root_id]['name'] if root_id else "Unknown System"
    title = f"{system_name} — HS2 Hierarchy"
    subtitle = ' | '.join([f'Tier {k}: {v}' for k, v in sorted(tier_labels.items())])

    cx = canvas_w / 2
    ax.text(cx, 12.2, title, ha='center', va='top', fontsize=20, fontweight='bold', color=TITLE_COLOR, family='sans-serif')
    ax.text(cx, 11.6, subtitle, ha='center', va='top', fontsize=13, color='#8b949e', family='sans-serif')

    positions = {}

    if root_id:
        root_x, root_y = cx, 10.5
        positions[root_id] = (root_x, root_y)
        circle = plt.Circle((root_x, root_y), 0.55, color=NODE_ROOT, ec='#30363d', linewidth=2)
        ax.add_patch(circle)
        ax.text(root_x + 0.05, root_y, f'★ {system_name}', ha='center', va='center', fontsize=12, fontweight='bold', color=TEXT, family='sans-serif')

    def place_row(items, y, radius, font, width):
        n = len(items)
        if n == 0:
            return
        spacing = width / (n + 1)
        for i, (rel, ent) in enumerate(items):
            x = 1.5 + (i + 1) * spacing
            positions[ent['id']] = (x, y)
            circle = plt.Circle((x, y), radius, color=NODE_ROOT if ent.get('tier') == 0 else
                                {1: NODE_T1, 2: NODE_T2, 3: NODE_T3}.get(ent.get('tier'), NODE_T1),
                                ec='#30363d', linewidth=1.5)
            ax.add_patch(circle)
            ax.text(x, y - radius - 0.28, ent['name'], ha='center', va='top',
                    fontsize=font, color=TEXT, family='sans-serif')

    place_row(tier1, 7.4, 0.45, 10, w1)
    place_row(tier3, 0.9, 0.35, 9, w3)

    # tier 2: center under its parent when the parent is placed (e.g. a hospital), else under the root
    t2_parent_id = None
    for rel, ent in tier2:
        src = rel['source']
        if src in positions:
            t2_parent_id = src
            break
    if t2_parent_id is None and root_id:
        t2_parent_id = root_id
    if t2_parent_id:
        parent_x = positions[t2_parent_id][0]
        t2_w = min(w2, canvas_w - 2)
        t2_spacing = t2_w / (len(tier2) + 1)
        for i, (rel, ent) in enumerate(tier2):
            x = parent_x - t2_w / 2 + (i + 1) * t2_spacing
            positions[ent['id']] = (x, 4.2)
            circle = plt.Circle((x, 4.2), 0.4, color=NODE_T2, ec='#30363d', linewidth=1.5)
            ax.add_patch(circle)
            ax.text(x, 4.2 - 0.68, ent['name'], ha='center', va='top', fontsize=10, color=TEXT, family='sans-serif')

    for rel in relationships:
        source_id, target_id, rtype = rel['source'], rel['target'], rel['relationship_type']
        if rtype == 'owns': color, ls, lw = EDGE_OWNS, '-', 2
        elif rtype == 'manages': color, ls, lw = EDGE_MANAGES, '--', 2.5
        else: color, ls, lw = EDGE_PARTNERS, ':', 2.5

        if source_id not in positions or target_id not in positions: continue

        sx, sy = positions[source_id]
        tx, ty = positions[target_id]
        arrow = FancyArrowPatch(
            (sx, sy), (tx, ty), arrowstyle='->', mutation_scale=18,
            color=color, linewidth=lw, linestyle=ls,
            connectionstyle='arc3,rad=0.12', shrinkA=12, shrinkB=12
        )
        ax.add_patch(arrow)

    rel_counts = {}
    for rel in relationships:
        rt = rel['relationship_type']
        rel_counts[rt] = rel_counts.get(rt, 0) + 1

    # legend: top-left, clear of the centered root node
    legend_x, legend_y = 0.5, 9.9
    legend_bg = FancyBboxPatch((legend_x - 0.1, legend_y - 0.15), 3.0, 1.5,
                               boxstyle='round,pad=0.1', facecolor='#161b22',
                               edgecolor='#30363d', alpha=0.9)
    ax.add_patch(legend_bg)

    legend_items = [
        (EDGE_OWNS, '-', f'owns ({rel_counts.get("owns", 0)})', legend_y + 1.0),
        (EDGE_MANAGES, '--', f'manages ({rel_counts.get("manages", 0)})', legend_y + 0.55),
        (EDGE_PARTNERS, ':', f'partners_with ({rel_counts.get("partners_with", 0)})', legend_y + 0.1),
    ]

    for color, ls, label, y in legend_items:
        ax.plot([legend_x + 0.15, legend_x + 0.55], [y, y], color=color, linewidth=2.5, linestyle=ls)
        ax.text(legend_x + 0.7, y, label, ha='left', va='center', fontsize=10, color=TEXT, family='sans-serif')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f'Saved {output_path}')

if __name__ == '__main__':
    main()
