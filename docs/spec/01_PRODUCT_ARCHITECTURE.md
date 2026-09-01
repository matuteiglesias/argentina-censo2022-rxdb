# Product and Architecture

## 1. Product definition

The system is a **hierarchical RXDB record extraction platform**. It converts a RedatamX statistical-query database into ordinary relational/columnar data while preserving:

- entity identity;
- parent-child hierarchy;
- source geography;
- stored values and missing-state information exposed by RedEngine;
- source/runtime provenance;
- reproducible validation evidence.

Argentina Census 2022 is the first real adapter and flagship validation corpus, not the definition of the generic product.

## 2. Target users

### Data user

```bash
arg-censo2022 extract /data/censo2022 ./out
```

No REDATAM or R knowledge required.

### Generic RXDB user

```bash
rxdb inspect database.rxdb
rxdb extract database.rxdb --entity PERSONA --output ./out
rxdb validate ./out
```

### Library user

Conceptual Python API:

```python
import rxdb

db = rxdb.open("database.rxdb")
db.entities()
db.variables("PERSONA")
db.extract(entity="PERSONA", selection={"RADIO": "061471101"})
```

## 3. Layering

```text
CLI / Python API / optional future R binding
                    │
                    ▼
       Generic RXDB extraction library
 hierarchy / planner / IDs / batching / validation
 provenance / checkpoints / Parquet contracts
                    │
                    ▼
             RedEngine adapter
      open / inspect / execute SPC / decode
                    │
                    ▼
               RedEngine runtime
                    │
                 RXDB/RBFX
```

Adapter layer:

```text
generic RXDB core
      │
      ▼
Argentina Census 2022 adapter
      ├── VP / PO_A_IG / VC_PSC semantics
      ├── INDEC release provenance
      ├── metadata and labels
      ├── official controls
      ├── geography restrictions
      └── known source anomalies
```

## 4. Production mechanism

The production backend MUST use supported SPC semantics based on:

```text
RUNDEF ...
SELECTION <selectable ancestor> == "<compound code>"

DEFINE <entity>.<own_id> AS NUMBER <identity scope>
DEFINE <child>.<parent_id> AS <parent>.<generated_id>

FREQ <entity>.<own_id>
  BY <entity>.<parent_id>
  BY <stored variables...>
```

The extractor MUST discard frequency margins and retain complete record cells only.

It MUST NOT depend on `TABLE VIEW` and MUST NOT require an on-disk RedEngine patch.

## 5. Core responsibilities

The generic core owns:

- runtime/capability detection;
- database open/close;
- entity/variable inventory;
- entity graph representation;
- selectable-ancestor discovery;
- `SELECTION`, `NUMBER`, inheritance and `@cmpcode` query generation;
- variable batching;
- output normalization;
- explicit-key joins;
- Parquet writing;
- checkpoint/resume;
- validation;
- provenance manifests.

The Argentina adapter owns:

- identifying VP / PO_A_IG / VC_PSC;
- source release history/provenance;
- official controls and metadata;
- INDEC geography/universe semantics;
- cross-base integration;
- HNVUA anomaly policy;
- public aggregate product derivation.

## 6. Non-goals for v1

The project MUST NOT initially:

- directly decode encrypted RBFX storage;
- replace RedEngine;
- emulate the entire SPC language;
- support database creation;
- depend on TABLE VIEW;
- infer household/dwelling hierarchy from P01/TOTPOBV when native hierarchy exists;
- silently flatten unsupported branching entity trees;
- publish full person-level extracted data by default;
- treat a successful file write as proof of a correct extraction.

## 7. Runtime strategy

RedEngine 1.3.0 requires a newer glibc/libstdc++ than the current host and has been reproduced successfully in an isolated container.

Therefore:

- runtime compatibility MUST be checked early;
- containerized execution SHOULD be first-class;
- every dataset manifest MUST record RedEngine/runtime identity;
- bundling RedEngine in distributed images remains conditional on license/redistribution review.

## 8. Quality priorities

1. correctness;
2. reproducibility;
3. provenance;
4. restartability;
5. bounded memory;
6. portability;
7. performance;
8. convenience.

A faster implementation that weakens identity or validation is a regression.

## 9. Exit condition for generic v1

A clean environment can:

- inspect a supported RXDB;
- extract a selected area deterministically;
- produce normalized Parquet with explicit PK/FK relations;
- resume safely after interruption;
- reproduce source counts and selected distributions exactly;
- record source/runtime/query provenance;
- execute from CLI without requiring the user to author R code.
