# Hierarchical Structure of Health Systems (HS2)

US Health System hierarchy — validated, typed relationships.

## Model

### Tiers

| Tier | Entity Type | Example |
|---|---|---|
| Tier 0 | Health System (root) | University of Michigan Health |
| Tier 1 | Hospitals / Medical Centers | C.S. Mott Children's Hospital |
| Tier 2 | Specialty Centers / Ambulatory Care Centers | Kellogg Eye Center |
| Tier 3 | Clinics / Satellite Locations / Provider Practices | UW Medicine Primary Care |

**Tier 2 vs Tier 3 distinction:** Tier 2 = specialty centers with independent brand identity and focused multi-service array (e.g., "Kellogg Eye Center," "Karmanos Cancer Institute"). Tier 3 = general clinics, satellite offices, provider practices — community-level access points with limited service (e.g., "Urology Clinic," "Pediatric Cardiology in Flint"). The dividing line is independent brand identity and service array, not naming convention alone.

**Evidence:** Every major US health system self-describes with this 3-level structure below the system root. UM Health: "3 hospitals, 6 specialty treatment centers and over 50 clinics." Cleveland Clinic: "23 hospitals, 276 outpatient facilities, 18 Family Health and Service Centers." Kaiser: "40 hospitals and 609 medical facilities." See `references/tier-system-research.md` for full research.

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
  "type": "hospital|specialty_center|clinic|health_system|physician_group|clinic_network|air_ambulance|...",
  "tier": 0|1|2|3,
  "address": {
    "street": "...",
    "city": "...",
    "state": "...",
    "zip": "..."
  },
  "addresses": [
    {
      "label": "Optional site label (unique per entity)",
      "street": "...",
      "city": "...",
      "state": "...",
      "zip": "..."
    }
  ],
  "service_area": "Optional geographic footprint (e.g. \"WWAMI region\")",
  "brand_id": "Epic FHIR brand UUID (optional)",
  "epic_id": "Epic system ID (optional)",
  "fhir_endpoint": "Epic FHIR proxy URL (optional)",
  "note": "Required context"
}
```

**Addressing rules:**

- `address` = primary site (HQ for the system root). **Required** for physical types: `health_system`, `hospital`, `specialty_center`, `clinic`, `air_ambulance`. **Omitted** (absent, not null/empty) for non-physical types: `physician_group`, `clinic_network`, `program`, `brand`. Unknown types: warn only.
- `addresses` (optional) = additional sites for multi-address entities. Each entry carries the same street/city/state/zip quartet plus an optional `label` (must be unique per entity). Entries must not duplicate the primary `address`.
- `service_area` (optional string) = geographic footprint for entities whose reach is regional rather than fixed-site (e.g. `"WWAMI region"`). The natural counterpart for non-physical entities; also valid alongside a single HQ address (e.g. Airlift Northwest: HQ address + `service_area`).
- Locations that are organizations in their own right (clinics, satellites, provider practices) are modeled as **Tier 3 entities**, never as bare address entries. Address data describes where an entity operates; it does not create entities.

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
hs2/
├── README.md          ← this file (model spec)
├── systems/           ← per health system
│   ├── um-health/
│   │   ├── hierarchy.json
│   │   └── hierarchy.png
│   ├── ur-medicine/
│   │   ├── hierarchy.json
│   │   └── hierarchy.png
│   └── uw-medicine/
│       ├── hierarchy.json
│       └── hierarchy.png
├── server/            ← interactive explorer (FastAPI; renders hierarchy.json directly)
│   ├── app.py         ← /api/systems + /api/hierarchy?system=<id>, all systems
│   └── index.html     ← collapsible tree, typed edges, provenance, search, zoom/pan
└── tools/             ← reusable scripts
    ├── generate_hierarchy.py
    └── validate_hierarchy.py
```

## Status

| Health System | Tiers | Entities | Owns | Manages | Partners | Status |
|---|---|---|---|---|---|---|
| University of Michigan Health | 1,2 | 10 | 8 | 1 | 0 | Validated core |
| UR Medicine | 1,2 | 12 | 5 | 0 | 6 | Validated core |
| UW Medicine | 1,2,3 | 22 | 18 | 1 | 2 | Validated core + clinic network (13 sites) |


---

## Interactive Explorer

The `server/` directory contains a self-contained interactive explorer. It renders directly
from each system's validated `hierarchy.json` — the same data the validator and PNG generator
use, with no separate embedded copy.

```
python3 server/app.py
```

- **Endpoint:** `http://localhost:8646` (bound to 127.0.0.1)
- **API:** `GET /api/systems` → list of systems · `GET /api/hierarchy?system=<id>` → that system's `hierarchy.json`
- **UI:** collapsible tree built from the relationship graph, color-coded edges
  (green=owns, blue=manages, red=partners_with; solid/dashed/dotted per type), dynamic
  legend counts, entity detail panels with full relationship provenance
  (confidence, sources, verified_at), entity search with auto-expand, and zoom/pan
  (wheel, drag, buttons).

---

Built with Qwen 3.6 27B (MTP) running locally via [Hermes Agent](https://github.com/nousresearch/hermes-agent).
