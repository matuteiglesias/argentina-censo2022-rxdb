# Generic RXDB Extractor — Normative Specification

## 1. Scope

Convert supported hierarchical `.rxdb` databases into validated relational Parquet datasets.

The first implementation MAY temporarily use an R subprocess as the RedEngine bridge, but the public architecture MUST remain CLI/library centered and allow a later native C/C++/Python binding without changing extraction contracts.

## 2. Runtime capabilities

At startup detect and record:

- RedEngine version;
- binding/wrapper version;
- OS and architecture;
- runtime compatibility;
- support for `SELECTION`;
- `NUMBER`;
- inherited DEFINEs;
- `FREQ`;
- `ENTITY@cmpcode`;
- masks/labels exposed by the selected binding.

Capabilities MUST be explicit, e.g.:

```json
{
  "redengine_version": "1.3.0-final",
  "selection": true,
  "number": true,
  "inherited_define": true,
  "freq": true,
  "cmpcode": true,
  "table_view": false
}
```

Launch-critical missing capabilities are fatal.

## 3. `rxdb inspect`

Inspection MUST emit:

- source path and hashes;
- engine identity;
- entities;
- aliases;
- variables;
- variable aliases;
- selectable status;
- parent-child graph;
- candidate record entities;
- selectable ancestors for each record entity;
- runtime warnings.

No extraction should be required to inspect the schema.

## 4. Entity graph

Internal model:

```text
Entity
- name
- alias
- parent
- children[]
- selectable
- variables[]
```

The generic implementation MUST NOT use `last entity == leaf` as its algorithm.

Unsupported branching topologies MAY be explicitly rejected in v1, but never silently flattened.

## 5. Selection

The planner MUST prefer engine `SELECTION` over equivalent `FILTER` conditions when selecting a geographic/ancestor partition.

Initial supported physical partitions SHOULD be RADIO and FRAC.

## 6. Geography via `@cmpcode`

When capability-tested, the extractor SHOULD generate source geography using `ENTITY@cmpcode`.

Example:

```text
DEFINE PERSONA.XPROV AS PROV@cmpcode TYPE STRING SIZE 16
DEFINE PERSONA.XDPTO AS DPTO@cmpcode TYPE STRING SIZE 16
DEFINE PERSONA.XFRAC AS FRAC@cmpcode TYPE STRING SIZE 16
DEFINE PERSONA.XRADIO AS RADIO@cmpcode TYPE STRING SIZE 16
```

Do not assume `@cmpcode` appears in `redatam_variables()` metadata.

## 7. Record identity

Every record MUST expose:

- deterministic own sequence;
- deterministic relevant parent sequences;
- source geography sufficient to construct a global key;
- documented identity scope.

Preferred global-key concept:

```text
<identity-scope cmpcode>:<entity sequence>
```

### Required qualification before freezing v1

Test whether a FRAC physical selection can still use RADIO-relative identity:

```text
physical partition = FRAC
identity scope      = RADIO
```

If `NUMBER RADIO` correctly resets per RADIO and pairs with inherited `RADIO@cmpcode`, canonical IDs SHOULD be radio-relative and independent from processing partition.

If not, identity scope MUST be explicit in the manifest and another stable contract chosen.

## 8. Native hierarchy generation

For a chain like RADIO > VIVIENDA > HOGAR > PERSONA the planner should generate equivalent logic to:

```text
DEFINE VIVIENDA.XVID AS NUMBER <scope>

DEFINE HOGAR.XHID AS NUMBER <scope>
DEFINE HOGAR.XVID AS VIVIENDA.XVID

DEFINE PERSONA.XPID AS NUMBER <scope>
DEFINE PERSONA.XHID AS HOGAR.XHID
DEFINE PERSONA.XVID AS VIVIENDA.XVID
DEFINE PERSONA.XPINH AS NUMBER HOGAR
```

Names MUST be collision-safe and planner-generated.

## 9. FREQ record normalization

A record batch MUST include a unique own-ID dimension.

Retain only complete non-margin cells according to engine masks.

For every retained cell require:

```text
count == 1
```

Fatal conditions:

- duplicate own ID;
- missing own ID;
- unexpected non-unit count;
- unexpected margin state;
- row-count disagreement with an independent engine count.

## 10. Variables and batching

The extractor MUST:

- inventory stored variables;
- detect name/alias ambiguity;
- divide variables into bounded batches;
- repeat stable entity IDs in every batch;
- merge batches by explicit key;
- never rely on identical row position.

Batch width is configurable and selected empirically.

## 11. Batch merge

Require:

- identical key sets;
- no duplicates;
- no unexpected missing keys;
- collision-free column names;
- deterministic output schema.

For large data use Arrow/DuckDB/Parquet joins rather than materializing the full wide table in R/Pandas memory.

## 12. Missing states

The canonical representation SHOULD preserve the value plus mask/missing-state information exposed by FREQ.

Frequency margins MUST never be mistaken for source missing values.

## 13. Output

Canonical persistence: Parquet.

Suggested layout:

```text
output/
  VIVIENDA/
  HOGAR/
  PERSONA/
  source-manifest.json
  dataset-manifest.json
  validation.json
```

CSV/SPSS/SAS are optional downstream exports, not canonical storage.

## 14. Checkpoints

A valid completed partition MUST bind:

```text
source hash
schema hash
query/planner hash
runtime fingerprint
entity
selection entity/code
expected rows
actual rows
output hash
validation status
```

Only write `_SUCCESS` atomically after all required validation passes.

File existence alone MUST NOT imply completion.

## 15. Resume

On restart:

- valid checkpoints MAY be skipped;
- changed source/query/schema/runtime contracts MUST invalidate stale checkpoints;
- partial files MUST be recomputed;
- corrupted outputs MUST be detected.

## 16. CLI target

```bash
rxdb info
rxdb inspect <database.rxdb>
rxdb extract <database.rxdb> --entity <ENTITY> --output <PATH>
rxdb validate <PATH>
```

Initial options:

```text
--selection RADIO=...
--partition RADIO|FRAC
--batch-width N
--variables ...
--workers N
--resume
--validation-level structural|counts|reaggregate|full
```

## 17. Python target API

Conceptual:

```python
db = rxdb.open(path)
schema = db.inspect()
db.extract(...)
rxdb.validate(output)
```

CLI and Python MUST share the same planner/executor contracts.

## 18. Typed errors

Distinguish at least:

- incompatible runtime;
- missing engine capability;
- DB open failure;
- schema/topology ambiguity;
- SPC compile failure;
- variable ambiguity;
- identity failure;
- validation failure;
- output corruption;
- checkpoint mismatch.
