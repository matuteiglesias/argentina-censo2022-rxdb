from dataclasses import dataclass
from pathlib import Path


class SourceDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceDatabase:
    logical_name: str
    directory: Path
    rxdb: Path
    rbfx: tuple[Path, ...]


@dataclass(frozen=True)
class CensusSources:
    root: Path
    vp: SourceDatabase
    po_a_ig: SourceDatabase
    vc_psc: SourceDatabase


_DIRECTORY_ALIASES = {
    "VP": ("Base_VP",),
    # The April development corpus contains a historical spelling with a space.
    "PO_A_IG": ("Base_PO_A_IG", "Base_ PO_A_IG"),
    "VC_PSC": ("Base_VC_PSC",),
}


def _find_directory(root: Path, logical_name: str) -> Path:
    for name in _DIRECTORY_ALIASES[logical_name]:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    expected = ", ".join(_DIRECTORY_ALIASES[logical_name])
    raise SourceDiscoveryError(
        f"missing {logical_name} source directory; expected one of: {expected}"
    )


def _discover_database(root: Path, logical_name: str) -> SourceDatabase:
    directory = _find_directory(root, logical_name)
    rxdb = sorted(directory.glob("*.rxdb"))
    if len(rxdb) != 1:
        raise SourceDiscoveryError(
            f"{logical_name} must contain exactly one .rxdb file; found {len(rxdb)}"
        )
    rbfx = tuple(sorted(directory.glob("*.rbfx")))
    if not rbfx:
        raise SourceDiscoveryError(f"{logical_name} contains no .rbfx files")
    return SourceDatabase(logical_name, directory, rxdb[0], rbfx)


def discover_sources(root: str | Path) -> CensusSources:
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise SourceDiscoveryError(f"census source root is not a directory: {root_path}")
    return CensusSources(
        root=root_path,
        vp=_discover_database(root_path, "VP"),
        po_a_ig=_discover_database(root_path, "PO_A_IG"),
        vc_psc=_discover_database(root_path, "VC_PSC"),
    )
