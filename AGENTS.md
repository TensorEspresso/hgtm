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
│       └── hierarchy.png
└── tools/             ← reusable scripts
    └── generate_hierarchy.py
```

## Structural Invariants

- Each system directory contains: `hierarchy.json`, `hierarchy.png`\n- `hierarchy.json` follows the schema in README.md
- Entity fields: `id`, `name`, `type`, `tier`, `note` (required); `address` (required for physical types, omitted for non-physical); `addresses`, `service_area`, `brand_id`, `epic_id`, `fhir_endpoint` (optional)
- Relationship fields: `source`, `target`, `relationship_type`, `confidence`, `sources`, `verified_at` (required); `note` (optional, only for `manages`/`partners_with`)
- Relationship types: `owns`, `manages`, `partners_with`
- Confidence levels: `high`, `medium`, `low`, `inferred`
- Visualizations use dark theme with color-coded edges: green=owns, blue=manages, red=partners_with

## Workflow Rules

- New systems: research → create `hierarchy.json` → `python3 tools/validate_hierarchy.py <system_dir>` → `python3 tools/generate_hierarchy.py <system_dir>`
- Relationship type corrections: update JSON → regenerate PNG → verify legend counts
- All systems must pass schema parity validation

## Verification Standard

- `hierarchy.json` summary counts match actual entity/relationship counts
- All entities have `note`; physical types have a complete `address`, non-physical types omit it (footprint via `service_area` or `note`)
- All visualizations have dynamic legend counts from data
- No orphan entities (every entity appears in at least one relationship)
