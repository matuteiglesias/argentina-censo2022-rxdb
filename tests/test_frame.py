import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from argentina_censo2022_rxdb.frame import (
    CensusFrameBuildError,
    build_vp_slice_frame,
    department_from_radio_cmpcode,
    sha256_file,
)


def _write_slice(root: Path, *, include_dpto: bool = False, validation_status: str = "pass"):
    root.mkdir()
    radio = "061471101"

    vivienda = [
        {"vivienda_key": f"{radio}:1", "XRADIO": radio, "V01": 1},
        {"vivienda_key": f"{radio}:2", "XRADIO": radio, "V01": 2},
    ]
    hogar = [
        {
            "hogar_key": f"{radio}:1",
            "vivienda_key": f"{radio}:1",
            "XRADIO": radio,
            "H10": 1,
        },
        {
            "hogar_key": f"{radio}:2",
            "vivienda_key": f"{radio}:2",
            "XRADIO": radio,
            "H10": 2,
        },
    ]
    persona = [
        {
            "persona_key": f"{radio}:1",
            "hogar_key": f"{radio}:1",
            "vivienda_key": f"{radio}:1",
            "XRADIO": radio,
            "P02": 1,
        },
        {
            "persona_key": f"{radio}:2",
            "hogar_key": f"{radio}:1",
            "vivienda_key": f"{radio}:1",
            "XRADIO": radio,
            "P02": 2,
        },
        {
            "persona_key": f"{radio}:3",
            "hogar_key": f"{radio}:2",
            "vivienda_key": f"{radio}:2",
            "XRADIO": radio,
            "P02": 1,
        },
    ]
    if include_dpto:
        for rows in (vivienda, hogar, persona):
            for row in rows:
                row["XDPTO"] = "06147"

    pq.write_table(pa.Table.from_pylist(vivienda), root / "vivienda.parquet")
    pq.write_table(pa.Table.from_pylist(hogar), root / "hogar.parquet")
    pq.write_table(pa.Table.from_pylist(persona), root / "persona.parquet")
    (root / "dataset-manifest.json").write_text(
        json.dumps({"contract": "rxdb.dataset-slice/v1", "fixture": True}),
        encoding="utf-8",
    )
    (root / "validation.json").write_text(
        json.dumps({"status": validation_status}), encoding="utf-8"
    )


def test_department_prefix_fallback_is_bounded():
    assert department_from_radio_cmpcode("061471101") == "06147"
    with pytest.raises(CensusFrameBuildError, match="invalid_argentina_radio_cmpcode"):
        department_from_radio_cmpcode("06147")
    with pytest.raises(CensusFrameBuildError, match="invalid_argentina_radio_cmpcode"):
        department_from_radio_cmpcode("06147A101")


def test_build_vp_slice_frame_preserves_full_payload_and_builds_index(tmp_path):
    source = tmp_path / "slice"
    _write_slice(source)

    frame = build_vp_slice_frame(
        source, tmp_path / "frames", source_release_label="april-2025"
    )
    manifest = json.loads((frame / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["contract"] == "research.census-frame/v1"
    assert manifest["census_vintage"] == 2022
    assert manifest["source_release_id"] == "april-2025"
    assert manifest["geography_derivation_policy"] == "argentina-radio-prefix-fallback/v1"
    assert manifest["counts"] == {
        "dwellings": 2,
        "households": 2,
        "persons": 3,
        "departments": 1,
    }
    for name, record in manifest["artifacts"].items():
        assert record["sha256"] == sha256_file(frame / name)

    households = pq.read_table(frame / "frame_households.parquet").to_pylist()
    assert households == [
        {
            "frame_household_id": "061471101:1",
            "frame_dwelling_id": "061471101:1",
            "department_id": "06147",
            "radio_id": "061471101",
            "household_person_count": 2,
        },
        {
            "frame_household_id": "061471101:2",
            "frame_dwelling_id": "061471101:2",
            "department_id": "06147",
            "radio_id": "061471101",
            "household_person_count": 1,
        },
    ]
    assert pq.read_table(frame / "donor_person_mass.parquet").to_pylist() == [
        {"department_id": "06147", "donor_person_mass": 3}
    ]

    vivienda_schema = pq.read_schema(frame / "payload/vivienda.parquet").names
    hogar_schema = pq.read_schema(frame / "payload/hogar.parquet").names
    persona_schema = pq.read_schema(frame / "payload/persona.parquet").names
    assert "V01" in vivienda_schema
    assert "H10" in hogar_schema
    assert "P02" in persona_schema
    assert "frame_dwelling_id" in vivienda_schema
    assert {"frame_household_id", "frame_dwelling_id"} <= set(hogar_schema)
    assert {"frame_person_id", "frame_household_id"} <= set(persona_schema)


def test_engine_department_cmpcode_is_preferred_when_present(tmp_path):
    source = tmp_path / "slice"
    _write_slice(source, include_dpto=True)
    frame = build_vp_slice_frame(source, tmp_path / "frames")
    manifest = json.loads((frame / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["geography_derivation_policy"] == "redengine-dpto-cmpcode/v1"
    donor = pq.read_table(frame / "donor_person_mass.parquet").to_pylist()
    assert donor == [{"department_id": "06147", "donor_person_mass": 3}]


def test_failed_extractor_slice_is_rejected(tmp_path):
    source = tmp_path / "slice"
    _write_slice(source, validation_status="fail")
    with pytest.raises(CensusFrameBuildError, match="vp_slice_validation_not_pass"):
        build_vp_slice_frame(source, tmp_path / "frames")
