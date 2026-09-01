# Evidence Baseline — Do Not Re-Litigate Without New Evidence

This file records the experimentally established baseline that implementation agents may rely on. New experiments may supersede it, but agents should not reopen settled questions merely from intuition.

## E1 — Supported source counts

On the development VP corpus, RedEngine reproduces exactly:

```text
VIVIENDA 17,783,029
HOGAR    15,932,302
PERSONA  45,618,787
```

Interpretation: supported aggregate access is sound.

## E2 — Selectable geography

Known national VP inventory:

```text
PROV  24
DPTO  527
FRAC  6,540
RADIO 66,422
```

VIVIENDA/HOGAR/PERSONA are not AREALIST-selectable entities.

## E3 — `SELECTION` is the partition primitive

`SELECTION RADIO == ...` and FRAC selection reproduce correct descendant records and run sub-second on small fixtures.

Equivalent ancestor-variable `FILTER` expressions scan national data and take tens of seconds.

Do not replace SELECTION with FILTER for physical partitioning without contrary evidence.

## E4 — Entity identity via NUMBER

Examples already confirmed:

```text
DEFINE PERSONA.XPID AS NUMBER RADIO
DEFINE PERSONA.XPINH AS NUMBER HOGAR
```

Own sequences are unique/contiguous within tested scope; `NUMBER HOGAR` gives within-household position.

## E5 — Parent-key inheritance

Generated VIVIENDA/HOGAR sequences can be inherited onto child entities. All tested HOGAR→VIVIENDA and PERSONA→HOGAR/VIVIENDA FKs resolve.

Use native hierarchy rather than reconstructing from substantive variables.

## E6 — FREQ can emit records

With a unique generated sequence dimension, complete non-margin FREQ cells correspond one-to-one with underlying records and have count=1.

This is the production extraction primitive.

## E7 — Permanent relational fixture

RADIO `061471101`:

```text
73 VIVIENDA
56 HOGAR
137 PERSONA
```

Confirmed:

- unique PKs;
- all FKs resolve;
- contiguous positions;
- household rows equal `TOTPOBH`;
- exact distributions for V01, V06, TOTPOBV, NHOGH, TOTPOBH, H10, P02, EDAD and P06.

## E8 — Variable coverage

All tested VIVIENDA and HOGAR variables succeed.

PERSONA: 33/34 succeed.

`PERSONA.HNVUA` fails due same-name alias ambiguity. Bare/qualified/quoted variants did not disambiguate it.

Treat as a known variable defect, not as evidence against the extraction architecture.

## E9 — Scale reference

Historical all-variable selected-radio proof:

```text
6,992 persons + 1,663 dwellings + 1,627 households
20.09 s
2.57 GB peak RSS
```

Interpretation: memory/batching is a real engineering constraint.

## E10 — FRAC/resume proof

FRAC `0614711`:

```text
130 VIVIENDA
72 HOGAR
173 PERSONA
```

Existing prototype wrote Parquet + SHA-256 + `_SUCCESS` and skipped validated work on rerun.

## E11 — RedEngine 1.3.0 compatibility

Confirmed unchanged relative to 1.1.0 for tested capabilities:

- RXDB/schema access;
- SELECTION;
- NUMBER;
- inherited parent sequences;
- unique-ID FREQ;
- masks/labels;
- deterministic selected outputs;
- exact reaggregation.

Verdict: GREEN WITH IMPROVEMENTS.

## E12 — `@cmpcode`

RedEngine 1.3 supports syntax:

```text
ENTITY@cmpcode
```

Confirmed:

- stable string geographic redcodes;
- unique at tested selectable levels;
- inherited successfully onto PERSONA;
- not listed by ordinary variable inventory;
- not directly usable as a SELECTION entity expression.

Use as a preferred geography/key primitive with capability guards.

## E13 — TABLE VIEW is not viable

Historical 1.1.0 behavior: approximately 101 rows on unmodified engine.

Current RedEngine 1.3.0 behavior:

```text
VIEW tables are not supported.
```

Do not build production code around TABLE VIEW or a binary patch.

## E14 — Runtime constraint

RedEngine 1.3.0 requires a newer glibc/libstdc++ than the current host. It ran successfully in an isolated R 4.4.2 container while the validated older environment remained intact.

Treat reproducible runtime/container packaging as product work.

## E15 — Performance reference under 1.3

ID + three-variable selected extraction:

```text
137 persons:   0.696 s
6,992 persons: 1.248 s
```

This is a modest slowdown from 1.1.0, not a feasibility regression.

## Open questions that ARE legitimate to investigate

1. Can physical FRAC extraction use RADIO-relative NUMBER identity, allowing canonical `RADIO@cmpcode + seq` keys independent of processing partition?
2. What batch width minimizes peak memory while preserving throughput?
3. What native binding technology gives the cleanest stable RedEngine boundary?
4. What robust identity joins VP and PO_A_IG without positional assumptions?
5. What exactly should be extracted from VC_PSC at each entity/universe?
6. Does the corrected July-2025 source change HNVUA or schema details?
7. What RedEngine redistribution rights apply to containers/installers?

## Questions that are CLOSED for normal development

Unless new evidence appears, do not spend development cycles on:

- blind LZMA/zlib/RBFX decompression experiments;
- making AREALIST emit non-selectable PERSONA/HOGAR/VIVIENDA;
- using TABLE VIEW as the modern production backend;
- reconstructing native hierarchy from P01/TOTPOBV;
- joining variable blocks by row position;
- assuming the April source is the canonical final data release.
