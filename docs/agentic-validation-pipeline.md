# Agentic Web Validation Pipeline — Design Document

**Project:** HS2 (Hierarchical Structure of Health Systems)
**Status:** Design — pre-build
**Stack:** Firecrawl (web retrieval), Databricks (storage + orchestration), LLM via Databricks Model Serving endpoints
**Scope:** Validate the elements of healthcare data entities (hospitals, specialty centers, clinics, and the relationships between them) against live web sources, with full evidence replay.

---

## 1. Problem Statement

HS2 maintains a typed graph of US health system hierarchies (tiers: system → hospital → specialty center → clinic; relationship types: `owns` / `manages` / `partners_with`; confidence: `high` / `medium` / `low` / `inferred`). Data was built by research and is now static. We need a repeatable, auditable pipeline that:

1. Takes in an entity (and its relationships) from the gold dataset.
2. Validates each element against live web sources.
3. Returns per-element verdicts with **citable evidence** (verbatim span + URL + fetch timestamp).
4. Updates entity confidence and surfaces contradictions for human review.
5. Optionally *adds* relationships the graph is missing (e.g., a partnership discovered during validation).

## 2. Core Principles

1. **The agent never judges from its own knowledge.** It retrieves, extracts, and cites. Every `confirmed` verdict must carry a verbatim span from a retrieved page. No span → `inconclusive`, never `confirmed`.
2. **Absence of evidence is not evidence of absence.** `not_found` (positive evidence something is gone) is a different state from `inconclusive` (we couldn't tell) and a different state from `blocked` (source inaccessible).
3. **A contradiction is usually a missing relationship type, not a data error.** `owns`/`manages`/`partners_with` are not mutually exclusive at the same address. Cross-domain hits get re-queued for relationship-language classification, not flagged as errors.
4. **Deterministic where possible, LLM only for judgment.** Registry lookups (NPI/CMS) are the ground-truth fast path; deterministic string normalizers decide exact matches; LLMs are invoked only where language understanding is genuinely needed (query formulation, source relevance, non-exact match judgment, relationship-language classification).
5. **Everything is replayable.** Any gold field must be traceable to the exact page content as of fetch time.

## 3. Input Model

Entity fields (HS2 schema): `id, name, type, tier, address, addresses, service_area, brand_id, epic_id, fhir_endpoint, note`.
Relationship fields: `source, target, relationship_type, confidence, sources, verified_at, note`.

### Worked example (real data, `um-health/hierarchy.json`)

```json
{
  "id": "frankel-cvc",
  "name": "Frankel Cardiovascular Center",
  "type": "specialty_center",
  "tier": 2,
  "address": {"street": "1425 E Ann Street", "city": "Ann Arbor", "state": "MI", "zip": "48109"},
  "note": "350,000 sq ft cardiovascular center. Housed within University Hospital complex."
}
```

Relationship: `university-hospital owns frankel-cvc`, confidence `high`.

## 4. Pipeline Overview

```
Entity (gold, Databricks)
  └─ Stage 0: Claim decomposition (deterministic + LLM)
  └─ Stage 1: Fast path — tier-1 registry lookups (deterministic, no web)
  └─ Stage 2: Agent loop per claim (Firecrawl search → select → scrape → judge → replan)
  └─ Stage 3: Aggregation (rules table, not LLM) → entity confidence
  └─ Stage 4: Write bronze/silver/gold (Databricks)
```

### Stage 0 — Claim Decomposition

Split the entity into **testable claims**, one per element, each with a verifiability class:

| # | Claim | Class | Fast path? |
|---|---|---|---|
| C1 | `name` is a real, operating entity | existence | ✓ Care Compare / NPPES |
| C2 | `address` matches published location | location | ✓ if listed in registry |
| C3 | `type`/`tier` classification is correct | classification | ✗ — verify underlying facts, map to taxonomy by rules |
| C4 | Factual assertions in `note` (e.g., "housed within University Hospital complex") | note-claim | ✗ |
| C5 | Relationship edges attached to the entity | relationship | ✗ — hardest class |

Rules:
- **Taxonomy is never verified against the web directly.** `type=specialty_center` is an internal taxonomy. The pipeline verifies underlying facts (standalone vs. in-hospital, service mix, size) and maps to tier via a deterministic rules table. The LLM does not touch the taxonomy.
- **Claims share retrieval.** C1, C2, and C4 can be settled by one page. Retrieval is deduplicated by (entity, source_url); claims are resolved against a shared evidence cache.
- LLM use in this stage: generating `note`-claims from free text (C4) and relationship-language extraction for C5. Element→claim mapping for name/address/type is deterministic.

### Stage 1 — Fast Path (deterministic, zero LLM, zero web credits)

Tier-1 registry lookups before any web work:

- **NPI registry / NPPES:** existence, legal name, practice location, taxonomy.
- **CMS Care Compare:** existence, address, phone, website. Hospitals additionally cross-check **CCN** (CMS Certification Number) — a strong existence signal no website can provide.
- Registry results are **ground truth** for the elements they cover. A website contradicting NPPES is the website that's wrong.
- If the fast path fully confirms a claim (e.g., NPPES address == gold address after normalization), the claim is `confirmed` at tier 1 and the web agent is never invoked for it.
- If the fast path returns nothing (e.g., a specialty center not separately licensed), the claim falls through to Stage 2. This is normal, not a failure.

### Stage 2 — Agent Loop

The agentic part. Three LLM calls per claim round:

**Call A — Query planning.**
Input: claim + entity context + previously tried queries and their failures. Output: 2–3 query formulations with deliberate variation (exact-match address, name+city, paraphrased) plus a source preference list. The planner's job is formulation diversity, not cleverness — the failure mode being fought is "searched once, found nothing, concluded doesn't exist."

```json
{
  "queries": [
    "\"Frankel Cardiovascular Center\" \"1425 E Ann Street\"",
    "\"Frankel Cardiovascular Center\" Ann Arbor location",
    "Frankel CVC University Hospital complex Ann Arbor"
  ],
  "source_preference": ["official_site", "system_site", "press"]
}
```

**Call B — Source selection.**
Firecrawl `/search` returns ~10 URLs with titles/snippets. The LLM scores each by:
- **Trust class** (deterministic `trust_class` computed upstream — not an LLM guess; see §6)
- **Snippet relevance to this specific claim**

Output: top 3 URLs + per-page instructions ("find the address block", "find ownership/partnership language"). Zero URLs passing the tier filter → claim goes `inconclusive`, no scrape.

**Call C — Evidence judgment.**
Firecrawl `/scrape` with a **JSON schema** returns structured facts + a `verbatim_quotes` array. Relationship claims (C5) use a different schema: `ownership_language, partnership_language, parent_organization, rebrand_history, verbatim_quotes` instead of `address/phone`.

```json
{
  "page_title": "Frankel Cardiovascular Center - University of Michigan",
  "street_address": "1425 E Ann Street, Ann Arbor, MI 48109",
  "parent_organization": "University of Michigan Health",
  "verbatim_quotes": ["The Frankel Cardiovascular Center is located at 1425 E Ann Street, on the University Hospital campus in Ann Arbor."]
}
```

The judgment LLM outputs a verdict record:

```json
{
  "claim_id": "C2",
  "verdict": "confirmed",
  "evidence_span": "The Frankel Cardiovascular Center is located at 1425 E Ann Street",
  "source_url": "https://cvc.med.umich.edu/...",
  "source_tier": 2,
  "match_quality": "exact"
}
```

**The discipline that makes this trustworthy:**
- `evidence_span` **must be a verbatim substring** of the scraped content. A pure-Python post-processor asserts this. A `confirmed` whose span isn't found on the page is downgraded to `inconclusive` and the run flagged. This converts LLM hallucination from silent data poisoning into a caught anomaly.
- **Deterministic matcher first.** If the normalizer (whitespace, case, "E" vs "East", "St" vs "Street", suffixes) decides `exact`/`mismatch`, Call C is skipped entirely — no LLM, no tokens. LLM judgment only runs where the deterministic matcher can't decide.
- `match_quality` is part of the verdict: `exact` (normalizable string match) vs `semantically_equivalent` (LLM-judged).

**Replan loop (what makes it agentic):**

```
searching → extracting → judged
                      ├─ confirmed / contradicted → done
                      ├─ inconclusive & replans < 2 → back to Call A, with prior attempts + failures in context
                      └─ inconclusive & replans = 2 → final: inconclusive
```

Round-2 context example: *"Round 1: 'Frankel Cardiovascular Center Ann Arbor location' → top results were an Ohio facility and a directory listing; no address found."* Hard cap of 2 replans. Then `inconclusive` is the honest answer.

**Per-claim caps:** 3 queries, 3 page scrapes. Cache by URL+day.

### Stage 3 — Aggregation (rules, not LLM)

Per-element verdicts roll up via a deterministic policy:

| Evidence condition | Element verdict |
|---|---|
| ≥1 tier-1 source confirms | `confirmed` (registry) |
| ≥2 independent tier ≤2 sources confirm | `confirmed` |
| 1 tier ≤2 source confirms | `confirmed` (single-source — flagged) |
| Tier 3 sources only, consistent | `plausible` |
| Tier 4 only or contradictory tiers | `inconclusive` |
| Any tier-1 source contradicts | `contradicted` → entity-level `disputed`, human queue |
| Source returned 403/bot-wall | `inconclusive_with_reason=blocked` (distinct state; never `not_found`) |

Mapping to the existing HS2 confidence scale:

| HS2 confidence | Meaning |
|---|---|
| `high` | all claims confirmed by ≥1 tier-1 source, or ≥2 tier-2 |
| `medium` | confirmed, but tier 2/3 only, or single-source |
| `low` | `plausible` — consistent but below bar |
| `inferred` | `inconclusive` — **never delete; flag for review** |

Contradiction with any tier-1 source short-circuits: entity status = `disputed`, routed to human review with the full evidence set.

### Stage 4 — Databricks Layout

```
bronze/raw_evidence     {run_id, entity_id, claim_id, url, fetched_at, http_status, firecrawl_job_id, content_md}
                         — every scrape, immutable. The audit substrate.
silver/claim_verdicts   {run_id, entity_id, claim_id, element, verdict, evidence_span, source_url,
                         source_tier, match_quality, n_sources, model, prompt_version}
silver/entity_confidence{run_id, entity_id, field_confidence MAP<element, verdict>, overall_confidence,
                         contradicted_fields ARRAY, new_relationship_candidates ARRAY}
gold/entities           — HS2 schema. Updated only on verdicts. Every field carries the run_id that last validated it.
```

**Replay property:** anyone disputing a gold field drills down to `bronze.raw_evidence` by (entity_id, url, fetched_at) and sees the exact page content. This is what makes the pipeline defensible to compliance-minded stakeholders.

**Hallucination audit test (CI):** for every `confirmed` in `silver.claim_verdicts`, assert `evidence_span ∈ bronze.content_md` for the referenced URL. Any failure is a pipeline bug, not a data finding.

## 5. Firecrawl Usage (v2 API)

| Endpoint | Role in pipeline |
|---|---|
| `POST /v2/search` | Discovery in Call B. One call per query formulation. |
| `POST /v2/scrape` | Extraction in Call C. Pass a JSON schema (OpenAI tool-schema style) to get structured facts + verbatim quotes instead of raw markdown. |
| `POST /v2/map` | Discover all URLs on a domain. |
| `POST /v2/crawl` | **System-site pattern:** a health system = 20+ entities sharing one domain. Map/crawl the system site once, cache the corpus, validate all child entities against it. Biggest credit saver for clinic-tier validation (near-zero marginal cost per entity). |

Budget: ~2–5 credits per claim. Caps + URL/day caching + the system-site corpus pattern keep per-system runs bounded.

## 6. Source Trust

**Superseded by the legal-entity judge v2 trust model** (`legal-entity-judge.md`): the maintained domain→tier config table does not scale to a national collection. The current model uses a deterministic `trust_class` — `gov` / `own_site` / `aggregator` / `unclassified` — computed upstream with a tiny stable allowlist/blocklist, LLM structural judgment (trust-by-structure, never content self-certification) on the unclassified long tail, and convergence-based confidence (independent registrable domains, no tier arithmetic). Build against the judge doc.

Retired tier table (kept for the historical worked example in §7):

| Tier | Sources | Handling |
|---|---|---|
| 1 | NPI registry / NPPES, CMS Care Compare, state licensing boards, IRS | Deterministic match, no LLM. **Overrides all lower tiers.** |
| 2 | Official org website (locations/about/press), health-system org charts, medschool/faculty pages | High trust. 1 source = confirmed (single-source flag); 2 independent = clean confirm. |
| 3 | Press releases, trade media, credible directories | Medium. Requires corroboration to confirm. |
| 4 | Aggregators, Yelp, social, chamber-of-commerce directories | Corroboration only. **Never sole evidence for a `confirmed`.** |

Rules:
- Domain trust is a **maintained config table** (domain → tier), not an LLM guess.
- **Relationship-language override:** when a tier-2 domain that is *not* the owning system's domain lists an entity, the result is **not** `contradicted` — it is re-queued for relationship-language extraction (C5 schema). Without this rule, validation on systems with real joint ventures generates false alarms (see §7).
- Snippet-level evidence counts as evidence, with the URL's tier, when full-page scrape is blocked — but a `confirmed` from snippets alone requires ≥2 independent domains converging.

## 7. Worked Example — Live Pass on Frankel Cardiovascular Center (C2, address claim)

A real validation run (2026-08-19) surfaced the pipeline's two hardest design problems in one claim.

**Search** (`"Frankel Cardiovascular Center" "1425 E Ann Street" Ann Arbor`) returned:

| URL | Tier | Signal |
|---|---|---|
| `trinityhealthmichigan.org/location/frankel-cardiovascular-center` | 2 | Address `1425 E Ann St, Ann Arbor, MI 48109` present — **on a different health system's domain** |
| `uofmhealth.org/locations-list/frankel-cardiovascular-center` | 2 | Address present, owning system's site — **blocked by Cloudflare bot-wall** |
| `medschool.umich.edu/facility/samuel-jean-frankel-cardiovascular-center` | 2 | Address in search snippet |
| `chamberofcommerce.com/business-directory/...` | 4 | Full address in search snippet |

**The naive-failure mode:** a pipeline that sees `trinityhealthmichigan.org → "1425 E Ann St"` fires `contradicted`: "gold says UM owns Frankel, but Trinity lists it as a Trinity location." This is a **false contradiction**.

**The correct handling (two mechanisms):**
1. *Framing extraction.* The Trinity page is a minimal location card (name/address/phone, ~2.1K chars, no ownership claim). Searching its context reveals the actual relationship: *"The Cardiovascular Network of West Michigan, a **joint operating agreement between Trinity Health and University of Michigan Health-West**, leverages … Michigan Medicine's Frankel Cardiovascular Center"* — same wording across three independent tier-2 sources (uofmhealthwest.org, trinityhealthmichigan.org press release, cvnetworkwmi.org). So `owns` is intact, and the Trinity listing is **evidence of a `partners_with` edge the graph doesn't yet contain**. The pipeline adds a candidate relationship; it does not flag a data error.
2. *Blocked-source recovery.* The best source (uofmhealth.org) returned a Cloudflare challenge → that URL's verdict is `inconclusive_with_reason=blocked`, never `confirmed`/`not_found`. C2 still lands `confirmed` because two **independent** domains' snippets (tier-2 search snippet + tier-4 directory) both contain the verbatim full address `1425 E Ann St, Ann Arbor, MI 48109`. Convergence, not a single strong source, decides it.

**Takeaways baked into the design:**
- Location/existence claims are cheap and high-signal (1 search, tier-rank, corroborate, cite; ~2 credits).
- Relationship claims need *framing* (ownership/partnership language), not just *facts* — a different extraction schema per claim class.
- Cross-domain hits → relationship-language classification, never automatic contradiction.
- `blocked` is a first-class verdict state.

## 8. Orchestration

- **Databricks Workflows** drive a Python job per batch of entities.
- The agent loop is a **plain Python state machine** (claim → searching → extracting → judged → replan|done), ~200 lines. No heavy agent framework — the agentic surface is query replanning and source selection.
- LLM calls go through **Databricks Model Serving** endpoints (keeps everything in one billing/audit domain; pin `model` + `prompt_version` in every verdict row).
- Fan out per **claim**, not per entity; entities with shared evidence reuse the retrieval cache.
- Per-system run order: (1) crawl/map the system's own site once, (2) fast-path all registry-covered claims, (3) agent-loop the remainder, (4) aggregate, (5) write.

## 9. Open Design Decisions

1. **Verdict taxonomy final form:** 5 states (`confirmed / plausible / contradicted / inconclusive / not_found`) + `inconclusive_with_reason=blocked`. Confirm the mapping to `high/medium/low/inferred` above.
2. **Re-validation cadence:** what triggers a re-run? (Address change detected, confidence below threshold, periodic drift check on tier-2 entities, new relationship candidate surfaced.)
3. **Stale-evidence policy:** max age for a page to count as "current". Licensing-board and directory sites go stale silently.
4. **Relationship candidate queue:** new edges surfaced during validation (like the Trinity `partners_with` case) — auto-insert at `inferred` + human review, or hold for a batch review?
5. **Blocked-source escalation:** retry with a different fetch path (Firecrawl's own rendering vs. fallback browser) before declaring `blocked`?

## 10. Suggested Build Sequence

**v1 (mechanical, ~80% of entity count):**
- Claim decomposition for `name` / `address` / existence.
- NPI/Care Compare fast path.
- Agent loop with search → tier-rank → scrape → deterministic matcher → LLM judgment only on non-exact matches.
- Bronze/silver/gold tables + the hallucination audit test in CI.
- Test corpus: all 10 `um-health` entities (ground truth already in the repo).

**v2 (where the graph improves, not just confirms):**
- Relationship-language extractor (C5) with the `partners_with` classifier and cross-domain re-queue rule.
- System-site crawl/caching pattern for multi-entity domains.
- New-relationship candidate queue.

## Appendix A — Verdict Record Schema (silver.claim_verdicts)

```json
{
  "run_id": "2026-08-19T18:30:00Z-a1b2",
  "entity_id": "frankel-cvc",
  "claim_id": "C2",
  "element": "address",
  "verdict": "confirmed",
  "match_quality": "exact",
  "evidence_span": "1425 E Ann St, Ann Arbor, MI 48109",
  "source_url": "https://www.trinityhealthmichigan.org/location/frankel-cardiovascular-center",
  "source_tier": 2,
  "n_sources": 2,
  "corroborating_urls": ["https://www.chamberofcommerce.com/..."],
  "model": "qwen-27b",
  "prompt_version": "judge-v3"
}
```

## Appendix B — Query Plan Schema (Call A output)

```json
{
  "claim_id": "C5",
  "entity_id": "frankel-cvc",
  "round": 1,
  "queries": [
    "\"Frankel Cardiovascular Center\" \"University of Michigan\" owns OR affiliated",
    "\"Frankel Cardiovascular Center\" partnership OR joint venture Trinity"
  ],
  "extraction_focus": "ownership_language, partnership_language, parent_organization",
  "prior_rounds": []
}
```

## Appendix C — Key Sources

- Firecrawl v2 API (search / scrape / map / crawl, JSON-schema extraction): https://docs.firecrawl.dev — verify current endpoints before build.
- NPPES / NPI registry (CMS): weekly bulk file + lookup.
- CMS Care Compare (provider/organization lookup, CCN for hospitals).
- HS2 gold data: `~/projects/hs2/systems/<system>/hierarchy.json`.
