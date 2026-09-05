# UW Medicine — Data Provenance

Every claim in `hierarchy.json` maps to a source artifact. Raw captures live in
`sources/` (SHA-256 below, verify with `sha256sum -c` or `shasum -a 256`).

## 1. Captured artifacts

| Artifact | URL | Captured | SHA-256 |
|---|---|---|---|
| `sources/epic-brands-uw.json` | https://open.epic.com/Endpoints/Brands (UW Medicine slice; 47 locations, 10 groups) | 2026-09-05 | `e8aea23de0c6250016aeb7bf41317a04843a3143f879aa6d902da9e64aa610e0` |
| `sources/uw-patient-education-neighborhood-clinics.pdf` | https://healthonline.washington.edu/sites/default/files/record_pdfs/Choosing-Provider-Your-Newborn.pdf (UW patient education, clinician review 2020-03) | 2026-09-05 | `e808ad4fd8787f0a579654bde4b71da5b67cc1bb0a8b75bab3eeee864de31f71` |
| `sources/chpw-cascade-select-directory-2026.pdf` | Cascade Select 2026 provider directory (CHPW; ~90k lines text, 2026 edition) | 2026-09-05 | `2795f866b64c670f906a4c6b8c5269bb7a904122c9a74daf9fef1bc063844880` |
| `uw-medicine-hierarchy-report.md` | Original extraction report (2026-06), documents Epic Brands Bundle methodology | — | (in repo, git-tracked) |

Reproduce the Epic slice: `python3 tools/extract_uw_hierarchy.py <full-bundle.json> systems/uw-medicine/sources/epic-brands-uw.json`

Note: the UW Medicine FHIR proxy (`fhir.epic.medical.washington.edu`) now serves Bulk
Data / US Core only — the `Brand` resource 404s (confirmed 2026-09-05). The open
platform Brands Bundle remains the authoritative Epic-side source.

## 2. Entity → source map

| Entity (id) | Membership / relationship | Address | Notes |
|---|---|---|---|
| `uw-medicine-root` | Epic bundle `brand` (uuid `68ff3f69-...`, id 255) | Epic bundle "UW Medicine - Washington" 185 NE Stevens Way (used 1959 NE Pacific St HQ per uwmedicine.org) | brand_id/epic_id/fhir_endpoint carried from bundle |
| `uwmc-montlake` | uwmedicine.org + Wikipedia + Epic bundle (group "UW Medical Center - Montlake") | 1959 NE Pacific St, 98195 | — |
| `uwmc-northwest` | uwmedicine.org + Wikipedia + Epic bundle (group "UW Medical Center - Northwest") | 1550 N 115th St, 98133 | — |
| `harborview` | kingcounty.gov (ownership) + uwmedicine.org + Wikipedia | Epic bundle "Harborview Medical Center - Washington" 325 9th Ave, 98104 | King County owns, UW operates |
| `valley-medical` | seattletimes.com, beckershospitalreview.com (alliance ending 2026-12-31) | 400 S 43rd St, Renton 98055 (web-verified 2026-09-05: yellowpages, solvhealth, vivian, 10times) | Not in Epic bundle (separate PHD-1 system) |
| `fred-hutch` | fredhutch.org + Wikipedia | 1100 Fairview Ave N, 98109 (Epic bundle "Fred Hutch Wellness Center- Arnold Building") | — |
| `airlift-northwest` | newsroom.uw.edu + uwmedicine.org | 6505 Perimeter Rd S Ste 200, 98108 | — |
| `uw-physicians` | uwmedicine.org + NPI registry (web-verified 2026-09-05) | non-physical (omitted per schema) | — |
| `uw-neighborhood-clinics` | 2020 UW roster (13 names+phones) | non-physical; `addresses[]` below | network node |

### Clinic sites (13)

| Site | Membership source | Address source(s) | Address |
|---|---|---|---|
| Ballard (`nc-ballard`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 1455 NW Leary Way Ste 250, 98107 |
| Belltown (`nc-belltown`) | 2020 roster + CHPW 2026 index | CHPW 2026 + web (2026-09-05) | 2505 2nd Ave Ste 200, 98121 |
| Factoria (`nc-factoria`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 13231 SE 36th St Ste 110, Bellevue 98006 |
| Federal Way (`nc-federal-way`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 32018 23rd Ave S, 98003 |
| Fremont (`nc-fremont`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 + web. CHPW lists it as "Primary Care at Fremont" (400 N 34th St Ste 203, phone 206-545-9300 = roster phone) | 459 N 35th St Ste 203, 98103 |
| Issaquah (`nc-issaquah`) | 2020 roster + CHPW 2026 | CHPW 2026 + web | 1740 NW Maple St Ste 100, 98027 |
| Kent–Des Moines (`nc-kent-des-moines`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 23213 Pacific Hwy S, Kent 98032 |
| Mountlake Terrace (`nc-mountlake-terrace`) | Epic bundle + CHPW 2026 + MLTnews 2022-05-11 | all three | 24360 Van Ry Blvd Ste 111, 98043 |
| Northgate (`nc-northgate`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 314 NE Thornton Pl, 98125 |
| Olympia (`nc-olympia`) | **2020 roster only** | web 2026-09-05 (opennpi, 2016 opening article) | 3525 Ensign Rd NE Ste B, 98506 |
| Ravenna (`nc-ravenna`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 4915 25th Ave NE Ste 300, 98105 |
| Shoreline (`nc-shoreline`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 + web. CHPW lists as "UW Physicians Shoreline Clinic" (1355 N 205th St, phone 206-542-5656 = roster phone) | 1355 N 205th St, 98133 |
| Woodinville (`nc-woodinville`) | 2020 roster + Epic bundle | Epic bundle + CHPW 2026 | 17638 140th Ave NE, 98072 |

## 3. The Mountlake Terrace / Lake Forest Park relocation

- The 2020 roster lists "UW Medicine Primary Care at **Lake Forest Park**" (206.668.8272).
- **MLTnews (2022-05-11):** "UW Medicine opened a clinic location this spring at
  24360 Van Ry Blvd., Suite 111... To do so, the organization relocated its Primary
  Care at Lake Forest Park clinic **along with the UW Medicine Heart Institute
  Edmonds** to create [the combined building]."
- The 2026-09-05 Epic bundle and CHPW 2026 directory both list only Mountlake
  Terrace; Lake Forest Park appears in neither.
- → Entity modeled at the current location; note records the relocation. Confidence high.

## 4. Known discrepancies & review queue

1. **`nc-olympia` — downgraded to `medium`.** Absent from both 2026 captures
   (Epic bundle, CHPW directory) though in the 2020 roster. May have closed or
   re-branded under a non-matching name. Keep until confirmed.
2. **Sites in the 2026 captures but NOT modeled** (not in the 2020 roster network;
   tracked here so they aren't "lost" on future updates):
   - **Kirkland** — Epic bundle "UWMPC KIRKLAND" (620 Kirkland Way, 98033) + CHPW 2026 index. Not in the 2020 neighborhood roster; appears to be a newer Primary Care site.
   - **South Lake Union** — Epic bundle "UWMPC SOUTH LAKE UNION" (750 Republican St, 98109) + CHPW 2026 index.
   - **Lopez Island** — Epic bundle only (103 Washburn Place, 98261); small/telehealth-oriented.
   - **Arlington MFM Clinic** — Epic bundle (3823 172nd St NE, 98223); specialty (MFM), not neighborhood network.
   - **Hall Health Care Center** (4060 NE Stevens Way) and **UW Medicine Alaska** (Anchorage transplant clinic) — Epic bundle groups; student-health / WWAMI-satellite, deliberately out of scope for this network model.
3. **UW Physicians Shoreline vs `nc-shoreline`** — same address/phone; CHPW indexes it under UW Physicians. Kept as one neighborhood-network entity (the network is the patient-facing brand); flagged in the site table.
4. **SCCA (Seattle Cancer Care Alliance)** — merged into Fred Hutch April 2022; entity removed in the June 2026 cleanup (git history: pre-`b8c0e6f`).
5. **"UW Tacoma hospital"** — rejected during the 2026-09-05 expansion: 4801 Yakima Ave Tacoma is a provider office; Tacoma hospital ownership is MultiCare/CHI, not UW.
6. **CUMG (Children's University Medical Group)** — rejected: it is Seattle Children's billing group, not a UW Medicine entity.

## 5. Confidence summary

- 19 high / 2 medium (of 21 relationships). The two mediums: `valley-medical`
  (alliance, not ownership — 3 non-authoritative corroborations) and `nc-olympia`
  (roster-only membership, 2026 status unverified).
- No `low`/`inferred` relationships in the current graph.
