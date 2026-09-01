# Argentina Census 2022 Adapter — Normative Specification

## 1. Purpose

The Argentina 2022 adapter is the first production consumer of the generic RXDB extractor. It contains INDEC-specific source knowledge, metadata, controls, geography and release semantics while delegating all RedEngine/extraction mechanics to the generic core.

## 2. Source families

Recognize three complementary official databases:

- `Base_VP` — private dwellings with VIVIENDA/HOGAR/PERSONA hierarchy to RADIO.
- `Base_PO_A_IG` — additional Indigenous/Afro-descendant/gender-identity variables with different dissemination geography.
- `Base_VC_PSC` — collective dwellings / street-population dissemination database.

The adapter MUST discover actual RXDB/RBFX filenames and MUST NOT assume the April-2025 local spelling is universal.

## 3. Source release model

Source release is part of dataset identity.

Known history:

- April 2025 initial portable RedatamX release;
- May 2025 corrections/dictionary fixes;
- 2025-07-08 replacement of all databases with geography corrections and an added educational-age variable;
- portable RedatamX download later removed from the current INDEC page.

Development MAY continue against the April corpus. A canonical release SHOULD use the corrected July corpus once acquired.

April and July sources MUST remain separate, hashed and explicitly labeled.

## 4. Source manifest

Record for every logical database:

```text
logical name
actual RXDB filename
associated RBFX filenames
sizes
SHA-256
acquisition provenance
release classification
```

The adapter MUST never overwrite a prior source snapshot in place.

## 5. VP extraction

VP MUST produce normalized:

```text
VIVIENDA
HOGAR
PERSONA
```

using native generated hierarchy.

Known April development-source controls:

```text
VIVIENDA 17,783,029
HOGAR    15,932,302
PERSONA  45,618,787
```

Release-specific controls belong in adapter data/config, not generic code.

## 6. PO_A_IG integration

Production integration MUST NOT join VP and PO by row position.

Before integration, establish a defensible cross-base identity strategy using some combination of:

- common geography;
- generated local sequences;
- shared controls;
- stable reproducible fingerprints;
- explicit source identity if available.

If identity cannot be proven strongly enough, PO stays a separate output/unresolved adapter feature rather than weakening VP correctness.

## 7. VC_PSC semantics

The adapter MUST inspect and expose the actual entity hierarchy and output semantics.

It MUST NOT call a VIVIENDA-level table "collective persons".

If both VIVIENDA and PERSONA universes exist, they must be represented separately and validated separately.

## 8. Geography and dissemination limits

Preserve the geography actually exposed by each official database/universe.

The adapter MUST NOT synthesize finer geography for variables distributed only at a coarser level.

Metadata MUST carry source database, source universe and geography limitation.

## 9. `@cmpcode`

On RedEngine 1.3-capable runtimes, include stable geography fields when applicable:

```text
prov_cmpcode
dpto_cmpcode
frac_cmpcode
radio_cmpcode
```

Preferred source radio ID is `RADIO@cmpcode`, not manual string concatenation.

## 10. Canonical relational IDs

Preferred contract, pending the explicit identity-scope qualification:

```text
vivienda_key = <radio_cmpcode>:<vivienda_seq>
hogar_key    = <radio_cmpcode>:<hogar_seq>
persona_key  = <radio_cmpcode>:<persona_seq>
```

Required FKs:

```text
HOGAR.vivienda_key
PERSONA.hogar_key
PERSONA.vivienda_key
```

All FKs must validate exactly.

## 11. HNVUA policy

`PERSONA.HNVUA` is currently ambiguous because source name and alias collide. It fails under RedEngine 1.1 and 1.3.

The adapter MUST:

- inventory the variable;
- mark it explicitly as known-unextractable under the current source/runtime;
- isolate the failure so other PERSONA variables continue;
- include its status in metadata/manifest;
- retest against the corrected July source.

It MUST NOT silently disappear.

## 12. Metadata

Adapter metadata SHOULD include:

- entity;
- source variable name and alias;
- label;
- categories;
- universe;
- source database;
- dissemination geography;
- extraction status;
- notes/known anomaly.

Original variable names SHOULD remain canonical; friendly labels belong in metadata.

## 13. Partition strategy

Support RADIO and FRAC initially.

Known VP geography counts:

```text
PROV  24
DPTO  527
FRAC  6,540
RADIO 66,422
```

FRAC is operationally attractive but must pass identity-scope and memory tests before becoming the production default.

## 14. Permanent Argentina fixtures

### Tiny

```text
RADIO 061120902
1 dwelling / 1 household / 1 person
```

### Relational

```text
RADIO 061471101
73 dwellings / 56 households / 137 persons
```

### Large-radio performance fixture

```text
RADIO 064279901
6,992 persons
```

### FRAC

```text
FRAC 0614711
130 dwellings / 72 households / 173 persons
```

## 15. Adapter-level validation

Must include:

- entity counts;
- PK/FK integrity;
- household size checks via `TOTPOBH` where present;
- selected exact source reaggregations;
- geographic inventory/coverage;
- province/national controls when available;
- explicit incomplete-variable report.

## 16. Output layout

Recommended:

```text
argentina-censo2022/
  source-manifest.json
  dataset-manifest.json
  metadata.parquet
  validation.json
  vp/
    vivienda/
    hogar/
    persona/
  po/
  vc/
```

## 17. Derived public product

A downstream product MAY materialize:

```text
geo_id
entity
variable
category_code
category_label
count
source_release
```

This is separate from the full relational extract.

## 18. Redistribution boundary

The adapter MAY produce full relational records locally.

Public redistribution of person-level recovered records MUST NOT be assumed appropriate merely because extraction is technically possible. It requires a separate privacy/legal/disclosure review.

## 19. CLI target

```bash
arg-censo2022 inspect /data/censo2022
arg-censo2022 extract /data/censo2022 ./out
arg-censo2022 validate ./out
arg-censo2022 aggregate-public ./out ./public
```
