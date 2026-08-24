#!/usr/bin/env python3
"""Generate HS2 hierarchy visualization — multi-level parent-child edges."""

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

    children = {}
    for rel in relationships:
        children.setdefault(rel['source'], []).append((rel, entities[rel['target']]))

    tier1, tier2, tier3 = [], [], []
    root_id = None
    for e in data['entities']:
        t = e.get('tier')
        if t == 0: root_id = e['id']
    
    for rel in relationships:
        target = entities[rel['target']]
        t = target.get('tier')
        if t == 1: tier1.append((rel, target))
        elif t == 2: tier2.append((rel, target))
        elif t == 3: tier3.append((rel, target))

    tier1.sort(key=lambda x: x[1]['name'])
    tier2.sort(key=lambda x: x[1]['name'])
    tier3.sort(key=lambda x: x[1]['name'])

    fig, ax = plt.subplots(1, 1, figsize=(18, 12), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-1, 19)
    ax.set_ylim(-1, 13)
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
    
    ax.text(9, 12.2, title, ha='center', va='top', fontsize=20, fontweight='bold', color=TITLE_COLOR, family='sans-serif')
    ax.text(9, 11.6, subtitle, ha='center', va='top', fontsize=13, color='#8b949e', family='sans-serif')

    positions = {}

    if root_id:
        root_x, root_y = 9, 10.5
        positions[root_id] = (root_x, root_y)
        circle = plt.Circle((root_x, root_y), 0.55, color=NODE_ROOT, ec='#30363d', linewidth=2)
        ax.add_patch(circle)
        ax.text(root_x + 0.05, root_y, f'★ {system_name}', ha='center', va='center', fontsize=12, fontweight='bold', color=TEXT, family='sans-serif')

    t1_y, t1_r = 7.0, 0.45
    t1_count = len(tier1)
    t1_spacing = 16 / (t1_count + 1) if t1_count > 0 else 0

    for i, (rel, ent) in enumerate(tier1):
        x = 1.5 + i * t1_spacing
        positions[ent['id']] = (x, t1_y)
        circle = plt.Circle((x, t1_y), t1_r, color=NODE_T1, ec='#30363d', linewidth=1.5)
        ax.add_patch(circle)
        ax.text(x, t1_y, ent['name'], ha='center', va='center', fontsize=10, color=TEXT, family='sans-serif')

    t2_y, t2_r = 3.5, 0.4
    t2_parent_id = None
    for rel, ent in tier2:
        for r in relationships:
            if r['target'] == ent['id']:
                t2_parent_id = r['source']
                break
        if t2_parent_id: break

    if t2_parent_id and t2_parent_id in positions:
        parent_x, _ = positions[t2_parent_id]
        t2_count = len(tier2)
        t2_spacing = 2.5
        t2_start_x = parent_x - ((t2_count - 1) * t2_spacing) / 2
    else:
        t2_start_x, t2_spacing = 3, 3

    for i, (rel, ent) in enumerate(tier2):
        x = t2_start_x + i * t2_spacing
        positions[ent['id']] = (x, t2_y)
        circle = plt.Circle((x, t2_y), t2_r, color=NODE_T2, ec='#30363d', linewidth=1.5)
        ax.add_patch(circle)
        ax.text(x, t2_y, ent['name'], ha='center', va='center', fontsize=10, color=TEXT, family='sans-serif')

    if tier3:
        t3_y, t3_r = 0.5, 0.35
        t3_count = len(tier3)
        t3_spacing = 16 / (t3_count + 1)
        for i, (rel, ent) in enumerate(tier3):
            x = 1.5 + i * t3_spacing
            positions[ent['id']] = (x, t3_y)
            circle = plt.Circle((x, t3_y), t3_r, color=NODE_T3, ec='#30363d', linewidth=1.5)
            ax.add_patch(circle)
            ax.text(x, t3_y, ent['name'], ha='center', va='center', fontsize=9, color=TEXT, family='sans-serif')

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
            connectionstyle='arc3,rad=0.15', shrinkA=12, shrinkB=12
        )
        ax.add_patch(arrow)

    rel_counts = {}
    for rel in relationships:
        rt = rel['relationship_type']
        rel_counts[rt] = rel_counts.get(rt, 0) + 1

    legend_x, legend_y = 0.5, 0.5
    legend_bg = FancyBboxPatch((legend_x - 0.1, legend_y - 0.15), 2.8, 1.5,
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
