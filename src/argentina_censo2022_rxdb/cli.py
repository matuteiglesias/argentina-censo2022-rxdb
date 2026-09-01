import argparse
import json

from .manifest import build_source_manifest
from .sources import discover_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arg-censo2022")
    sub = parser.add_subparsers(dest="command")

    inspect = sub.add_parser("inspect", help="inspect the local Census 2022 source corpus")
    inspect.add_argument("root")
    inspect.add_argument(
        "--release-label",
        default="unknown",
        help="explicit provenance label such as april-2025 or july-2025",
    )
    inspect.add_argument(
        "--hashes",
        action="store_true",
        help="compute SHA-256 for every RXDB/RBFX file (may take time)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "inspect":
        parser.print_help()
        return 0

    sources = discover_sources(args.root)
    manifest = build_source_manifest(
        sources,
        release_label=args.release_label,
        include_hashes=args.hashes,
    )
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0
