# argentina-censo2022-rxdb

Reproducible extraction and validation adapter for the Argentina 2022 Census RedatamX databases.

This repository contains the INDEC-specific layer built on top of [`rxdb-extractor`](https://github.com/matuteiglesias/rxdb-extractor): source-release provenance, VP / PO_A_IG / VC_PSC semantics, official controls, metadata, known anomalies, and adapter-level validation.

## Status

Specification-first / early development. The generic extractor is being built first. This repository is intentionally kept thin until the generic M3 one-RADIO vertical slice is stable.

Development may use the existing April 2025 source corpus, while the corrected July 2025 RedatamX release remains the preferred canonical source once recovered.

See [`docs/spec/00_START_HERE.md`](docs/spec/00_START_HERE.md) and [`docs/spec/03_ARG2022_ADAPTER_SPEC.md`](docs/spec/03_ARG2022_ADAPTER_SPEC.md).

## Boundaries

This adapter must not reimplement RedEngine extraction mechanics, must not join VP/PO by positional row order, and must keep any public-data release decision separate from the correctness of local relational extraction.
