from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .frame import (
    FRAME_ARTIFACTS,
    FRAME_CONTRACT,
    REQUIRED_SLICE_FILES,
    CensusFrameBuildError,
    _department_id,
    _frame_geography_policy,
    _iter_parquet_rows,
    _load_json,
    _require_columns,
    _validate_source_slice,
    _write_rows,
    canonical_json,
    sha256_file,
)

PARTITION_FRAME_BUILDER_VERSION = "arg-cpv2022-vp-partitions-parquet/v1"


@dataclass(frozen=True)
class VPPartition:
    selection_code: str
    root: Path
    manifest: dict[str, object]


def discover_vp_partitions(root: Path) -> tuple[VPPartition, ...]:
    """Discover completed extractor slice directories below one run root."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise CensusFrameBuildError(f"partition_root_missing:{root}")
    output: list[VPPartition] = []
    seen_codes: set[str] = set()
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if not all((child / name).is_file() for name in REQUIRED_SLICE_FILES):
            continue
        manifest, _ = _validate_source_slice(child)
        selection = manifest.get("selection")
        if not isinstance(selection, dict):
            raise CensusFrameBuildError(f"partition_missing_selection:{child.name}")
        entity = selection.get("entity")
        code = selection.get("code")
        if entity != "RADIO" or not isinstance(code, str) or not code:
            raise CensusFrameBuildError(f"partition_not_radio_slice:{child.name}")
        if code in seen_codes:
            raise CensusFrameBuildError(f"duplicate_radio_partition:{code}")
        seen_codes.add(code)
        output.append(VPPartition(code, child, manifest))
    if not output:
        raise CensusFrameBuildError("partition_root_contains_no_valid_vp_slices")
    output.sort(key=lambda item: item.selection_code)
    return tuple(output)


def _entity_artifact_record(partition: VPPartition, entity: str) -> dict[str, object]:
    entities = partition.manifest.get("entities")
    if not isinstance(entities, dict):
        raise CensusFrameBuildError(
            f"partition_manifest_missing_entities:{partition.selection_code}"
        )
    record = entities.get(entity)
    if not isinstance(record, dict) or not isinstance(record.get("artifact"), dict):
        raise CensusFrameBuildError(
            f"partition_manifest_missing_artifact:{partition.selection_code}:{entity}"
        )
    return record["artifact"]


def _verify_partition_artifacts(partition: VPPartition) -> dict[str, object]:
    """Verify actual Parquet bytes against each slice manifest before merging."""
    result: dict[str, object] = {}
    for entity in ("VIVIENDA", "HOGAR", "PERSONA"):
        artifact = _entity_artifact_record(partition, entity)
        expected = artifact.get("sha256")
        path = partition.root / f"{entity.lower()}.parquet"
        observed = sha256_file(path)
        if not isinstance(expected, str) or observed != expected:
            raise CensusFrameBuildError(
                f"partition_artifact_hash_mismatch:{partition.selection_code}:{entity}"
            )
        result[entity] = {
            "sha256": observed,
            "rows": artifact.get("rows"),
            "size_bytes": path.stat().st_size,
        }
    return result


def _partition_schemas(partition: VPPartition):
    import pyarrow.parquet as pq

    return {
        entity: pq.ParquetFile(partition.root / f"{entity}.parquet").schema_arrow
        for entity in ("vivienda", "hogar", "persona")
    }


def _copy_partition_payloads(
    partitions: tuple[VPPartition, ...],
    *,
    entity: str,
    destination: Path,
    aliases: tuple[tuple[str, str], ...],
    batch_size: int = 65536,
) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq

    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    output_schema = None
    count = 0
    try:
        for partition in partitions:
            source = partition.root / f"{entity}.parquet"
            parquet = pq.ParquetFile(source)
            _require_columns(
                parquet.schema_arrow.names,
                {source_name for _, source_name in aliases},
                f"{partition.selection_code}:{entity}",
            )
            collisions = {name for name, _ in aliases} & set(parquet.schema_arrow.names)
            if collisions:
                raise CensusFrameBuildError(
                    "neutral_frame_id_collision:" + ",".join(sorted(collisions))
                )
            for batch in parquet.iter_batches(batch_size=batch_size):
                table = pa.Table.from_batches([batch])
                for target, source_name in aliases:
                    table = table.append_column(target, table[source_name].cast(pa.string()))
                if output_schema is None:
                    output_schema = table.schema
                    writer = pq.ParquetWriter(destination, output_schema, compression="zstd")
                elif not table.schema.equals(output_schema):
                    raise CensusFrameBuildError(
                        f"partition_payload_schema_mismatch:{partition.selection_code}:{entity}"
                    )
                assert writer is not None
                writer.write_table(table)
                count += table.num_rows
        if writer is None:
            raise CensusFrameBuildError(f"cannot_copy_empty_partition_payload:{entity}")
    finally:
        if writer is not None:
            writer.close()
    return count


def _partition_index(
    partitions: tuple[VPPartition, ...],
    artifact_evidence: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "partition_count": len(partitions),
        "selection_entity": "RADIO",
        "partitions": [
            {
                "selection_code": partition.selection_code,
                "dataset_manifest_semantic_hash": partition.manifest.get("semantic_hash"),
                "validation_status": partition.manifest.get("validation_status"),
                "artifacts": artifact_evidence[partition.selection_code],
            }
            for partition in partitions
        ],
    }


def build_vp_partition_frame(
    partition_root: Path,
    output_root: Path,
    *,
    source_release_label: str = "unknown",
) -> Path:
    """Build one immutable sampler frame directly from validated RADIO partitions.

    No giant intermediate merged extraction is created: relation indexes are built
    in temporary SQLite and source Parquet batches are streamed directly into the
    frame payload files.
    """
    import pyarrow.parquet as pq

    source = Path(partition_root).expanduser().resolve()
    output_root = Path(output_root).expanduser().resolve()
    if output_root == source or source in output_root.parents:
        raise CensusFrameBuildError("unsafe_output_path_inside_partition_root")
    partitions = discover_vp_partitions(source)

    first_schemas = _partition_schemas(partitions[0])
    _require_columns(first_schemas["vivienda"].names, {"vivienda_key", "XRADIO"}, "VIVIENDA")
    _require_columns(
        first_schemas["hogar"].names,
        {"hogar_key", "vivienda_key", "XRADIO"},
        "HOGAR",
    )
    _require_columns(
        first_schemas["persona"].names,
        {"persona_key", "hogar_key", "vivienda_key", "XRADIO"},
        "PERSONA",
    )
    geography_policy = _frame_geography_policy(first_schemas["hogar"].names)

    artifact_evidence: dict[str, dict[str, object]] = {}
    for partition in partitions:
        schemas = _partition_schemas(partition)
        for entity in ("vivienda", "hogar", "persona"):
            if not schemas[entity].equals(first_schemas[entity]):
                raise CensusFrameBuildError(
                    f"partition_source_schema_mismatch:{partition.selection_code}:{entity}"
                )
        if _frame_geography_policy(schemas["hogar"].names) != geography_policy:
            raise CensusFrameBuildError("mixed_partition_geography_policies")
        artifact_evidence[partition.selection_code] = _verify_partition_artifacts(partition)

    run_manifest_path = source / "run-manifest.json"
    run_manifest = _load_json(run_manifest_path, "run_manifest") if run_manifest_path.is_file() else None
    index = _partition_index(partitions, artifact_evidence)
    identity = {
        "contract": FRAME_CONTRACT,
        "builder": PARTITION_FRAME_BUILDER_VERSION,
        "country": "ARG",
        "census_vintage": 2022,
        "source_release_label": source_release_label,
        "geography_policy": geography_policy,
        "run_source_hash": run_manifest.get("source_hash") if run_manifest else None,
        "partition_semantic_hashes": [
            [partition.selection_code, partition.manifest.get("semantic_hash")]
            for partition in partitions
        ],
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    release_id = f"arg-cpv2022-frame-{digest[:16]}"
    destination = output_root / release_id
    if destination.exists():
        existing = destination / "manifest.json"
        if existing.is_file():
            manifest = _load_json(existing, "frame_manifest")
            if manifest.get("frame_release_id") == release_id:
                return destination
        raise CensusFrameBuildError(f"immutable_frame_exists:{destination}")

    output_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{release_id}.", dir=output_root))
    db_path = work / ".frame-index.sqlite"
    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=OFF")
            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("PRAGMA temp_store=FILE")
            conn.execute(
                "CREATE TABLE hogar (hh TEXT PRIMARY KEY, viv TEXT NOT NULL, dept TEXT NOT NULL, radio TEXT NOT NULL)"
            )
            conn.execute("CREATE TABLE person (person TEXT PRIMARY KEY, hh TEXT NOT NULL)")
            conn.execute("CREATE TABLE hh_counts (hh TEXT PRIMARY KEY, n INTEGER NOT NULL)")

            try:
                for partition in partitions:
                    hogar_columns = ["hogar_key", "vivienda_key", "XRADIO"]
                    if geography_policy == "redengine-dpto-cmpcode/v1":
                        hogar_columns.append("XDPTO")
                    for row in _iter_parquet_rows(
                        partition.root / "hogar.parquet", hogar_columns
                    ):
                        hh = str(row.get("hogar_key") or "")
                        viv = str(row.get("vivienda_key") or "")
                        radio = str(row.get("XRADIO") or "")
                        if not hh or not viv or not radio:
                            raise CensusFrameBuildError("hogar:empty_relational_identity")
                        if radio != partition.selection_code:
                            raise CensusFrameBuildError(
                                f"partition_radio_mismatch:{partition.selection_code}:{radio}"
                            )
                        dept = _department_id(row, geography_policy)
                        conn.execute(
                            "INSERT INTO hogar(hh,viv,dept,radio) VALUES (?,?,?,?)",
                            (hh, viv, dept, radio),
                        )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise CensusFrameBuildError("duplicate_household_key_across_partitions") from exc

            try:
                for partition in partitions:
                    for row in _iter_parquet_rows(
                        partition.root / "persona.parquet", ["persona_key", "hogar_key"]
                    ):
                        person = str(row.get("persona_key") or "")
                        hh = str(row.get("hogar_key") or "")
                        if not person or not hh:
                            raise CensusFrameBuildError("persona:empty_relational_identity")
                        conn.execute("INSERT INTO person(person,hh) VALUES (?,?)", (person, hh))
                        conn.execute(
                            "INSERT INTO hh_counts(hh,n) VALUES (?,1) "
                            "ON CONFLICT(hh) DO UPDATE SET n=n+1",
                            (hh,),
                        )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise CensusFrameBuildError("duplicate_person_key_across_partitions") from exc

            orphan_people = conn.execute(
                "SELECT COUNT(*) FROM person p LEFT JOIN hogar h ON h.hh=p.hh WHERE h.hh IS NULL"
            ).fetchone()[0]
            empty_households = conn.execute(
                "SELECT COUNT(*) FROM hogar h LEFT JOIN hh_counts c ON c.hh=h.hh WHERE c.hh IS NULL"
            ).fetchone()[0]
            if orphan_people:
                raise CensusFrameBuildError(f"persona:orphan_households:{orphan_people}")
            if empty_households:
                raise CensusFrameBuildError(f"households_without_persons:{empty_households}")

            household_count = _write_rows(
                work / "frame_households.parquet",
                (
                    {
                        "frame_household_id": str(hh),
                        "frame_dwelling_id": str(viv),
                        "department_id": str(dept),
                        "radio_id": str(radio),
                        "household_person_count": int(n),
                    }
                    for hh, viv, dept, radio, n in conn.execute(
                        "SELECT h.hh,h.viv,h.dept,h.radio,c.n "
                        "FROM hogar h JOIN hh_counts c ON c.hh=h.hh ORDER BY h.hh"
                    )
                ),
            )
            donor_rows = [
                {"department_id": str(dept), "donor_person_mass": int(mass)}
                for dept, mass in conn.execute(
                    "SELECT h.dept,SUM(c.n) FROM hogar h JOIN hh_counts c ON c.hh=h.hh "
                    "GROUP BY h.dept ORDER BY h.dept"
                )
            ]
            _write_rows(work / "donor_person_mass.parquet", iter(donor_rows))
            person_count = conn.execute("SELECT COUNT(*) FROM person").fetchone()[0]
            if sum(int(row["donor_person_mass"]) for row in donor_rows) != person_count:
                raise CensusFrameBuildError("donor_person_mass_does_not_sum_to_person_count")
        finally:
            conn.close()

        payload = work / "payload"
        dwelling_count = _copy_partition_payloads(
            partitions,
            entity="vivienda",
            destination=payload / "vivienda.parquet",
            aliases=(("frame_dwelling_id", "vivienda_key"),),
        )
        payload_households = _copy_partition_payloads(
            partitions,
            entity="hogar",
            destination=payload / "hogar.parquet",
            aliases=(
                ("frame_household_id", "hogar_key"),
                ("frame_dwelling_id", "vivienda_key"),
            ),
        )
        payload_persons = _copy_partition_payloads(
            partitions,
            entity="persona",
            destination=payload / "persona.parquet",
            aliases=(
                ("frame_person_id", "persona_key"),
                ("frame_household_id", "hogar_key"),
            ),
        )
        if payload_households != household_count or payload_persons != person_count:
            raise CensusFrameBuildError("payload_row_count_mismatch")

        (work / "partition-index.json").write_text(
            canonical_json(index), encoding="utf-8"
        )
        artifacts = {
            name: {
                "sha256": sha256_file(work / name),
                "size_bytes": (work / name).stat().st_size,
            }
            for name in FRAME_ARTIFACTS
        }
        partition_index_meta = {
            "sha256": sha256_file(work / "partition-index.json"),
            "size_bytes": (work / "partition-index.json").stat().st_size,
        }
        manifest = {
            "contract": FRAME_CONTRACT,
            "frame_release_id": release_id,
            "country": "ARG",
            "census_vintage": 2022,
            "builder": PARTITION_FRAME_BUILDER_VERSION,
            "source_release_id": source_release_label,
            "source": {
                "kind": "rxdb-extractor VP RADIO partition set",
                "partition_root_name": source.name,
                "partition_count": len(partitions),
                "partition_index": partition_index_meta,
                "run_manifest_sha256": (
                    sha256_file(run_manifest_path) if run_manifest_path.is_file() else None
                ),
                "run_source_hash": run_manifest.get("source_hash") if run_manifest else None,
                "microdata_republished_outside_local_frame": False,
            },
            "department_alignment_policy": "assume-code-identity/v1",
            "geography_derivation_policy": geography_policy,
            "identity": {
                "frame_dwelling_id": "vivienda_key",
                "frame_household_id": "hogar_key",
                "frame_person_id": "persona_key",
            },
            "counts": {
                "dwellings": dwelling_count,
                "households": household_count,
                "persons": person_count,
                "departments": len(donor_rows),
                "radio_partitions": len(partitions),
            },
            "artifacts": artifacts,
            "payload_policy": "full-source-columns-plus-neutral-frame-ids/v1",
            "feature_projection": None,
            "limitations": [
                "Department-code identity is provisionally assumed compatible with the sampler target-population parent; mismatches must be surfaced by the sampler.",
                "The frame preserves Census variables but does not define EPH semantic mappings.",
                "Public redistribution of recovered person-level records requires separate privacy/legal/disclosure review.",
            ],
        }
        (work / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
        db_path.unlink(missing_ok=True)
        work.replace(destination)
        return destination
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise
