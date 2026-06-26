#!/usr/bin/env python3
"""Visualize UR Medicine HS2 hierarchy with improved layout for wide tiers."""
import json
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    with open('hierarchy.json') as f:
        data = json.load(f)

    entities = {e['id']: e for e in data['entities']}
    rels = data['relationships']

    G = nx.DiGraph()

    for e in data['entities']:
        label = e['name']
        if e['tier'] == 0:
            label = f"\u2605 {label}"
        G.add_node(e['id'], name=e['name'], tier=e['tier'],
                   etype=e['type'], label=label)

    for r in rels:
        G.add_edge(r['source'], r['target'],
                   rtype=r['relationship_type'], confidence=r['confidence'])

    # Layout - hierarchical by tier with adaptive spacing
    tiers = {}
    for node in G.nodes():
        t = G.nodes[node]['tier']
        tiers.setdefault(t, []).append(node)

    pos = {}
    y_spacing = 3
    for tier_num, nodes in sorted(tiers.items()):
        n = len(nodes)
        # Adaptive x-spacing: wider for larger tiers, extra wide for tier 2
        if tier_num == 2:
            x_spacing = 8  # Extra spacing for tier 2 to avoid overlap
        else:
            x_spacing = max(3, n * 0.8)
        total_width = (n - 1) * x_spacing
        start_x = -total_width / 2
        for i, node in enumerate(nodes):
            pos[node] = (start_x + i * x_spacing, -tier_num * y_spacing)

    # Draw
    fig, ax = plt.subplots(figsize=(20, 10))

    tier_colors = {0: '#1a1a2e', 1: '#16213e', 2: '#0f3460'}
    tier_sizes = {0: 4500, 1: 2200, 2: 1800}

    for tier_num in sorted(tiers.keys()):
        nodes_list = [n for n in G.nodes() if G.nodes[n]['tier'] == tier_num]
        nx.draw_networkx_nodes(G, pos, nodelist=nodes_list,
                               node_size=tier_sizes[tier_num],
                               node_color=tier_colors[tier_num],
                               ax=ax, alpha=0.9, edgecolors='#333',
                               linewidths=1.5)

    # Truncate long labels for display
    short_labels = {}
    for n in G.nodes():
        name = G.nodes[n]['name']
        tier = G.nodes[n]['tier']
        if tier == 0:
            short_labels[n] = "\u2605 UR Medicine"
        elif tier == 1:
            # Short hospital names
            short = name.replace(' Hospital', '').replace(' Memorial', '')
            if len(short) > 22:
                short = short[:20] + '...'
            short_labels[n] = short
        else:
            short = name.replace(' Institute for Oral Health', ' Dental')
            short = short.replace('James P. Wilmot Cancer Center', 'Wilmot Cancer Center')
            short_labels[n] = short

    nx.draw_networkx_labels(G, pos, short_labels, font_size=10,
                            font_weight='bold', font_color='white',
                            ax=ax, font_family='sans-serif')

    edge_styles = {
        'owns': {'style': 'solid', 'color': '#2ecc71', 'width': 2.5},
        'manages': {'style': 'dashed', 'color': '#3498db', 'width': 2},
        'partners_with': {'style': 'dotted', 'color': '#e74c3c', 'width': 2.5},
    }

    for edge in G.edges():
        rtype = G.edges[edge]['rtype']
        style = edge_styles[rtype]
        nx.draw_networkx_edges(G, pos, edgelist=[edge], ax=ax,
                              edge_color=style['color'], width=style['width'],
                              style=style['style'], alpha=0.7,
                              arrows=True, arrowsize=18,
                              arrowstyle='-|>', connectionstyle='arc3,rad=0.15')

    # Legend with dynamic counts
    from matplotlib.lines import Line2D
    rel_counts = {}
    for r in data['relationships']:
        rt = r['relationship_type']
        rel_counts[rt] = rel_counts.get(rt, 0) + 1
    legend_elements = []
    for rtype, style in edge_styles.items():
        count = rel_counts.get(rtype, 0)
        legend_elements.append(
            Line2D([0], [0], color=style['color'], lw=style['width'],
                   label=f'{rtype} ({count})', linestyle=style['style']))
    ax.legend(handles=legend_elements, loc='lower left', framealpha=1,
             fontsize=10, labelcolor='white', edgecolor='#333',
             facecolor='#1a1a2e')

    # Dynamic tier descriptions from actual data
    tier_labels = {}
    for e in data['entities']:
        t = e.get('tier', 0)
        if t == 0:
            tier_labels[0] = 'Health System'
        elif t == 1:
            tier_labels[1] = 'Hospitals / Medical Centers'
        elif t == 2:
            tier_labels[2] = 'Clinics / Specialty Centers / Ambulatory Care'
        elif t == 3:
            tier_labels[3] = 'Satellite Locations / Provider Practices'
    tier_label = ' | '.join(f"Tier {k}: {v}" for k, v in sorted(tier_labels.items()))
    ax.set_title(f'UR Medicine (University of Rochester Medical Center) — HS2 Hierarchy\n{tier_label}',
                 fontsize=15, fontweight='bold', color='white', pad=20)

    ax.set_axis_off()
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    plt.tight_layout()
    plt.savefig('hierarchy.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    print("Saved to hierarchy.png")

if __name__ == '__main__':
    main()
