from __future__ import annotations

import json
from pathlib import Path

from .controls import APRIL_2025_VP_COUNTS, VP_GEOGRAPHY_COUNTS
from .frame import FRAME_ARTIFACTS, FRAME_CONTRACT, CensusFrameBuildError, sha256_file


def _manifest(root: Path) -> dict[str, object]:
    path = root / "manifest.json"
    if not path.is_file():
        raise CensusFrameBuildError("frame_manifest_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CensusFrameBuildError("frame_manifest_invalid") from exc
    if not isinstance(payload, dict) or payload.get("contract") != FRAME_CONTRACT:
        raise CensusFrameBuildError("unexpected_frame_contract")
    if payload.get("census_vintage") != 2022:
        raise CensusFrameBuildError("unexpected_frame_vintage")
    return payload


def validate_national_vp_frame(
    root: Path,
    *,
    source_release_label: str,
) -> dict[str, object]:
    """Validate Argentina-specific national controls for a completed VP frame.

    Relational integrity is established during extraction/frame construction and can
    be independently rechecked by ``censo-sampler frame check``.  This gate owns the
    Argentina-specific facts that do not belong in the generic frame contract:
    source release identity, April national totals and expected VP geography coverage.
    """
    import pyarrow.parquet as pq

    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise CensusFrameBuildError(f"frame_root_missing:{root}")
    manifest = _manifest(root)
    if manifest.get("source_release_id") != source_release_label:
        raise CensusFrameBuildError(
            "source_release_label_mismatch:"
            f"expected={source_release_label}:observed={manifest.get('source_release_id')}"
        )

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise CensusFrameBuildError("frame_artifacts_missing")
    artifact_checks: list[dict[str, object]] = []
    for name in FRAME_ARTIFACTS:
        path = root / name
        record = artifacts.get(name)
        if not path.is_file() or not isinstance(record, dict):
            raise CensusFrameBuildError(f"frame_artifact_missing:{name}")
        expected = record.get("sha256")
        observed = sha256_file(path)
        if not isinstance(expected, str) or expected != observed:
            raise CensusFrameBuildError(f"frame_artifact_hash_mismatch:{name}")
        artifact_checks.append({"artifact": name, "sha256": observed, "passed": True})

    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise CensusFrameBuildError("frame_counts_missing")
    count_checks: list[dict[str, object]] = []
    if source_release_label == "april-2025":
        mapping = {"VIVIENDA": "dwellings", "HOGAR": "households", "PERSONA": "persons"}
        for entity, expected in APRIL_2025_VP_COUNTS.items():
            field = mapping[entity]
            observed = counts.get(field)
            if observed != expected:
                raise CensusFrameBuildError(
                    f"national_count_mismatch:{entity}:expected={expected}:observed={observed}"
                )
            count_checks.append(
                {"entity": entity, "expected": expected, "observed": observed, "passed": True}
            )
    else:
        raise CensusFrameBuildError(
            f"no_national_controls_registered_for_release:{source_release_label}"
        )

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise CensusFrameBuildError("frame_source_missing")
    selection_entity = source.get("partition_selection_entity")
    partition_checks: list[dict[str, object]] = []
    if selection_entity in {"RADIO", "FRAC"}:
        expected_partitions = VP_GEOGRAPHY_COUNTS[str(selection_entity)]
        observed_partitions = source.get("partition_count")
        if observed_partitions != expected_partitions:
            raise CensusFrameBuildError(
                "national_partition_count_mismatch:"
                f"{selection_entity}:expected={expected_partitions}:observed={observed_partitions}"
            )
        partition_checks.append(
            {
                "selection_entity": selection_entity,
                "expected": expected_partitions,
                "observed": observed_partitions,
                "passed": True,
            }
        )
    else:
        raise CensusFrameBuildError("national_frame_requires_partition_set_provenance")

    donor = pq.read_table(
        root / "donor_person_mass.parquet",
        columns=["department_id", "donor_person_mass"],
    )
    donor_mass = sum(int(value) for value in donor["donor_person_mass"].to_pylist())
    expected_persons = APRIL_2025_VP_COUNTS["PERSONA"]
    if donor_mass != expected_persons:
        raise CensusFrameBuildError(
            f"national_donor_mass_mismatch:expected={expected_persons}:observed={donor_mass}"
        )
    observed_departments = donor.num_rows
    manifest_departments = counts.get("departments")
    if manifest_departments != observed_departments:
        raise CensusFrameBuildError(
            "national_department_manifest_mismatch:"
            f"manifest={manifest_departments}:observed={observed_departments}"
        )

    return {
        "status": "pass",
        "contract": FRAME_CONTRACT,
        "frame_release_id": manifest.get("frame_release_id"),
        "source_release_id": source_release_label,
        "selection_entity": selection_entity,
        "counts": counts,
        "donor_person_mass": donor_mass,
        "department_count": observed_departments,
        "artifact_checks": artifact_checks,
        "count_checks": count_checks,
        "partition_checks": partition_checks,
    }
