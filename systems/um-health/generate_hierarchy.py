#!/usr/bin/env python3
"""Generate UM Health hierarchy visualization matching UW Medicine style."""

import json
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

with open('hierarchy.json') as f:
    data = json.load(f)

entities = {e['id']: e for e in data['entities']}
relationships = data['relationships']

root_id = 'um-health-root'

# Separate by tier
tier1 = []  # hospitals
tier2 = []  # specialty centers
tier3 = []  # clinics, provider practices
for rel in relationships:
    target = entities[rel['target']]
    if target.get('tier') == 1:
        tier1.append((rel, target))
    elif target.get('tier') == 2:
        tier2.append((rel, target))
    elif target.get('tier') == 3:
        tier3.append((rel, target))

tier1.sort(key=lambda x: x[1]['name'])
tier2.sort(key=lambda x: x[1]['name'])
tier3.sort(key=lambda x: x[1]['name'])

fig, ax = plt.subplots(1, 1, figsize=(16, 11), facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(-1, 17)
ax.set_ylim(-1, 12)
ax.axis('off')

# Title
# Dynamic tier descriptions from actual data
tier_labels = {}
for e in data['entities']:
    t = e.get('tier')
    if t == 0:
        tier_labels[0] = 'Health System'
    elif t == 1:
        tier_labels[1] = 'Hospitals / Medical Centers'
    elif t == 2:
        tier_labels[2] = 'Specialty Centers / Ambulatory Care'
    elif t == 3:
        tier_labels[3] = 'Clinics / Provider Practices'

title = 'University of Michigan Health — HS2 Hierarchy'
subtitle_parts = [f'Tier {k}: {v}' for k, v in sorted(tier_labels.items())]
subtitle = ' | '.join(subtitle_parts)
ax.text(8, 11.2, title, ha='center', va='top', fontsize=20, fontweight='bold', color=TITLE_COLOR, family='sans-serif')
ax.text(8, 10.6, subtitle, ha='center', va='top', fontsize=13, color='#8b949e', family='sans-serif')

# Root node
root_x, root_y = 8, 9.5
root_r = 0.55
circle = plt.Circle((root_x, root_y), root_r, color=NODE_ROOT, ec='#30363d', linewidth=2)
ax.add_patch(circle)
ax.text(root_x + 0.05, root_y, '★ UM Health', ha='center', va='center', fontsize=12, fontweight='bold', color=TEXT, family='sans-serif')

# Short name map
short_names = {
    'C.S. Mott Children\'s Hospital': 'C.S. Mott',
    'Frankel Cardiovascular Center': 'Frankel CVC',
    'Kellogg Eye Center': 'Kellogg Eye',
    'Rogel Cancer Center': 'Rogel Cancer',
    'Transplant Center': 'Transplant',
    'UM Health-Sparrow': 'UM-Sparrow',
    'UM Health-West (Metro Health Hospital)': 'UM-West',
    'Von Voigtlander Women\'s Hospital': 'Von Voigtlander',
}

# Tier 1: Hospitals (row at y=6.5)
t1_y = 6.5
t1_r = 0.45
t1_count = len(tier1)
t1_spacing = 14 / (t1_count + 1)
t1_positions = {}

for i, (rel, ent) in enumerate(tier1):
    x = 1 + i * t1_spacing
    t1_positions[ent['id']] = (x, t1_y)
    circle = plt.Circle((x, t1_y), t1_r, color=NODE_T1, ec='#30363d', linewidth=1.5)
    ax.add_patch(circle)
    name = short_names.get(ent['name'], ent['name'])
    ax.text(x, t1_y, name, ha='center', va='center', fontsize=10, color=TEXT, family='sans-serif')

# Tier 2: Specialty Centers (row at y=3)
t2_y = 3.0
t2_r = 0.45
t2_count = len(tier2)
t2_spacing = 14 / (t2_count + 1)
t2_positions = {}

for i, (rel, ent) in enumerate(tier2):
    x = 1 + i * t2_spacing
    t2_positions[ent['id']] = (x, t2_y)
    circle = plt.Circle((x, t2_y), t2_r, color=NODE_T2, ec='#30363d', linewidth=1.5)
    ax.add_patch(circle)
    name = short_names.get(ent['name'], ent['name'])
    ax.text(x, t2_y, name, ha='center', va='center', fontsize=10, color=TEXT, family='sans-serif')

# Tier 3: Clinics / Provider Practices (row at y=0.5)
if tier3:
    t3_y = 0.5
    t3_r = 0.35
    t3_count = len(tier3)
    t3_spacing = 14 / (t3_count + 1)
    t3_positions = {}

    for i, (rel, ent) in enumerate(tier3):
        x = 1 + i * t3_spacing
        t3_positions[ent['id']] = (x, t3_y)
        circle = plt.Circle((x, t3_y), t3_r, color=NODE_T3, ec='#30363d', linewidth=1.5)
        ax.add_patch(circle)
        name = short_names.get(ent['name'], ent['name'])
        ax.text(x, t3_y, name, ha='center', va='center', fontsize=9, color=TEXT, family='sans-serif')

# Draw edges
for rel in relationships:
    target_id = rel['target']
    rtype = rel['relationship_type']

    if rtype == 'owns':
        color = EDGE_OWNS
        ls = '-'
        lw = 2
    elif rtype == 'manages':
        color = EDGE_MANAGES
        ls = '--'
        lw = 2.5
    else:
        color = EDGE_PARTNERS
        ls = ':'
        lw = 2.5

    # Find target position
    if target_id in t1_positions:
        tx, ty = t1_positions[target_id]
    elif target_id in t2_positions:
        tx, ty = t2_positions[target_id]
    elif 't3_positions' in globals() and target_id in t3_positions:
        tx, ty = t3_positions[target_id]
    else:
        continue

    # Curved arrow from root to target
    arrow = FancyArrowPatch(
        (root_x, root_y), (tx, ty),
        arrowstyle='->', mutation_scale=18,
        color=color, linewidth=lw, linestyle=ls,
        connectionstyle='arc3,rad=0.15',
        shrinkA=12, shrinkB=12
    )
    ax.add_patch(arrow)

# Legend with dynamic counts
rel_counts = {}
for rel in relationships:
    rt = rel['relationship_type']
    rel_counts[rt] = rel_counts.get(rt, 0) + 1

legend_x, legend_y = 0.5, 0.5
legend_bg = FancyBboxPatch((legend_x - 0.1, legend_y - 0.15), 2.2, 1.5,
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
plt.savefig('hierarchy.png', dpi=150, bbox_inches='tight', facecolor=BG)
print('Saved hierarchy.png')
