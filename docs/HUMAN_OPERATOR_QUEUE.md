# Human operator queue

These tasks are deferred until a human operator has access to the local census corpus and validated runtime.

## When back at the local machine

1. Run `arg-censo2022 inspect <source-root> --release-label april-2025 --hashes` against the preserved April source and save the JSON manifest.
2. If the corrected July-2025 source is acquired, unpack it separately and run the same command with `--release-label july-2025`; never overwrite the April corpus.
3. Run the generic extractor's live RedEngine integration probes against `Base_VP/cpv2022.rxdb` once the runtime bridge is ready.
4. Run the permanent M3 laboratory on RADIO `061471101` and the FRAC identity-scope qualification on `0614711`.

## Source acquisition

- Continue pursuing a retained copy of the corrected July-2025 official RedatamX ZIP through known researchers or archived sources.

## Governance decisions

- Confirm RedEngine redistribution/licensing before bundling it in a public container image.
- Resolve publication/disclosure policy before releasing reconstructed person-level national records.

These items are deliberately not blockers for source-manifest, adapter, CLI, validation, Parquet, checkpointing, or generic-core development.
