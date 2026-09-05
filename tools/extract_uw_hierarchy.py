#!/usr/bin/env python3
"""Extract the UW Medicine slice from the Epic open-platform Brands Bundle.

Reconstruction of the original pipeline documented in
systems/uw-medicine/uw-medicine-hierarchy-report.md (2026-05-26). The original
script was never committed; this one re-implements its methodology so the
source -> derived chain is re-runnable:

  open.epic.com/Endpoints/Brands (FHIR R4 Bundle)
    -> filter Organizations.partOf == UW Medicine primary brand
    -> classify by naming convention (report section 2.3)
    -> grouped JSON with capture metadata + bundle sha256

Usage:
  python3 tools/extract_uw_hierarchy.py [path/to/bundle.json] [out.json]
"""
import hashlib
import json
import sys
import urllib.request

BUNDLE_URL = "https://open.epic.com/Endpoints/Brands"
UW_BRAND_UUID = "68ff3f69-42cc-4cb7-9dad-1e9cd768e413"

# Naming-convention classification (report section 2.3)
GROUPS = [
    (["HMC", "HARBORVIEW"], "Harborview Medical Center"),
    (["FRED HUTCH", "FRED HUTCHINSON"], "Fred Hutchinson Cancer Center"),
    (["UWMPC"], "UW Medicine Primary Care"),
    (["UWMC NW"], "UW Medical Center - Northwest"),
    (["UWMC ROOSEVELT", "UWMC STADIUM", "UWMC OUTPATIENT", "UWMC MCMURRAY"],
     "UW Medical Center - Montlake"),
    (["UWMC EASTSIDE"], "UW Medical Center - Eastside"),
    (["HALL HEALTH"], "Hall Health Care Center"),
    (["ALASKA"], "UW Medicine Alaska"),
    (["SPOKANE"], "UW Medicine Spokane"),
]


def classify(name: str) -> str:
    up = name.upper()
    for keys, group in GROUPS:
        if any(k in up for k in keys):
            return group
    return "Other UW Medicine Locations"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    bundle_path = sys.argv[1] if len(sys.argv) > 1 else None
    out_path = sys.argv[2] if len(sys.argv) > 2 else \
        "systems/uw-medicine/sources/epic-brands-uw.json"

    if bundle_path is None:
        print(f"downloading {BUNDLE_URL} ...", file=sys.stderr)
        urllib.request.urlretrieve(BUNDLE_URL, "/tmp/epic_brands_bundle.json")
        bundle_path = "/tmp/epic_brands_bundle.json"

    with open(bundle_path) as f:
        bundle = json.load(f)

    entries = bundle.get("entry", [])
    orgs = {}
    endpoints = {}
    for e in entries:
        r = e.get("resource", {})
        rt = r.get("resourceType")
        if rt == "Organization":
            orgs[r.get("id")] = r
        elif rt == "Endpoint":
            endpoints[r.get("id")] = r

    primary = orgs.get(UW_BRAND_UUID)
    if not primary:
        sys.exit(f"UW primary brand {UW_BRAND_UUID} not found in bundle")
    brand_id = next((i["value"] for i in primary.get("identifier", [])
                     if "brand-identifier" in i.get("system", "")), None)
    endpoint = endpoints.get(next(
        (e["reference"].split("urn:uuid:")[1]
         for e in primary.get("endpoint", [])), None))

    ref = f"urn:uuid:{UW_BRAND_UUID}"
    locations = [o for o in orgs.values()
                 if o.get("partOf", {}).get("reference") == ref]

    grouped = {}
    for o in locations:
        name = o.get("name", "(unnamed)")
        addr = (o.get("address") or [{}])[0]
        grouped.setdefault(classify(name), []).append({
            "name": name,
            "uuid": o.get("id"),
            "address": {
                "street": ", ".join(addr.get("line", [])[:2]),
                "city": addr.get("city"),
                "state": addr.get("state"),
                "zip": addr.get("postalCode"),
            },
            "active": o.get("active", True),
        })
    for v in grouped.values():
        v.sort(key=lambda x: x["name"])

    out = {
        "source": {
            "name": "Epic FHIR Brands Bundle (open platform)",
            "url": BUNDLE_URL,
            "bundle_id": bundle.get("id"),
            "last_updated": bundle.get("meta", {}).get("lastUpdated"),
            "total_entries_in_bundle": bundle.get("meta", {}).get(
                "extension", [{}])[0].get("valueDecimal"),
            "sha256_of_full_bundle": sha256_of(bundle_path),
        },
        "brand": {
            "name": primary.get("name"),
            "uuid": UW_BRAND_UUID,
            "epic_brand_identifier": brand_id,
            "fhir_endpoint": endpoint.get("address") if endpoint else None,
            "fhir_endpoint_uuid": endpoint.get("id") if endpoint else None,
        },
        "total_locations": len(locations),
        "groups": {g: {"count": len(v), "locations": v}
                   for g, v in sorted(grouped.items())},
    }

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"extracted {len(locations)} locations "
          f"across {len(grouped)} groups -> {out_path}")


if __name__ == "__main__":
    main()
