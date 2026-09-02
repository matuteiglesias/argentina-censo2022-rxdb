import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from argentina_censo2022_rxdb.frame import FRAME_ARTIFACTS, CensusFrameBuildError, sha256_file
from argentina_censo2022_rxdb import validation


def _frame(root: Path) -> Path:
    (root / "payload").mkdir(parents=True)
    pq.write_table(
        pa.Table.from_pylist(
            [{"frame_household_id": "h1", "frame_dwelling_id": "v1", "department_id": "06147", "radio_id": "061471101", "household_person_count": 3}]
        ),
        root / "frame_households.parquet",
    )
    pq.write_table(
        pa.Table.from_pylist(
            [
                {"department_id": "06147", "donor_person_mass": 3},
                {"department_id": "06427", "donor_person_mass": 3},
            ]
        ),
        root / "donor_person_mass.parquet",
    )
    pq.write_table(pa.Table.from_pylist([{"frame_dwelling_id": "v1"}]), root / "payload/vivienda.parquet")
    pq.write_table(pa.Table.from_pylist([{"frame_household_id": "h1", "frame_dwelling_id": "v1"}]), root / "payload/hogar.parquet")
    pq.write_table(pa.Table.from_pylist([{"frame_person_id": "p1", "frame_household_id": "h1"}]), root / "payload/persona.parquet")
    artifacts = {
        name: {
            "sha256": sha256_file(root / name),
            "size_bytes": (root / name).stat().st_size,
        }
        for name in FRAME_ARTIFACTS
    }
    manifest = {
        "contract": "research.census-frame/v1",
        "frame_release_id": "fixture-frame",
        "country": "ARG",
        "census_vintage": 2022,
        "source_release_id": "april-2025",
        "source": {
            "partition_selection_entity": "RADIO",
            "partition_count": 2,
        },
        "counts": {
            "dwellings": 4,
            "households": 4,
            "persons": 6,
            "departments": 2,
        },
        "artifacts": artifacts,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_national_validation_applies_registered_counts_and_coverage(tmp_path: Path, monkeypatch) -> None:
    frame = _frame(tmp_path / "frame")
    monkeypatch.setattr(
        validation,
        "APRIL_2025_VP_COUNTS",
        {"VIVIENDA": 4, "HOGAR": 4, "PERSONA": 6},
    )
    monkeypatch.setattr(validation, "VP_GEOGRAPHY_COUNTS", {"RADIO": 2, "FRAC": 1})
    result = validation.validate_national_vp_frame(
        frame, source_release_label="april-2025"
    )
    assert result["status"] == "pass"
    assert result["donor_person_mass"] == 6
    assert result["department_count"] == 2
    assert result["selection_entity"] == "RADIO"


def test_national_validation_fails_on_wrong_source_total(tmp_path: Path, monkeypatch) -> None:
    frame = _frame(tmp_path / "frame")
    monkeypatch.setattr(
        validation,
        "APRIL_2025_VP_COUNTS",
        {"VIVIENDA": 4, "HOGAR": 4, "PERSONA": 7},
    )
    monkeypatch.setattr(validation, "VP_GEOGRAPHY_COUNTS", {"RADIO": 2, "FRAC": 1})
    with pytest.raises(CensusFrameBuildError, match="national_count_mismatch:PERSONA"):
        validation.validate_national_vp_frame(frame, source_release_label="april-2025")
