# Hierarchical Ground Truth Model (HGTM)

US Health System hierarchy — validated, typed relationships.

## Model

### Tiers

| Tier | Entity Type | Example |
|---|---|---|
| Root | Health System | University of Michigan Health |
| Tier 1 | Hospitals / Medical Centers | C.S. Mott Children's Hospital |
| Tier 2 | Clinics / Specialty Centers / Ambulatory Care | Kellogg Eye Center |
| Tier 3 | Satellite Locations / Provider Practices | Pediatric Cardiology in Flint |

### Relationship Types

| Type | Binding | Control | Evidence |
|---|---|---|---|
| **owns** | Equity ownership | Full | SEC filings, EIN overlap, state business registry |
| **manages** | Management contract | Operational | "Operated by" language, contract references |
| **partners_with** | Formal contract | Shared | Joint venture agreements, revenue sharing, clinical partnerships |

Loose affiliations (no contract, no equity) are **not** included.

### Validation

| Confidence | Requirement |
|---|---|
| **high** | 1 authoritative source (SEC, state licensing, CMS) |
| **medium** | 2 corroborating non-authoritative sources |
| **low** | 1 non-authoritative source |
| **inferred** | Pattern-based (naming, address overlap) — review queue only |

### Entity Schema

```json
{
  "id": "unique-id",
  "name": "Facility Name",
  "type": "hospital|specialty_center|clinic|health_system|...",
  "tier": 0|1|2|3,
  "address": {
    "street": "...",
    "city": "...",
    "state": "...",
    "zip": "..."
  },
  "identifiers": ["NPI", "EIN", ...],
  "note": "Optional context"
}
```

### Relationship Schema

```json
{
  "source": "source-entity-id",
  "target": "target-entity-id",
  "relationship_type": "owns|manages|partners_with",
  "confidence": "high|medium|low|inferred",
  "sources": ["source-name", ...],
  "verified_at": "YYYY-MM-DD",
  "note": "Optional context"
}
```

## Structure

```
hgtm/
├── README.md          ← this file (model spec)
├── systems/           ← per health system
│   ├── um-health/
│   │   ├── hierarchy.json
│   │   ├── hierarchy.png
│   │   └── generate_hierarchy.py
│   ├── ur-medicine/
│   │   ├── hierarchy.json
│   │   ├── hierarchy.png
│   │   └── generate_hierarchy.py
│   └── uw-medicine/
│       ├── hierarchy.json
│       ├── hierarchy.png
│       └── uw-medicine-hierarchy-report.md
└── tools/             ← reusable scripts
```

## Status

| Health System | Tiers | Entities | Owns | Manages | Partners | Status |
|---|---|---|---|---|---|---|
| University of Michigan Health | 1, 2 | 9 | 8 | 0 | 0 | Validated core |
| UR Medicine | 1, 2 | 12 | 5 | 0 | 6 | Validated core |
| UW Medicine | 1, 2 | 10 | 6 | 1 | 2 | Validated core |

Built with Qwen 3.6 27B (MTP) running locally via [Hermes Agent](https://github.com/nousresearch/hermes-agent).
