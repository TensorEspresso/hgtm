# AGENTS.md

Hierarchical Structure of Health Systems (HS2) — US health system hierarchy with validated, typed relationships.

## Project Layout

```
hs2/
├── README.md          ← model spec (tiers, relationship types, schemas)
├── systems/           ← per health system
│   ├── um-health/
│   ├── ur-medicine/
│   └── uw-medicine/
│       ├── hierarchy.json
│       ├── hierarchy.png
│       └── generate_hierarchy.py
└── tools/             ← reusable scripts
```

## Structural Invariants

- Each system directory contains: `hierarchy.json`, `hierarchy.png`, `generate_hierarchy.py`
- `hierarchy.json` follows the schema in README.md
- Entity fields: `id`, `name`, `type`, `tier`, `address`, `note` (required); `brand_id`, `epic_id`, `fhir_endpoint` (optional)
- Relationship fields: `source`, `target`, `relationship_type`, `confidence`, `sources`, `verified_at` (required); `note` (optional, only for `manages`/`partners_with`)
- Relationship types: `owns`, `manages`, `partners_with`
- Confidence levels: `high`, `medium`, `low`, `inferred`
- Visualizations use dark theme with color-coded edges: green=owns, blue=manages, red=partners_with

## Workflow Rules

- New systems: research → create `hierarchy.json` → run `generate_hierarchy.py` → validate
- Relationship type corrections: update JSON → regenerate PNG → verify legend counts
- All systems must pass schema parity validation

## Verification Standard

- `hierarchy.json` summary counts match actual entity/relationship counts
- All entities have `note` and `address`
- All visualizations have dynamic legend counts from data
- No orphan entities (every entity appears in at least one relationship)
