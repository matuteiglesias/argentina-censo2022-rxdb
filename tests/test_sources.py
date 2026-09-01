from pathlib import Path

import pytest

from argentina_censo2022_rxdb.sources import SourceDiscoveryError, discover_sources


def create_db(root: Path, dirname: str, rxdb: str, rbfx_count: int = 1):
    d = root / dirname
    d.mkdir()
    (d / rxdb).write_text("fixture")
    for i in range(rbfx_count):
        (d / f"block-{i:03d}.rbfx").write_text("fixture")


def test_discovers_april_historical_directory_spelling(tmp_path):
    create_db(tmp_path, "Base_VP", "cpv2022.rxdb", 2)
    create_db(tmp_path, "Base_ PO_A_IG", "cpv2022.rxdb", 3)
    create_db(tmp_path, "Base_VC_PSC", "cpv2022_col.rxdb", 1)
    sources = discover_sources(tmp_path)
    assert sources.vp.rxdb.name == "cpv2022.rxdb"
    assert sources.po_a_ig.directory.name == "Base_ PO_A_IG"
    assert len(sources.po_a_ig.rbfx) == 3


def test_prefers_canonical_po_directory_name(tmp_path):
    create_db(tmp_path, "Base_VP", "cpv2022.rxdb")
    create_db(tmp_path, "Base_PO_A_IG", "cpv2022.rxdb")
    create_db(tmp_path, "Base_VC_PSC", "cpv2022_col.rxdb")
    assert discover_sources(tmp_path).po_a_ig.directory.name == "Base_PO_A_IG"


def test_missing_family_fails_closed(tmp_path):
    create_db(tmp_path, "Base_VP", "cpv2022.rxdb")
    with pytest.raises(SourceDiscoveryError, match="PO_A_IG"):
        discover_sources(tmp_path)


def test_multiple_rxdb_files_are_rejected(tmp_path):
    create_db(tmp_path, "Base_VP", "cpv2022.rxdb")
    (tmp_path / "Base_VP" / "other.rxdb").write_text("fixture")
    create_db(tmp_path, "Base_PO_A_IG", "cpv2022.rxdb")
    create_db(tmp_path, "Base_VC_PSC", "cpv2022_col.rxdb")
    with pytest.raises(SourceDiscoveryError, match="exactly one"):
        discover_sources(tmp_path)
