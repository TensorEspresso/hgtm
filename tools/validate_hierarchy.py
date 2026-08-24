#!/usr/bin/env python3
"""Validate HS2 hierarchy files against the model spec (README.md).

Usage:
  python3 tools/validate_hierarchy.py <system_dir> [<system_dir> ...]
  python3 tools/validate_hierarchy.py --all

Checks:
  - Entity required fields: id, name, type, tier, note
  - Addressing rules: 'address' required for physical types, omitted for
    non-physical types; 'addresses[]' full quartet, unique labels, no
    duplication of the primary address; 'service_area' string when present
  - Relationship required fields, valid enums, date format, dangling refs,
    self-loops, duplicate edges, note restriction (manages/partners_with)
  - Graph invariants: single tier-0 'health_system' root, no orphans
  - Summary parity: declared counts match actual entity/relationship/tier/
    type/confidence distributions

Exit code 0 = all pass, 1 = any error, 2 = usage error.
"""

import json
import os
import re
import sys

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
REL_TYPES = {'owns', 'manages', 'partners_with'}
CONFIDENCE_LEVELS = {'high', 'medium', 'low', 'inferred'}
PHYSICAL_TYPES = {'health_system', 'hospital', 'specialty_center', 'clinic', 'air_ambulance'}
NON_PHYSICAL_TYPES = {'physician_group', 'clinic_network', 'program', 'brand'}
ADDR_FIELDS = ('street', 'city', 'state', 'zip')


def check_address(addr, ctx, errs):
    """Validate one address object has the full quartet."""
    if not isinstance(addr, dict):
        errs.append(f"{ctx}: address must be an object")
        return
    for f in ADDR_FIELDS:
        if not addr.get(f):
            errs.append(f"{ctx}: address missing '{f}'")


def validate(data):
    errs, warns = [], []
    ents = data.get('entities', [])
    rels = data.get('relationships', [])

    # --- duplicate ids ---
    id_counts = {}
    for e in ents:
        id_counts[e.get('id', '?')] = id_counts.get(e.get('id', '?'), 0) + 1
    dups = [i for i, c in id_counts.items() if c > 1]
    if dups:
        errs.append(f"duplicate entity ids: {dups}")
    emap = {e['id']: e for e in ents if 'id' in e}

    # --- entities ---
    for e in ents:
        eid = e.get('id', '?')
        for f in ('id', 'name', 'type', 'tier', 'note'):
            if f not in e or e[f] in (None, ''):
                errs.append(f"entity {eid}: missing required field '{f}'")

        if not isinstance(e.get('tier'), int) or e['tier'] not in (0, 1, 2, 3):
            errs.append(f"entity {eid}: invalid tier {e.get('tier')!r}")

        t = e.get('type')
        has_addr = 'address' in e and e.get('address')
        if t in PHYSICAL_TYPES:
            if not has_addr:
                errs.append(f"entity {eid}: type '{t}' is physical — 'address' required")
            else:
                check_address(e['address'], f"entity {eid}", errs)
        elif t in NON_PHYSICAL_TYPES:
            if has_addr:
                errs.append(f"entity {eid}: type '{t}' is non-physical — 'address' must be omitted")
        else:
            warns.append(f"entity {eid}: unknown type '{t}' — addressing rules not enforced")
            if has_addr:
                check_address(e['address'], f"entity {eid}", errs)

        # additional addresses (multi-address entities)
        extra = e.get('addresses')
        if extra is not None:
            if not isinstance(extra, list):
                errs.append(f"entity {eid}: 'addresses' must be an array")
            else:
                seen_labels = set()
                for i, a in enumerate(extra):
                    ctx = f"entity {eid} addresses[{i}]"
                    if not isinstance(a, dict):
                        errs.append(f"{ctx}: must be an object")
                        continue
                    check_address(a, ctx, errs)
                    lbl = a.get('label')
                    if lbl:
                        if lbl in seen_labels:
                            errs.append(f"{ctx}: duplicate label '{lbl}'")
                        seen_labels.add(lbl)
                if has_addr:
                    for i, a in enumerate(extra):
                        if isinstance(a, dict) and all(a.get(f) == e['address'].get(f) for f in ADDR_FIELDS):
                            errs.append(f"entity {eid}: addresses[{i}] duplicates primary address")

        sa = e.get('service_area')
        if sa is not None and not isinstance(sa, str):
            errs.append(f"entity {eid}: 'service_area' must be a string")

    # --- relationships ---
    for r in rels:
        key = f"rel {r.get('source')}->{r.get('target')}"
        for f in ('source', 'target', 'relationship_type', 'confidence', 'sources', 'verified_at'):
            if f not in r or r[f] in (None, '') or (f == 'sources' and not r[f]):
                errs.append(f"{key}: missing required field '{f}'")
        if r.get('relationship_type') not in REL_TYPES:
            errs.append(f"{key}: invalid relationship_type {r.get('relationship_type')!r}")
        if r.get('confidence') not in CONFIDENCE_LEVELS:
            errs.append(f"{key}: invalid confidence {r.get('confidence')!r}")
        if r.get('verified_at') and not DATE_RE.match(str(r['verified_at'])):
            errs.append(f"{key}: verified_at {r['verified_at']!r} not YYYY-MM-DD")
        if r.get('source') not in emap:
            errs.append(f"{key}: dangling source")
        if r.get('target') not in emap:
            errs.append(f"{key}: dangling target")
        if r.get('source') == r.get('target'):
            errs.append(f"{key}: self-loop")
        if 'note' in r and r.get('relationship_type') == 'owns':
            warns.append(f"{key}: 'note' on 'owns' (spec: manages/partners_with only)")

    # --- graph invariants ---
    if not ents:
        errs.append("no entities")
    else:
        t0 = [e for e in ents if e.get('tier') == 0]
        if len(t0) != 1:
            errs.append(f"expected exactly one tier-0 root, found {len(t0)}")
        elif t0[0].get('type') != 'health_system':
            errs.append(f"tier-0 root type must be 'health_system', found {t0[0].get('type')!r}")

    connected = set()
    for r in rels:
        connected.add(r.get('source'))
        connected.add(r.get('target'))
    orphans = [e['id'] for e in ents if 'id' in e and e['id'] not in connected]
    if orphans:
        errs.append(f"orphan entities (in no relationship): {orphans}")

    edges = [(r.get('source'), r.get('target'), r.get('relationship_type')) for r in rels]
    dup_edges = sorted({k for k in edges if edges.count(k) > 1})
    if dup_edges:
        errs.append(f"duplicate edges: {dup_edges}")

    # --- summary parity ---
    s = data.get('summary')
    if s:
        at, ac, atier = {}, {}, {}
        for r in rels:
            rt, cf = r.get('relationship_type'), r.get('confidence')
            if rt in REL_TYPES:
                at[rt] = at.get(rt, 0) + 1
            if cf in CONFIDENCE_LEVELS:
                ac[cf] = ac.get(cf, 0) + 1
        for e in ents:
            if isinstance(e.get('tier'), int):
                k = f"tier_{e['tier']}"
                atier[k] = atier.get(k, 0) + 1

        if s.get('total_entities') != len(ents):
            errs.append(f"summary total_entities {s.get('total_entities')} != actual {len(ents)}")
        if s.get('total_relationships') != len(rels):
            errs.append(f"summary total_relationships {s.get('total_relationships')} != actual {len(rels)}")

        def parity(name, declared, actual):
            for k in set(list(declared or {}) + list(actual)):
                if (declared or {}).get(k, 0) != actual.get(k, 0):
                    errs.append(f"summary {name}.{k}: declared {(declared or {}).get(k, 0)} != actual {actual.get(k, 0)}")

        parity('by_relationship_type', s.get('by_relationship_type'), at)
        parity('by_confidence', s.get('by_confidence'), ac)
        parity('tiers', s.get('tiers'), atier)

    return errs, warns


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)

    if args[0] == '--all':
        systems_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'systems'))
        dirs = sorted(os.path.join(systems_root, d) for d in os.listdir(systems_root)
                      if os.path.isdir(os.path.join(systems_root, d)))
    else:
        dirs = args

    failed = False
    for d in dirs:
        p = os.path.join(d, 'hierarchy.json')
        print(f"== {os.path.basename(os.path.normpath(d))} ==")
        if not os.path.exists(p):
            print(f"  ERROR: {p} not found")
            failed = True
            continue
        try:
            with open(p) as f:
                data = json.load(f)
        except Exception as ex:
            print(f"  ERROR: JSON parse failed: {ex}")
            failed = True
            continue

        errs, warns = validate(data)
        n_ent = len(data.get('entities', []))
        n_rel = len(data.get('relationships', []))
        print(f"  {'PASS' if not errs else 'FAIL'} — {n_ent} entities, {n_rel} relationships")
        for e in errs:
            print(f"  ERROR: {e}")
        for w in warns:
            print(f"  warn: {w}")
        if errs:
            failed = True

    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
