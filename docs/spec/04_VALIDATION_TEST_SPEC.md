# Validation and Test Specification

## 1. Philosophy

Validation is a product feature. A partition is complete only when identity, hierarchy, counts, schema, provenance and selected source-equivalence checks pass.

## 2. Test pyramid

### A. Pure unit tests — no RedEngine

Test:

- entity graph;
- hierarchy planner;
- variable batching;
- query generation;
- margin/mask filtering;
- ID construction;
- manifest hashing;
- checkpoint invalidation;
- schema assembly;
- typed errors.

### B. Minimal RedEngine integration

Test:

- open/close;
- schema inventory;
- `SELECTION`;
- `NUMBER`;
- inherited DEFINE;
- `FREQ`;
- `@cmpcode`;
- masks.

### C. Permanent Argentina fixtures

Tiny RADIO `061120902`: 1/1/1.

Relational RADIO `061471101`: 73/56/137.

Large RADIO `064279901`: 6,992 persons.

FRAC `0614711`: 130/72/173.

### D. National/release controls

Run for releases, not every unit test:

- national counts;
- provincial controls;
- full partition coverage;
- duplicate global keys;
- missing partitions;
- schema completeness.

## 3. Mandatory first thin vertical slice

Input:

```text
Base_VP/cpv2022.rxdb
RADIO 061471101
```

Execution:

```text
discover hierarchy
→ select RADIO
→ acquire cmpcode geography
→ generate VIVIENDA/HOGAR/PERSONA IDs
→ extract stored variables in batches
→ merge batches by explicit IDs
→ write three Parquet outputs
→ write manifests
→ validate
```

### Required assertions

#### Hierarchy discovery

Generic layer identifies a chain ending in:

```text
RADIO > VIVIENDA > HOGAR > PERSONA
```

without an Argentina-specific hard-coded return value.

#### Geography

Recovered `RADIO@cmpcode` equals selected radio.

#### Counts

Exactly:

```text
VIVIENDA 73
HOGAR    56
PERSONA  137
```

#### PK/FK

- every entity PK unique;
- every HOGAR references one recovered VIVIENDA;
- every PERSONA references one recovered HOGAR and VIVIENDA;
- PERSONA dwelling assignment agrees directly and through its HOGAR path.

#### Position

`NUMBER HOGAR` on PERSONA is contiguous within every household.

#### Household size

Recovered person count per household equals `TOTPOBH`.

#### Exact reaggregation

At minimum reproduce source distributions for:

```text
VIVIENDA: V01, V06, TOTPOBV, NHOGH
HOGAR:    TOTPOBH, H10
PERSONA:  P02, EDAD, P06
```

Comparison includes category codes, missing/mask semantics and counts.

#### Determinism

A second complete run from the same inputs/config produces identical logical rows, IDs, schemas and semantic dataset fingerprints.

#### Resume

Interrupt after at least one batch, restart, and obtain the same final logical dataset as a clean run.

#### Corruption

Damage/delete one checkpoint artifact. Restart must detect and recompute it.

#### Provenance mismatch

Change query/schema configuration. Existing checkpoint must invalidate.

## 4. Identity-scope qualification

Before freezing canonical keys, run a multi-radio FRAC extraction while setting:

```text
physical selection = FRAC
identity scope      = RADIO
```

Determine whether `NUMBER RADIO` resets correctly and pairs with inherited `RADIO@cmpcode`.

If yes, freeze:

```text
global key = radio_cmpcode + radio-relative sequence
```

and prove overlapping records have identical keys whether extracted by RADIO or FRAC.

If no, define another explicit identity-scope contract.

## 5. Batch-width study

Test widths such as 1, 3, 5, 8, 10 on the 6,992-person radio and representative FRACs.

Measure:

- elapsed;
- peak RSS;
- raw FREQ cells;
- normalized rows;
- merge cost.

Choose default for bounded memory first, throughput second.

## 6. Exact source equivalence

For selected variables:

```text
RedEngine source FREQ
       ==
GROUP BY extracted Parquet
```

This is mandatory evidence, not optional diagnostics.

## 7. HNVUA

Expected current status: known compiler ambiguity.

Test that:

- anomaly is surfaced;
- remaining variables continue;
- manifest reports it;
- a failed HNVUA query cannot silently make the whole containing batch incomplete.

## 8. TABLE VIEW

Only a capability smoke test is needed. Current RedEngine 1.3 expected result:

```text
VIEW tables are not supported.
```

It is not a production acceptance criterion.

## 9. Fatal failures

Fatal:

- PK duplication;
- missing keys;
- FK violation;
- entity count mismatch;
- exact reaggregation mismatch;
- source/query/schema hash mismatch;
- schema collision;
- missing required variable batch;
- unexpected non-unit record cell.

Warnings MAY cover known HNVUA omission and optional metadata gaps.

## 10. Machine-readable validation output

Example:

```json
{
  "status": "pass",
  "source_hash": "...",
  "dataset_hash": "...",
  "counts": {},
  "checks": [
    {"name": "persona_fk_hogar", "status": "pass"}
  ]
}
```
