# argentina-censo2022-rxdb

Reproducible extraction, validation, and Census-frame adapter for the Argentina 2022 Census RedatamX databases.

This repository contains the INDEC-specific layer built on top of [`rxdb-extractor`](https://github.com/matuteiglesias/rxdb-extractor): source-release provenance, VP / PO_A_IG / VC_PSC semantics, official controls, known anomalies, geography policy, governed partition inventories, and conversion of validated VP relational extracts into the vintage-neutral `research.census-frame/v1` contract consumed by [`samplerCensoARG`](https://github.com/matuteiglesias/samplerCensoARG).

## Status

The VP extraction primitive is live-qualified against the preserved April-2025 source on `redatamx 1.1.3` / `RedEngine 1.1.0-final`.

Qualified laboratories include:

- RADIO `061120902`: 1 VIVIENDA / 1 HOGAR / 1 PERSONA;
- RADIO `061471101`: 73 / 56 / 137, exact PK/FK validation pass;
- RADIO `064279901`: 1,663 / 1,627 / 6,992, exact PK/FK validation pass; the qualifying one-shot run took about 2m30s and peaked near 1.34 GB RSS.

Development may use the preserved April 2025 source. The corrected July-2025 RedatamX release remains the preferred canonical national source once recovered.

## Profiles and partition strategies

Compatibility profile:

```bash
arg-censo2022 profile vp > argentina-censo2022-vp-radio.json
```

This selects RADIO and keeps RADIO as the identity scope. It works on the qualified RedEngine-1.1 fallback even without `@cmpcode`.

Preferred national profile when a cmpcode-capable runtime is qualified:

```bash
arg-censo2022 profile vp-frac > argentina-censo2022-vp-frac.json
```

This selects FRAC while **retaining RADIO as record identity scope**. It reduces the intended partition count from roughly 66k RADIOs to roughly 6.5k FRACs without changing canonical VIVIENDA/HOGAR/PERSONA key semantics. The generic extractor deliberately fails closed if this profile is attempted without cmpcode support.

## Source provenance

```bash
arg-censo2022 inspect /data/bases_censo2022_RedatamX \
  --release-label april-2025 --hashes
```

April and July source corpora must remain separate and explicitly identified.

## Governed partition inventories

Turn an official/local geography table into the exact sorted partition list consumed by `rxdb extract-many`:

```bash
arg-censo2022 partition-inventory /data/geography.parquet ./radios.json \
  --level RADIO --column IDRADIO --expected-count 66422
```

or, for the preferred cmpcode path:

```bash
arg-censo2022 partition-inventory /data/geography.parquet ./fracs.json \
  --level FRAC --column IDFRAC --expected-count 6540
```

CSV, TSV, Parquet, and one-code-per-line text sources are supported. Codes are normalized to the exact Argentina widths, deduplicated, sorted, and tied to the source hash. The explicit count control is optional but recommended when an official inventory control is known.

## National extraction

With `rxdb-extractor` installed from the companion repository:

```bash
export RXDB_BRIDGE="Rscript $HOME/repos/rxdb-extractor/bridges/redatamx_bridge.R"

rxdb --bridge "$RXDB_BRIDGE" --persistent-bridge \
  extract-many /data/Base_VP/cpv2022.rxdb \
  --profile ./argentina-censo2022-vp-radio.json \
  --partitions ./radios.json \
  --output-root /data/work/vp-radio \
  --workers 2
```

The run is checkpointed per partition. Re-running the same command skips only partitions whose provenance and output artifacts still verify. Worker count defaults to one and should be raised explicitly only after considering the memory footprint of one RedEngine worker.

Before a national launch, use `--limit` to qualify the exact runtime/transport on a small number of partitions.

## Census-frame materialization

One validated slice:

```bash
arg-censo2022 frame \
  /data/vp-radio-061471101 \
  /data/frames \
  --source-release-label april-2025
```

A complete RADIO or FRAC partition run:

```bash
arg-censo2022 frame-partitions \
  /data/work/vp-radio \
  /data/frames \
  --source-release-label april-2025
```

`frame-partitions` verifies every source Parquet against its slice manifest, checks cross-partition relational identities on disk, and streams the partition payloads directly into one frame. It does not require a giant intermediate merged extract.

The frame preserves every source payload column and appends only neutral frame identities:

```text
research.census-frame/v1
  frame_households.parquet
  donor_person_mass.parquet
  payload/vivienda.parquet
  payload/hogar.parquet
  payload/persona.parquet
  partition-index.json   # partition-set frames
  manifest.json
```

On cmpcode-capable output, department geography uses `XDPTO`. On the qualified RedEngine-1.1 RADIO fallback, the adapter derives the five-digit department code from the exact nine-digit `XRADIO` under the explicit Argentina-only policy `argentina-radio-prefix-fallback/v1`.

The resulting release is designed to pass:

```bash
censo-sampler frame check /data/frames/<frame-release>
```

See [`docs/NATIONAL_VP_RUNBOOK.md`](docs/NATIONAL_VP_RUNBOOK.md), [`docs/CENSUS_FRAME_HANDOFF.md`](docs/CENSUS_FRAME_HANDOFF.md), and [`docs/spec/03_ARG2022_ADAPTER_SPEC.md`](docs/spec/03_ARG2022_ADAPTER_SPEC.md).

## Boundaries

This adapter does not reimplement RedEngine extraction mechanics and never joins VP/PO by row position. Full recovered person-level records may be materialized locally for authorized work, but public redistribution requires a separate privacy/legal/disclosure review.
