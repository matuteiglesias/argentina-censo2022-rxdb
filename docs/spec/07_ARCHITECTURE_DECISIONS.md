# Architecture Decision Records

## ADR-001 — NUMBER/FREQ is the production backend

Status: **ACCEPTED**

Use:

```text
SELECTION + NUMBER + inherited parent IDs + unique-ID FREQ
```

Reasons:

- genuine record recovery demonstrated;
- exact reaggregation;
- explicit identity/hierarchy;
- compatible across RedEngine 1.1.0 and 1.3.0;
- no binary patch.

## ADR-002 — TABLE VIEW is not a production backend

Status: **ACCEPTED**

Reasons:

- unmodified 1.1.0 limited output to about 101 rows;
- `censo2022arg` required a version-specific binary modification for full extraction;
- RedEngine 1.3.0 reports `VIEW tables are not supported.`

May remain a historical small-sample oracle only.

## ADR-003 — Use native hierarchy

Status: **ACCEPTED**

Use engine-generated entity sequences and inherited parent IDs. Do not infer household/dwelling identity from row order, `TOTPOBV`, or `P01` when native hierarchy is available.

## ADR-004 — Explicit-key batch joins

Status: **ACCEPTED**

Never assemble variable blocks by positional cbind.

## ADR-005 — Generic core + Argentina adapter

Status: **ACCEPTED**

INDEC-specific source/metadata/control logic belongs in the adapter.

## ADR-006 — Parquet is canonical persistence

Status: **ACCEPTED**

Arrow/Parquet is the primary data plane. CSV/SPSS/SAS are optional downstream conversions.

## ADR-007 — Provenance-aware resume

Status: **ACCEPTED**

File existence is insufficient. Checkpoints bind source/query/schema/runtime plus validated output hashes.

## ADR-008 — `@cmpcode` is preferred geography where available

Status: **ACCEPTED WITH CAPABILITY GUARD**

Do not assume it appears in ordinary variable metadata.

## ADR-009 — Processing partition versus identity scope

Status: **OPEN — MUST RESOLVE IN M4**

Preferred:

```text
physical partition = FRAC
canonical identity = RADIO@cmpcode + NUMBER RADIO
```

Requires exact overlap test against RADIO extraction.

## ADR-010 — Native binding technology

Status: **OPEN**

Candidates:

- ctypes;
- cffi;
- pybind11/C++;
- small native executable;
- temporary R subprocess bridge during bootstrap.

Choose based on ABI stability, packaging, Arrow potential, testing and licensing—not taste.

## ADR-011 — Container distribution

Status: **OPEN PENDING LICENSING**

Technically desirable due RedEngine runtime requirements. Bundling engine binaries requires redistribution review.

## ADR-012 — Full person-level data publication

Status: **NOT APPROVED / SEPARATE DECISION**

Local extraction may proceed. Public redistribution requires confidentiality/legal/disclosure assessment.

## ADR-013 — HNVUA

Status: **KNOWN SOURCE/COMPILER DEFECT**

Surface it explicitly, isolate it from other variable batches, retest on corrected source releases, and do not let it block the generic architecture.
