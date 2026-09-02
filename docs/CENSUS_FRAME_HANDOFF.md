# Census 2022 VP → vintage-neutral Census frame

This document defines the supported handoff from a validated `rxdb-extractor` VP slice to the `research.census-frame/v1` contract consumed by `samplerCensoARG`.

## Preconditions

The input directory must be a completed `rxdb-extractor` relational slice containing:

```text
vivienda.parquet
hogar.parquet
persona.parquet
dataset-manifest.json
validation.json
```

`validation.json` must have `status=pass`. The source Parquet tables must contain the canonical relational keys produced by the generic extractor:

```text
VIVIENDA: vivienda_key, XRADIO
HOGAR:    hogar_key, vivienda_key, XRADIO
PERSONA:  persona_key, hogar_key, vivienda_key, XRADIO
```

The permanent live acceptance slice is RADIO `061471101`, with 73 VIVIENDA, 56 HOGAR, and 137 PERSONA records.

## Command

```bash
arg-censo2022 frame \
  /path/to/validated-vp-slice \
  /path/to/frame-output-root \
  --source-release-label april-2025
```

The command creates an immutable content/provenance-derived release directory named like:

```text
arg-cpv2022-frame-<digest>
```

If the same release identity already exists and its manifest agrees, the existing immutable release is returned. A conflicting destination fails closed.

## Output contract

```text
research.census-frame/v1
  frame_households.parquet
  donor_person_mass.parquet
  payload/
    vivienda.parquet
    hogar.parquet
    persona.parquet
  manifest.json
```

The narrow index plane contains only sampling identities and donor mass. The payload plane preserves every extracted Census source column and appends neutral IDs:

```text
vivienda_key → frame_dwelling_id
hogar_key    → frame_household_id
persona_key  → frame_person_id
```

HOGAR payload also receives `frame_dwelling_id`; PERSONA payload receives `frame_household_id`.

No EPH-facing feature selection is performed here.

## Geography policy

Preferred path, when RedEngine exposes cmpcodes:

```text
XDPTO  → department_id
XRADIO → radio_id
policy = redengine-dpto-cmpcode/v1
```

Qualified RedEngine-1.1 RADIO fallback:

```text
XRADIO = exact selected official RADIO code
radio_id = XRADIO
department_id = first five digits of the exact nine-digit XRADIO
policy = argentina-radio-prefix-fallback/v1
```

This is an Argentina-adapter rule, not a generic RXDB rule. It is bounded to exact nine-digit numeric RADIO codes and fails closed otherwise. The permanent fixtures establish the relevant hierarchical prefix relationship (`FRAC 0614711`, `RADIO 061471101`).

The sampler-level target-parent compatibility policy remains separately recorded as `assume-code-identity/v1`; the sampler planner must surface any donor/target department mismatches before materialization.

## Sampling handoff

After materialization, validate with the sampler's independent contract checker:

```bash
censo-sampler frame check /path/to/frame-release
```

Then dry-run the target-year design before writing sample rows:

```bash
censo-sample-plan \
  --frame /path/to/frame-release \
  --target-population /path/to/target.csv-or-parent \
  --target-year 2024 \
  --fraction 0.01 \
  --details
```

Only after the planner is ready should the frame be sampled.

## Scale boundary

The frame builder is disk-backed for household/person indexing and streams Parquet payload copies. It is suitable for large validated VP slices without loading all IDs or payload columns into Python memory.

National production still requires upstream partition inventory/orchestration and a national or multi-partition frame assembly policy. This command intentionally does not pretend that one RADIO slice is a national frame.

## Redistribution boundary

The frame may contain recovered person-level Census records. Local research materialization is technically supported. Public redistribution requires separate privacy/legal/disclosure review and is outside this handoff contract.
