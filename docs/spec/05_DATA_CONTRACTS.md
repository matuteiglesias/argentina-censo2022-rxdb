# Data Contracts

## 1. Entity tables

Every entity table begins with system/provenance columns, then source variables.

Conceptual PERSONA:

```text
source_release
source_database
selection_geo_type
selection_geo_code
prov_cmpcode
dpto_cmpcode
frac_cmpcode
radio_cmpcode
persona_seq
hogar_seq
vivienda_seq
persona_key
hogar_key
vivienda_key
<stored variables...>
```

HOGAR and VIVIENDA use the analogous subset.

## 2. Sequences

Sequences are RedEngine `NUMBER` results and MUST document their scope.

Example metadata:

```json
{
  "field": "persona_seq",
  "generator": "NUMBER RADIO",
  "scope_entity": "RADIO"
}
```

## 3. Composite global keys

Preferred, pending M4 qualification:

```text
<radio_cmpcode>:<radio-relative entity sequence>
```

Example:

```text
061471101:137
```

Keys SHOULD be strings unless a structured compact encoding is deliberately standardized.

## 4. Variable names

Preserve original source names. Friendly aliases/labels belong in metadata.

Generated columns MUST use a collision-safe reserved namespace or convention.

## 5. Metadata table

Recommended fields:

```text
source_database
entity
source_name
source_alias
source_label
source_type
category_code
category_label
universe
geography_limit
extraction_status
notes
```

`extraction_status` examples:

```text
available
known_ambiguous
unsupported_runtime
not_in_release
```

## 6. Source manifest

Must identify exact source files and hashes.

```json
{
  "manifest_version": "1",
  "dataset": "argentina-censo2022",
  "source_release": {
    "label": "april-2025",
    "status": "superseded-development-source"
  },
  "inputs": [
    {
      "logical_name": "Base_VP",
      "rxdb": {"path": "Base_VP/cpv2022.rxdb", "sha256": "..."},
      "rbfx": [{"path": "...", "sha256": "..."}]
    }
  ]
}
```

## 7. Runtime manifest

```json
{
  "redengine_version": "1.3.0-final",
  "binding": "...",
  "os": "...",
  "arch": "...",
  "container_image": "...",
  "capabilities": {
    "selection": true,
    "number": true,
    "inherited_define": true,
    "freq": true,
    "cmpcode": true,
    "table_view": false
  }
}
```

## 8. Extraction manifest

```json
{
  "extractor_version": "...",
  "entity": "PERSONA",
  "identity_scope": "RADIO",
  "partition_scope": "FRAC",
  "batch_width": 5,
  "variables": ["..."],
  "schema_hash": "...",
  "planner_hash": "..."
}
```

## 9. Partition checkpoint

```json
{
  "partition": {"entity": "FRAC", "code": "0614711"},
  "source_hash": "...",
  "schema_hash": "...",
  "query_hash": "...",
  "runtime_hash": "...",
  "entities": {
    "VIVIENDA": {"rows": 130, "sha256": "..."},
    "HOGAR": {"rows": 72, "sha256": "..."},
    "PERSONA": {"rows": 173, "sha256": "..."}
  },
  "validation": "pass"
}
```

`_SUCCESS` is written only after durable outputs and passing validation.

## 10. Logical dataset fingerprint

Byte hashes of Parquet files are useful but may change with writer versions.

Also define a semantic fingerprint based on stable schema + canonical key/value ordering + partition manifests so logically identical datasets can be recognized across harmless encoding changes.

## 11. Schema evolution

Every output has a schema version.

Breaking changes include:

- key semantics;
- missing-state semantics;
- destructive variable renaming;
- entity normalization changes.

Additional optional metadata fields may be additive.
