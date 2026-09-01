# Delivery Plan and Agent Work Packets

## Delivery principle

Proceed from a thin, completely validated vertical slice to larger-scale orchestration. No milestone may replace correctness evidence with projected performance.

# Milestones

## M0 — Repository and evidence freeze

Deliver:

- implementation repo structure;
- this bundle under `docs/spec/`;
- immutable references to research evidence;
- fixture configuration;
- no speculative production implementation.

## M1 — RedEngine runtime boundary

Implement:

- runtime discovery;
- engine/capability fingerprint;
- open/close;
- `run_spc()` boundary;
- typed runtime errors.

A temporary R subprocess bridge MAY be used, but contracts must permit later native replacement.

Acceptance: one command opens VP, reports current capabilities and runs a known FREQ under the isolated 1.3 runtime.

## M2 — Generic schema/hierarchy inspection

Implement:

- entities;
- variables/aliases;
- selectability;
- entity graph;
- selectable ancestor discovery;
- cmpcode capability.

CLI:

```bash
rxdb inspect Base_VP/cpv2022.rxdb
```

Acceptance: known VP hierarchy reconstructed without `last entity == leaf` logic.

## M3 — Mandatory thin vertical slice

Input:

```text
VP RXDB
RADIO 061471101
```

End-to-end:

```text
discover hierarchy
→ select RADIO
→ cmpcode geography
→ native IDs
→ variable inventory/batches
→ explicit-ID merge
→ VIVIENDA/HOGAR/PERSONA Parquet
→ manifests/checkpoints
→ exact validation
```

Acceptance: every requirement in `04_VALIDATION_TEST_SPEC.md`, including 73/56/137 counts, PK/FK integrity, household sizes, exact reaggregation, deterministic rerun, interruption/resume and corruption detection.

**No national orchestration before M3 passes.**

## M4 — Identity-scope qualification + FRAC slice

Target FRAC `0614711`.

Test:

```text
physical selection = FRAC
canonical identity = RADIO@cmpcode + NUMBER RADIO
```

Acceptance:

- 130/72/173 counts;
- overlapping records extracted by RADIO and FRAC receive identical canonical keys;
- no collisions.

Freeze v1 key contract after M4.

## M5 — Batch/memory engine

Implement configurable variable batching, disposable worker isolation where needed, Arrow/Parquet staging and explicit-ID joins.

Benchmark widths 1/3/5/8/10 on permanent fixtures and representative FRAC sizes.

Acceptance: bounded memory and deterministic logical output.

## M6 — CLI + production resume

Implement:

```bash
rxdb inspect
rxdb extract
rxdb validate
```

plus workers, partition discovery, progress, provenance-aware resume and atomic success markers.

Acceptance: kill/restart multi-partition run yields exact clean-run equivalence; stale checkpoints invalidate.

## M7 — Argentina VP adapter

Implement source discovery, release manifest, metadata, controls, HNVUA status, output layout and province/national validation.

## M8 — PO and VC adapters

Separate bounded workstreams.

### PO rule

No positional cbind. Identity must be demonstrated.

### VC rule

Entity/universe semantics must be explicit; do not label dwelling rows as persons.

## M9 — National readiness

Before full extraction freeze:

- source release;
- runtime/container;
- batch width;
- worker count;
- disk budget;
- checkpoint audit;
- failure-recovery drill;
- validation sampling/reaggregation policy.

Then launch the national run.

## M10 — Release/publication layer

Potentially release separately:

- generic extractor;
- Argentina adapter;
- public aggregate census cube;
- technical/software paper.

Full person-record redistribution remains a separate governance decision.

# Bounded agent work packets

## WP-01 — Repo skeleton/interfaces

Create modules and typed interfaces for runtime, schema, planner, writer, validator. No extraction implementation.

## WP-02 — Runtime probe

Implement RedEngine 1.3 runtime/capability detection and `run_spc()` boundary. Verify TABLE VIEW unsupported as expected.

## WP-03 — Entity graph

Generic schema inspection and hierarchy representation. Reject ambiguous unsupported topology rather than guessing.

## WP-04 — SPC planner

Generate deterministic selection, NUMBER, inherited IDs and cmpcode definitions. Golden query-generation tests.

## WP-05 — FREQ normalizer

Convert raw FREQ output to records using masks; enforce count=1 and unique IDs; test margins/missing states/failures.

## WP-06 — M3 vertical slice executor

Integrate WP-02..05 for VP RADIO 061471101 only. Produce three Parquets + manifests + validation. Do not widen scope.

## WP-07 — Validation engine

Implement PK/FK, counts, household sizes, exact reaggregation and semantic dataset fingerprint.

## WP-08 — Checkpoint/resume

Implement source/query/schema/runtime-aware checkpoints and atomic completion. Tests for kill/restart/stale/corrupt states.

## WP-09 — FRAC identity experiment

Answer whether RADIO-relative canonical identity remains stable under FRAC physical selection. Deliver evidence + ADR update.

## WP-10 — Batch-width/memory study

Benchmark widths and recommend production default. No semantic changes.

## WP-11 — Arrow/Parquet writer

Canonical schema/order/compression/partition metadata; avoid whole-wide-table accumulation.

## WP-12 — CLI

Build `inspect`, `extract`, `validate` on stable library contracts.

## WP-13 — Container/runtime

Pinned current-engine execution environment, health probe, provenance and licensing note.

## WP-14 — Argentina VP adapter

Source discovery, release metadata, controls, HNVUA policy; use generic core only.

## WP-15 — PO identity study

Evaluate explicit/reproducible cross-base identity. Reject row-order linkage as production policy.

## WP-16 — VC semantics/adapter

Map true hierarchy/universes and produce correctly named entity outputs.

## WP-17 — Public aggregate product

Downstream transformation only:

```text
geo × entity × variable × category × count
```

No changes to extraction semantics.

# Agent handoff template

Every agent returns:

```text
Scope completed
Files changed
Tests run
Evidence
Known gaps
Risks
Recommended next work packet
```

An agent MUST NOT claim DONE without executing the acceptance tests relevant to its packet.

# Collision policy

After M3, these can safely advance in parallel:

```text
runtime/native binding
CLI
manifest/schema
validation
Argentina metadata
container
user documentation
```

Avoid multiple agents simultaneously editing the extraction planner or canonical ID contract before M4 freezes those interfaces.
