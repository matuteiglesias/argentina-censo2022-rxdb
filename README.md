# argentina-censo2022-rxdb

Reproducible extraction, validation, and Census-frame adapter for the Argentina 2022 Census RedatamX databases.

This repository contains the INDEC-specific layer built on top of [`rxdb-extractor`](https://github.com/matuteiglesias/rxdb-extractor): source-release provenance, VP / PO_A_IG / VC_PSC semantics, official controls, metadata, known anomalies, geography policy, and conversion of validated VP relational extracts into the vintage-neutral `research.census-frame/v1` contract consumed by [`samplerCensoARG`](https://github.com/matuteiglesias/samplerCensoARG).

## Status

The permanent VP relational laboratory is live-qualified against the preserved April-2025 Argentina source. RADIO `061471101` reproduces the expected 73 VIVIENDA / 56 HOGAR / 137 PERSONA records with unique canonical keys and exact VIVIENDA/HOGAR/PERSONA foreign-key validation.

Development may use that April 2025 source corpus. The corrected July-2025 RedatamX release remains the preferred canonical national source once recovered.

## CLI

Inspect and provenance-lock a local source corpus:

```bash
arg-censo2022 inspect /data/bases_censo2022_RedatamX \
  --release-label april-2025 --hashes
```

Print the portable VP profile consumed by `rxdb-extractor`:

```bash
arg-censo2022 profile vp > argentina-censo2022-vp.json
```

After `rxdb-extractor` has produced a validated VP relational slice, materialize a sampler-compatible Census frame:

```bash
arg-censo2022 frame \
  /data/vp-radio-061471101 \
  /data/frames \
  --source-release-label april-2025
```

The frame command preserves every source payload column and appends only neutral frame identities. It writes:

```text
research.census-frame/v1
  frame_households.parquet
  donor_person_mass.parquet
  payload/vivienda.parquet
  payload/hogar.parquet
  payload/persona.parquet
  manifest.json
```

On runtimes exposing `XDPTO`, department geography uses the engine-provided cmpcode. On the qualified RedEngine-1.1 RADIO fallback, the adapter derives the five-digit Argentina department code from the exact nine-digit official `XRADIO` scope under the explicit policy `argentina-radio-prefix-fallback/v1`; this fallback is intentionally Argentina-specific and is not part of the generic extractor.

The resulting directory is designed to pass:

```bash
censo-sampler frame check /data/frames/<frame-release>
```

See [`docs/CENSUS_FRAME_HANDOFF.md`](docs/CENSUS_FRAME_HANDOFF.md), [`docs/spec/00_START_HERE.md`](docs/spec/00_START_HERE.md), and [`docs/spec/03_ARG2022_ADAPTER_SPEC.md`](docs/spec/03_ARG2022_ADAPTER_SPEC.md).

## Boundaries

This adapter must not reimplement RedEngine extraction mechanics, must not join VP/PO by positional row order, and must keep any public-data release decision separate from the correctness of local relational extraction. Full recovered person-level records may be materialized locally, but public redistribution requires a separate privacy/legal/disclosure review.
