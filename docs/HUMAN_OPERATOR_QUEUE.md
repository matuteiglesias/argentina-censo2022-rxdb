# Human operator queue

These tasks are the remaining local-data/runtime actions after the VP extraction and frame machinery has been developed.

## Completed live qualification

- Preserved April-2025 VP source opens through the supported `redatamx` bridge on RedEngine 1.1.0.
- RADIO `061120902` passes the 1/1/1 real-data smoke test.
- Permanent M3 RADIO `061471101` passes with 73 VIVIENDA / 56 HOGAR / 137 PERSONA records.
- Canonical `vivienda_key`, `hogar_key`, and `persona_key` are unique and all required VIVIENDA/HOGAR/PERSONA foreign keys validate exactly.
- The RedEngine-1.1 `XRADIO` selection-code fallback is qualified for RADIO-scoped identity.

## Next local actions

1. Pull the current adapter and run the supported frame handoff on the validated M3 directory:

   ```bash
   arg-censo2022 frame \
     /media/matias/Elements/CENSO_work/rxdb/vp-radio-061471101 \
     /media/matias/Elements/CENSO_work/frames \
     --source-release-label april-2025
   ```

2. Validate the resulting `research.census-frame/v1` independently with:

   ```bash
   censo-sampler frame check /media/matias/Elements/CENSO_work/frames/<frame-release>
   ```

3. Run a bounded sampler acceptance release against that real 2022 frame before any national extraction.
4. Run the large-radio performance fixture `064279901` and record elapsed time / peak memory.
5. Qualify FRAC identity scope on `0614711` before making FRAC the production partition default.
6. If the corrected July-2025 source is acquired, unpack it separately and provenance-lock it with `--release-label july-2025`; never overwrite the April corpus.

## Source acquisition

- Continue pursuing a retained copy of the corrected July-2025 official RedatamX ZIP through known researchers or archived sources.

## Governance decisions

- Confirm RedEngine redistribution/licensing before bundling it in a public container image.
- Resolve publication/disclosure policy before releasing reconstructed person-level national records.

These governance/source-acquisition items do not block local frame materialization, sampler acceptance, partition orchestration development, or national extraction engineering.
