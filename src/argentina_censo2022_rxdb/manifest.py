from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from .sources import CensusSources, SourceDatabase


@dataclass(frozen=True)
class SourceFileManifest:
    path: str
    size: int
    sha256: str | None = None


@dataclass(frozen=True)
class SourceDatabaseManifest:
    logical_name: str
    rxdb: SourceFileManifest
    rbfx: tuple[SourceFileManifest, ...]


@dataclass(frozen=True)
class CensusSourceManifest:
    manifest_version: str
    release_label: str
    root: str
    databases: tuple[SourceDatabaseManifest, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def hash_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _file_manifest(path: Path, root: Path, *, include_hashes: bool) -> SourceFileManifest:
    relative = path.relative_to(root).as_posix()
    return SourceFileManifest(
        path=relative,
        size=path.stat().st_size,
        sha256=hash_file(path) if include_hashes else None,
    )


def _database_manifest(
    database: SourceDatabase,
    root: Path,
    *,
    include_hashes: bool,
) -> SourceDatabaseManifest:
    return SourceDatabaseManifest(
        logical_name=database.logical_name,
        rxdb=_file_manifest(database.rxdb, root, include_hashes=include_hashes),
        rbfx=tuple(
            _file_manifest(path, root, include_hashes=include_hashes)
            for path in database.rbfx
        ),
    )


def build_source_manifest(
    sources: CensusSources,
    *,
    release_label: str = "unknown",
    include_hashes: bool = False,
) -> CensusSourceManifest:
    databases: Iterable[SourceDatabase] = (
        sources.vp,
        sources.po_a_ig,
        sources.vc_psc,
    )
    return CensusSourceManifest(
        manifest_version="1",
        release_label=release_label,
        root=str(sources.root),
        databases=tuple(
            _database_manifest(db, sources.root, include_hashes=include_hashes)
            for db in databases
        ),
    )
