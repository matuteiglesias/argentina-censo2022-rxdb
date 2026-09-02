from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator

from .frame import CensusFrameBuildError, canonical_json, sha256_file

WIDTHS = {"RADIO": 9, "FRAC": 7}


def _normalize_code(value: object, *, level: str) -> str:
    level = level.upper()
    if level not in WIDTHS:
        raise CensusFrameBuildError(f"unsupported_partition_level:{level}")
    if value is None or isinstance(value, bool):
        raise CensusFrameBuildError(f"invalid_{level.lower()}_code:{value!r}")
    if isinstance(value, float):
        if not value.is_integer():
            raise CensusFrameBuildError(f"invalid_{level.lower()}_code:{value!r}")
        value = int(value)
    text = str(value).strip()
    if not text or not text.isdigit():
        raise CensusFrameBuildError(f"invalid_{level.lower()}_code:{value!r}")
    width = WIDTHS[level]
    number = int(text)
    if number < 0 or number >= 10**width:
        raise CensusFrameBuildError(f"invalid_{level.lower()}_code:{value!r}")
    return f"{number:0{width}d}"


def _iter_structured(path: Path, column: str) -> Iterator[object]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        if column not in parquet.schema_arrow.names:
            raise CensusFrameBuildError(f"partition_source_missing_column:{column}")
        for batch in parquet.iter_batches(batch_size=65536, columns=[column]):
            for value in batch.column(0).to_pylist():
                yield value
        return
    if suffix in {".csv", ".tsv"}:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            sample = stream.read(8192)
            stream.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel_tab if suffix == ".tsv" else csv.excel
            reader = csv.DictReader(stream, dialect=dialect)
            if not reader.fieldnames or column not in reader.fieldnames:
                raise CensusFrameBuildError(f"partition_source_missing_column:{column}")
            for row in reader:
                yield row.get(column)
        return
    raise CensusFrameBuildError(f"unsupported_partition_source_format:{suffix or '<none>'}")


def build_partition_inventory(
    source: Path,
    output: Path,
    *,
    level: str,
    column: str | None = None,
    expected_count: int | None = None,
) -> Path:
    """Create an rxdb ``extract-many`` inventory from an official geography source.

    Structured CSV/TSV/Parquet inputs require an explicit column name. Plain text
    inputs are interpreted as one code per line. Codes are normalized to the exact
    Argentina FRAC/RADIO width, deduplicated, sorted and provenance-hashed.
    """
    source = Path(source).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if not source.is_file():
        raise CensusFrameBuildError(f"partition_source_missing:{source}")
    level = level.upper()
    if level not in WIDTHS:
        raise CensusFrameBuildError(f"unsupported_partition_level:{level}")

    suffix = source.suffix.lower()
    if suffix in {".txt", ".list", ""}:
        values = [
            line.strip()
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        source_column = None
    else:
        if not column:
            raise CensusFrameBuildError("structured_partition_source_requires_column")
        values = list(_iter_structured(source, column))
        source_column = column

    codes = sorted({_normalize_code(value, level=level) for value in values})
    if not codes:
        raise CensusFrameBuildError("partition_inventory_is_empty")
    if expected_count is not None and len(codes) != expected_count:
        raise CensusFrameBuildError(
            f"partition_count_mismatch:expected={expected_count}:observed={len(codes)}"
        )

    payload = {
        "contract": "argentina.censo2022-rxdb.partition-inventory/v1",
        "partition_level": level,
        "partition_count": len(codes),
        "source": {
            "path_name": source.name,
            "sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
            "column": source_column,
        },
        "partitions": codes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing == payload:
            return output
        raise CensusFrameBuildError(f"partition_inventory_output_exists:{output}")
    output.write_text(canonical_json(payload), encoding="utf-8")
    return output
