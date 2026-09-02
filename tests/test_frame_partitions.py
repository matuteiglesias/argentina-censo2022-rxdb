import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from argentina_censo2022_rxdb.frame import CensusFrameBuildError, sha256_file
from argentina_censo2022_rxdb.frame_partitions import build_vp_partition_frame


def _write_partition(
    root: Path,
    radio: str,
    *,
    selection_entity: str = "RADIO",
    selection_code: str | None = None,
    include_dpto: bool = False,
) -> None:
    root.mkdir(parents=True)
    selection_code = selection_code or radio
    vivienda = [
        {"vivienda_key": f"{radio}:1", "XRADIO": radio, "V01": 1},
        {"vivienda_key": f"{radio}:2", "XRADIO": radio, "V01": 2},
    ]
    hogar = [
        {"hogar_key": f"{radio}:1", "vivienda_key": f"{radio}:1", "XRADIO": radio, "H10": 1},
        {"hogar_key": f"{radio}:2", "vivienda_key": f"{radio}:2", "XRADIO": radio, "H10": 2},
    ]
    persona = [
        {"persona_key": f"{radio}:1", "hogar_key": f"{radio}:1", "vivienda_key": f"{radio}:1", "XRADIO": radio, "P02": 1},
        {"persona_key": f"{radio}:2", "hogar_key": f"{radio}:1", "vivienda_key": f"{radio}:1", "XRADIO": radio, "P02": 2},
        {"persona_key": f"{radio}:3", "hogar_key": f"{radio}:2", "vivienda_key": f"{radio}:2", "XRADIO": radio, "P02": 1},
    ]
    if include_dpto:
        for rows in (vivienda, hogar, persona):
            for row in rows:
                row["XDPTO"] = radio[:5]

    for entity, rows in (("VIVIENDA", vivienda), ("HOGAR", hogar), ("PERSONA", persona)):
        path = root / f"{entity.lower()}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), path)

    entities = {}
    for entity in ("VIVIENDA", "HOGAR", "PERSONA"):
        path = root / f"{entity.lower()}.parquet"
        entities[entity] = {
            "artifact": {
                "path": path.name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "rows": pq.ParquetFile(path).metadata.num_rows,
            }
        }
    manifest = {
        "manifest_version": "1",
        "selection": {"entity": selection_entity, "code": selection_code},
        "identity_scope": "RADIO",
        "scope_field": "XRADIO",
        "scope_source": "cmpcode" if include_dpto else "selection-code-fallback",
        "entities": entities,
        "validation_status": "pass",
        "semantic_hash": f"fixture-{selection_entity}-{selection_code}",
    }
    (root / "dataset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "validation.json").write_text(json.dumps({"status": "pass"}), encoding="utf-8")


def test_partition_frame_streams_multiple_radios_into_one_frame(tmp_path: Path) -> None:
    run = tmp_path / "vp-run"
    run.mkdir()
    _write_partition(run / "radio=061471101", "061471101")
    _write_partition(run / "radio=064279901", "064279901")
    (run / "run-manifest.json").write_text(
        json.dumps({"status": "pass", "source_hash": "source-fixture"}),
        encoding="utf-8",
    )

    frame = build_vp_partition_frame(
        run, tmp_path / "frames", source_release_label="april-2025"
    )
    manifest = json.loads((frame / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract"] == "research.census-frame/v1"
    assert manifest["counts"] == {
        "dwellings": 4,
        "households": 4,
        "persons": 6,
        "departments": 2,
        "partitions": 2,
        "radio_partitions": 2,
    }
    assert manifest["source"]["partition_count"] == 2
    assert manifest["source"]["partition_selection_entity"] == "RADIO"
    assert manifest["source"]["run_source_hash"] == "source-fixture"
    assert manifest["geography_derivation_policy"] == "argentina-radio-prefix-fallback/v1"

    donor = pq.read_table(frame / "donor_person_mass.parquet").to_pylist()
    assert donor == [
        {"department_id": "06147", "donor_person_mass": 3},
        {"department_id": "06427", "donor_person_mass": 3},
    ]
    households = pq.read_table(frame / "frame_households.parquet").to_pylist()
    assert len(households) == 4
    assert {row["radio_id"] for row in households} == {"061471101", "064279901"}
    assert pq.read_table(frame / "payload/persona.parquet").num_rows == 6
    assert (frame / "partition-index.json").is_file()


def test_partition_frame_supports_frac_selection_with_radio_identity(tmp_path: Path) -> None:
    run = tmp_path / "vp-frac-run"
    run.mkdir()
    _write_partition(
        run / "frac=0614711",
        "061471101",
        selection_entity="FRAC",
        selection_code="0614711",
        include_dpto=True,
    )
    _write_partition(
        run / "frac=0642799",
        "064279901",
        selection_entity="FRAC",
        selection_code="0642799",
        include_dpto=True,
    )

    frame = build_vp_partition_frame(run, tmp_path / "frames")
    manifest = json.loads((frame / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["partition_selection_entity"] == "FRAC"
    assert manifest["counts"]["frac_partitions"] == 2
    assert manifest["counts"]["partitions"] == 2
    assert manifest["geography_derivation_policy"] == "redengine-dpto-cmpcode/v1"
    households = pq.read_table(frame / "frame_households.parquet").to_pylist()
    assert {row["radio_id"] for row in households} == {"061471101", "064279901"}


def test_frac_partition_without_cmpcode_geography_is_rejected(tmp_path: Path) -> None:
    run = tmp_path / "vp-frac-run"
    run.mkdir()
    _write_partition(
        run / "frac=0614711",
        "061471101",
        selection_entity="FRAC",
        selection_code="0614711",
        include_dpto=False,
    )
    with pytest.raises(CensusFrameBuildError, match="frac_partitions_require_cmpcode"):
        build_vp_partition_frame(run, tmp_path / "frames")


def test_partition_frame_rejects_tampered_source_artifact(tmp_path: Path) -> None:
    run = tmp_path / "vp-run"
    run.mkdir()
    partition = run / "radio=061471101"
    _write_partition(partition, "061471101")

    # Keep a perfectly readable Parquet file but change its bytes after the slice
    # manifest was written. The partition-frame custody check must catch this.
    person_path = partition / "persona.parquet"
    rows = pq.read_table(person_path).to_pylist()
    rows[0]["P02"] = 99
    pq.write_table(pa.Table.from_pylist(rows), person_path)

    with pytest.raises(CensusFrameBuildError, match="artifact_hash_mismatch"):
        build_vp_partition_frame(run, tmp_path / "frames")
