import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from argentina_censo2022_rxdb.frame import CensusFrameBuildError
from argentina_censo2022_rxdb.partition_inventory import build_partition_inventory


def test_parquet_radio_inventory_zero_pads_and_deduplicates(tmp_path: Path) -> None:
    source = tmp_path / "geo.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {"IDRADIO": 61471101},
                {"IDRADIO": 61471101},
                {"IDRADIO": 64279901},
            ]
        ),
        source,
    )
    output = tmp_path / "radios.json"
    build_partition_inventory(
        source,
        output,
        level="RADIO",
        column="IDRADIO",
        expected_count=2,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["partition_level"] == "RADIO"
    assert payload["partitions"] == ["061471101", "064279901"]
    assert payload["partition_count"] == 2
    assert payload["source"]["column"] == "IDRADIO"


def test_frac_inventory_uses_seven_digit_codes(tmp_path: Path) -> None:
    source = tmp_path / "frac.csv"
    source.write_text("IDFRAC\n614711\n642799\n", encoding="utf-8")
    output = tmp_path / "frac.json"
    build_partition_inventory(
        source,
        output,
        level="FRAC",
        column="IDFRAC",
        expected_count=2,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["partitions"] == ["0614711", "0642799"]


def test_partition_count_control_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "radios.txt"
    source.write_text("061471101\n", encoding="utf-8")
    with pytest.raises(CensusFrameBuildError, match="partition_count_mismatch"):
        build_partition_inventory(
            source,
            tmp_path / "out.json",
            level="RADIO",
            expected_count=2,
        )
