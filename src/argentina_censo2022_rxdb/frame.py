from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

FRAME_CONTRACT = "research.census-frame/v1"
BUILDER_VERSION = "arg-cpv2022-vp-slice-parquet/v1"
REQUIRED_SLICE_FILES = (
    "vivienda.parquet",
    "hogar.parquet",
    "persona.parquet",
    "dataset-manifest.json",
    "validation.json",
)
FRAME_ARTIFACTS = (
    "frame_households.parquet",
    "donor_person_mass.parquet",
    "payload/vivienda.parquet",
    "payload/hogar.parquet",
    "payload/persona.parquet",
)


class CensusFrameBuildError(ValueError):
    """Raised when a VP extraction cannot safely become a Census frame."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def department_from_radio_cmpcode(radio_id: str) -> str:
    """Return Argentina's five-digit department code from a RADIO cmpcode.

    This adapter-only fallback is for runtimes without ``@cmpcode``. The permanent
    Argentina fixtures establish the hierarchical prefix relation, e.g.
    FRAC ``0614711`` and RADIO ``061471101``. We therefore accept only the exact
    nine-digit RADIO form and fail closed on anything else.
    """
    value = str(radio_id)
    if len(value) != 9 or not value.isdigit():
        raise CensusFrameBuildError(f"invalid_argentina_radio_cmpcode:{value!r}")
    return value[:5]


def _require_columns(names: list[str], required: set[str], table: str) -> None:
    missing = sorted(required - set(names))
    if missing:
        raise CensusFrameBuildError(
            f"{table}:missing_required_columns:{','.join(missing)}"
        )


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusFrameBuildError(f"{label}_missing_or_invalid") from exc
    if not isinstance(value, dict):
        raise CensusFrameBuildError(f"{label}_missing_or_invalid")
    return value


def _validate_source_slice(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    missing = [name for name in REQUIRED_SLICE_FILES if not (root / name).is_file()]
    if missing:
        raise CensusFrameBuildError("missing_vp_slice_files:" + ",".join(missing))
    manifest = _load_json(root / "dataset-manifest.json", "slice_manifest")
    validation = _load_json(root / "validation.json", "slice_validation")
    if validation.get("status") != "pass":
        raise CensusFrameBuildError("vp_slice_validation_not_pass")
    return manifest, validation


def _iter_parquet_rows(
    path: Path, columns: list[str], *, batch_size: int = 65536
) -> Iterator[dict[str, object]]:
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    _require_columns(parquet.schema_arrow.names, set(columns), path.name)
    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        values = batch.to_pydict()
        for index in range(batch.num_rows):
            yield {name: values[name][index] for name in columns}


def _write_rows(path: Path, rows: Iterator[dict[str, object]], *, batch_size: int = 65536) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    buffered: list[dict[str, object]] = []
    count = 0
    try:
        for row in rows:
            buffered.append(row)
            if len(buffered) >= batch_size:
                table = pa.Table.from_pylist(buffered)
                if writer is None:
                    writer = pq.ParquetWriter(path, table.schema, compression="zstd")
                writer.write_table(table)
                count += len(buffered)
                buffered.clear()
        if buffered:
            table = pa.Table.from_pylist(buffered)
            if writer is None:
                writer = pq.ParquetWriter(path, table.schema, compression="zstd")
            writer.write_table(table)
            count += len(buffered)
        if writer is None:
            raise CensusFrameBuildError(f"cannot_write_empty_parquet:{path.name}")
    finally:
        if writer is not None:
            writer.close()
    return count


def _copy_payload_with_aliases(
    source: Path,
    destination: Path,
    aliases: tuple[tuple[str, str], ...],
    *,
    batch_size: int = 65536,
) -> int:
    """Copy a full source Parquet payload while appending neutral frame IDs."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(source)
    _require_columns(
        parquet.schema_arrow.names,
        {source_field for _, source_field in aliases},
        source.name,
    )
    collisions = {name for name, _ in aliases} & set(parquet.schema_arrow.names)
    if collisions:
        raise CensusFrameBuildError(
            "neutral_frame_id_collision:" + ",".join(sorted(collisions))
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    count = 0
    try:
        for batch in parquet.iter_batches(batch_size=batch_size):
            table = pa.Table.from_batches([batch])
            for target, source_field in aliases:
                values = table[source_field].cast(pa.string())
                table = table.append_column(target, values)
            if writer is None:
                writer = pq.ParquetWriter(destination, table.schema, compression="zstd")
            writer.write_table(table)
            count += table.num_rows
        if writer is None:
            raise CensusFrameBuildError(f"cannot_copy_empty_parquet:{source.name}")
    finally:
        if writer is not None:
            writer.close()
    return count


def _frame_geography_policy(hogar_schema_names: list[str]) -> str:
    if "XDPTO" in hogar_schema_names:
        return "redengine-dpto-cmpcode/v1"
    return "argentina-radio-prefix-fallback/v1"


def _department_id(row: dict[str, object], policy: str) -> str:
    radio = str(row.get("XRADIO") or "")
    if not radio:
        raise CensusFrameBuildError("hogar:empty_XRADIO")
    if policy == "redengine-dpto-cmpcode/v1":
        department = str(row.get("XDPTO") or "")
        if not department:
            raise CensusFrameBuildError("hogar:empty_XDPTO")
        return department
    return department_from_radio_cmpcode(radio)


def build_vp_slice_frame(
    slice_root: Path,
    output_root: Path,
    *,
    source_release_label: str = "unknown",
) -> Path:
    """Build an immutable sampler-compatible frame from one validated VP slice."""
    import pyarrow.parquet as pq

    source = Path(slice_root).expanduser().resolve()
    output_root = Path(output_root).expanduser().resolve()
    _validate_source_slice(source)
    if output_root == source or source in output_root.parents:
        raise CensusFrameBuildError("unsafe_output_path_inside_source_slice")

    schemas = {
        name: pq.ParquetFile(source / f"{name}.parquet").schema_arrow.names
        for name in ("vivienda", "hogar", "persona")
    }
    _require_columns(schemas["vivienda"], {"vivienda_key", "XRADIO"}, "VIVIENDA")
    _require_columns(
        schemas["hogar"], {"hogar_key", "vivienda_key", "XRADIO"}, "HOGAR"
    )
    _require_columns(
        schemas["persona"],
        {"persona_key", "hogar_key", "vivienda_key", "XRADIO"},
        "PERSONA",
    )

    geography_policy = _frame_geography_policy(schemas["hogar"])
    source_hashes = {
        name: sha256_file(source / name)
        for name in REQUIRED_SLICE_FILES
    }
    identity = {
        "contract": FRAME_CONTRACT,
        "builder": BUILDER_VERSION,
        "country": "ARG",
        "census_vintage": 2022,
        "source_release_label": source_release_label,
        "source_slice_manifest_sha256": source_hashes["dataset-manifest.json"],
        "source_validation_sha256": source_hashes["validation.json"],
        "geography_policy": geography_policy,
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

            hogar_columns = ["hogar_key", "vivienda_key", "XRADIO"]
            if geography_policy == "redengine-dpto-cmpcode/v1":
                hogar_columns.append("XDPTO")
            try:
                for row in _iter_parquet_rows(source / "hogar.parquet", hogar_columns):
                    hh = str(row.get("hogar_key") or "")
                    viv = str(row.get("vivienda_key") or "")
                    radio = str(row.get("XRADIO") or "")
                    if not hh or not viv or not radio:
                        raise CensusFrameBuildError("hogar:empty_relational_identity")
                    dept = _department_id(row, geography_policy)
                    conn.execute(
                        "INSERT INTO hogar(hh,viv,dept,radio) VALUES (?,?,?,?)",
                        (hh, viv, dept, radio),
                    )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise CensusFrameBuildError("hogar:duplicate_household_key") from exc

            try:
                for row in _iter_parquet_rows(
                    source / "persona.parquet", ["persona_key", "hogar_key"]
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
                raise CensusFrameBuildError("persona:duplicate_person_key") from exc

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

            frame_household_rows = (
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
            )
            household_count = _write_rows(
                work / "frame_households.parquet", frame_household_rows
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
        vivienda_count = _copy_payload_with_aliases(
            source / "vivienda.parquet",
            payload / "vivienda.parquet",
            (("frame_dwelling_id", "vivienda_key"),),
        )
        payload_households = _copy_payload_with_aliases(
            source / "hogar.parquet",
            payload / "hogar.parquet",
            (
                ("frame_household_id", "hogar_key"),
                ("frame_dwelling_id", "vivienda_key"),
            ),
        )
        payload_persons = _copy_payload_with_aliases(
            source / "persona.parquet",
            payload / "persona.parquet",
            (
                ("frame_person_id", "persona_key"),
                ("frame_household_id", "hogar_key"),
            ),
        )
        if payload_households != household_count or payload_persons != person_count:
            raise CensusFrameBuildError("payload_row_count_mismatch")

        artifacts = {
            name: {
                "sha256": sha256_file(work / name),
                "size_bytes": (work / name).stat().st_size,
            }
            for name in FRAME_ARTIFACTS
        }
        manifest = {
            "contract": FRAME_CONTRACT,
            "frame_release_id": release_id,
            "country": "ARG",
            "census_vintage": 2022,
            "builder": BUILDER_VERSION,
            "source_release_id": source_release_label,
            "source": {
                "kind": "rxdb-extractor VP relational slice",
                "slice_root_name": source.name,
                "artifacts_sha256": source_hashes,
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
                "dwellings": vivienda_count,
                "households": household_count,
                "persons": person_count,
                "departments": len(donor_rows),
            },
            "artifacts": artifacts,
            "payload_policy": "full-source-columns-plus-neutral-frame-ids/v1",
            "feature_projection": None,
            "limitations": [
                "This release represents the supplied VP extraction slice, not necessarily the national Census universe.",
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
