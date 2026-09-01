# RXDB Extractor + Argentina 2022 Adapter — Specification Bundle

Status: development specification  
Date: 2026-09-01

## Purpose

This bundle turns the completed feasibility research into a methodical development program for two related products:

1. **Generic RXDB extractor** — a language-neutral extractor/CLI for hierarchical RedatamX `.rxdb` databases.
2. **Argentina Census 2022 adapter** — the first flagship adapter, containing INDEC-specific sources, metadata, controls, geography, validation and release provenance.

The generic core MUST NOT contain Argentina-specific assumptions. The Argentina adapter MUST NOT reimplement RedEngine mechanics that belong in the core.

## Evidence already established

The design starts from reproduced experiments, not hypotheses:

- official VP counts reproduce exactly: 17,783,029 VIVIENDA, 15,932,302 HOGAR, 45,618,787 PERSONA;
- `SELECTION` at RADIO/FRAC prunes efficiently;
- `NUMBER` provides deterministic partition-relative entity identity;
- parent-generated sequences can be inherited by children;
- a unique `NUMBER` dimension in `FREQ` yields one complete non-margin cell per underlying record;
- keys, FKs, household sizes and selected source distributions have been exactly reproduced;
- RedEngine 1.3.0 preserves the supported extraction path;
- `ENTITY@cmpcode` is available in 1.3.0 and yields stable geographic redcodes;
- `TABLE VIEW` is unavailable in 1.3.0 and is not a production backend;
- `PERSONA.HNVUA` remains a known dictionary/compiler ambiguity;
- a resumable FRAC proof already writes Parquet, hashes and `_SUCCESS`.

## Product thesis

> Reproducible, provenance-first extraction of relational records from modern hierarchical RXDB databases using supported RedEngine query semantics, without requiring users to write R or patch RedEngine binaries.

Production primitive:

```text
SELECTION + NUMBER + inherited parent NUMBER + unique-ID FREQ
```

## Mandatory first milestone

Before broad development, prove one thin end-to-end slice:

```text
one RXDB
→ discover hierarchy
→ select RADIO 061471101
→ assign canonical geography + native IDs
→ extract VIVIENDA/HOGAR/PERSONA in batches
→ write Parquet
→ generate manifests/checkpoints
→ validate PK/FK/counts and exact reaggregation
```

Expected fixture counts:

```text
VIVIENDA 73
HOGAR    56
PERSONA  137
```

No national extraction work should precede this milestone.

## Bundle map

- `01_PRODUCT_ARCHITECTURE.md` — product boundaries and target architecture.
- `02_GENERIC_EXTRACTOR_SPEC.md` — normative generic extractor contract.
- `03_ARG2022_ADAPTER_SPEC.md` — normative Argentina adapter contract.
- `04_VALIDATION_TEST_SPEC.md` — permanent fixtures, invariants and acceptance tests.
- `05_DATA_CONTRACTS.md` — canonical keys, schemas, manifests and checkpoints.
- `06_DELIVERY_AND_AGENT_PLAN.md` — milestones plus bounded agent work packets.
- `07_ARCHITECTURE_DECISIONS.md` — accepted and open ADRs.
- `08_RELEASE_GOVERNANCE.md` — software/data release boundaries.
- `COMBINED_SPEC.md` — single-file concatenated version.

`MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` are normative.
