import hashlib
import json

from argentina_censo2022_rxdb.cli import main
from argentina_censo2022_rxdb.manifest import build_source_manifest, hash_file
from argentina_censo2022_rxdb.sources import discover_sources


def _make_sources(tmp_path):
    specs = {
        "Base_VP": ("cpv2022.rxdb", "cpv2022-000.rbfx"),
        "Base_PO_A_IG": ("cpv2022.rxdb", "cpv2022-000.rbfx"),
        "Base_VC_PSC": ("cpv2022_col.rxdb", "cpv2022_col-000.rbfx"),
    }
    for dirname, (rxdb, rbfx) in specs.items():
        directory = tmp_path / dirname
        directory.mkdir()
        (directory / rxdb).write_bytes(f"{dirname}-rxdb".encode())
        (directory / rbfx).write_bytes(f"{dirname}-rbfx".encode())
    return tmp_path


def test_hash_file_is_sha256(tmp_path):
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    assert hash_file(path) == hashlib.sha256(b"abc").hexdigest()


def test_source_manifest_is_relative_and_hash_optional(tmp_path):
    root = _make_sources(tmp_path)
    sources = discover_sources(root)
    manifest = build_source_manifest(
        sources, release_label="april-2025", include_hashes=False
    ).to_dict()

    assert manifest["release_label"] == "april-2025"
    assert [db["logical_name"] for db in manifest["databases"]] == [
        "VP",
        "PO_A_IG",
        "VC_PSC",
    ]
    assert manifest["databases"][0]["rxdb"]["path"] == "Base_VP/cpv2022.rxdb"
    assert manifest["databases"][0]["rxdb"]["sha256"] is None


def test_source_manifest_hashes_all_files(tmp_path):
    root = _make_sources(tmp_path)
    manifest = build_source_manifest(
        discover_sources(root), include_hashes=True
    ).to_dict()

    files = []
    for database in manifest["databases"]:
        files.append(database["rxdb"])
        files.extend(database["rbfx"])
    assert files
    assert all(item["size"] > 0 for item in files)
    assert all(len(item["sha256"]) == 64 for item in files)


def test_cli_inspect_emits_manifest(tmp_path, capsys):
    root = _make_sources(tmp_path)
    assert main(["inspect", str(root), "--release-label", "test-release"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["release_label"] == "test-release"
    assert len(payload["databases"]) == 3
