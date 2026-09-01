# Release Governance

## 1. Separate artifacts

Treat as independent release decisions:

1. generic extractor software;
2. Argentina 2022 adapter software;
3. full relational extracts;
4. derived public aggregate datasets.

They need not share license, access policy or publication venue.

## 2. Generic software

Target open source subject to dependency compatibility.

Source code MUST NOT assume permission to redistribute proprietary RedEngine binaries.

A published container that bundles RedEngine requires explicit redistribution review.

## 3. Argentina adapter

May safely contain code/config such as:

- source URLs and expected logical structure;
- release provenance;
- hashes;
- metadata parsers;
- official controls;
- validation rules.

It SHOULD NOT embed official source census files unless clearly permitted.

## 4. Full relational extract

Default classification: **local/research substrate**.

Do not automatically publish a national PERSONA-level Parquet because it is technically recoverable.

Before public redistribution review:

- INDEC statistical secrecy rules;
- dissemination-geography restrictions;
- sensitive universes;
- disclosure risk;
- source terms;
- legal advice if warranted.

## 5. Public aggregate product

A downstream public layer may contain source-permitted:

```text
geography
entity
variable
category
count
```

with a separate manifest/version from the relational extraction.

## 6. Provenance requirements

Every released data artifact should identify:

- source release;
- extraction software version;
- RedEngine version;
- runtime/container fingerprint;
- source hashes where appropriate;
- validation report;
- known anomalies;
- release date.

## 7. Source supersession

Never silently replace April-derived output with July-derived output.

Use explicit source-release IDs, e.g.:

```text
arg-censo2022-redatamx-2025-04
arg-censo2022-redatamx-2025-07
```

## 8. Reproducibility contract

A scientific release should be rebuildable from:

```text
legitimately acquired source corpus
+ exact extractor release
+ exact adapter release/config
+ runtime definition
```

## 9. Security boundary

The software MUST NOT add mechanisms intended to defeat authentication, access controls or statistical disclosure-protection systems.

The current design operates against legitimately available local dissemination databases through RedEngine query semantics.

## 10. Attribution/citation

Future releases should provide citations/attribution for:

- extractor software;
- adapter/data release;
- INDEC source;
- RedEngine/CELADE;
- relevant prior REDATAM conversion/open-source work.
