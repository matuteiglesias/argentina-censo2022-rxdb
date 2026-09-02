import argparse
import json
from pathlib import Path

from .frame import CensusFrameBuildError, build_vp_slice_frame
from .frame_partitions import build_vp_partition_frame
from .manifest import build_source_manifest
from .profile import VP_PROFILE
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

    profile = sub.add_parser("profile", help="print a machine-readable extraction profile")
    profile.add_argument("name", choices=("vp",))

    frame = sub.add_parser(
        "frame",
        help="build research.census-frame/v1 from one validated rxdb-extractor VP slice",
    )
    frame.add_argument("slice", help="validated VP extraction directory")
    frame.add_argument("output_root", help="directory for immutable frame releases")
    frame.add_argument(
        "--source-release-label",
        default="unknown",
        help="source corpus label such as april-2025 or july-2025",
    )

    partition_frame = sub.add_parser(
        "frame-partitions",
        help="build one research.census-frame/v1 directly from validated RADIO partitions",
    )
    partition_frame.add_argument(
        "partition_root",
        help="rxdb extract-many output root containing completed RADIO slice directories",
    )
    partition_frame.add_argument("output_root", help="directory for immutable frame releases")
    partition_frame.add_argument(
        "--source-release-label",
        default="unknown",
        help="source corpus label such as april-2025 or july-2025",
    )
    return parser


def _frame_response(destination: Path) -> str:
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    return json.dumps(
        {
            "status": "pass",
            "output": str(destination),
            "frame_release_id": manifest["frame_release_id"],
            "contract": manifest["contract"],
            "counts": manifest["counts"],
            "geography_derivation_policy": manifest["geography_derivation_policy"],
        },
        indent=2,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            sources = discover_sources(args.root)
            manifest = build_source_manifest(
                sources,
                release_label=args.release_label,
                include_hashes=args.hashes,
            )
            print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "profile":
            print(json.dumps(VP_PROFILE.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "frame":
            destination = build_vp_slice_frame(
                Path(args.slice),
                Path(args.output_root),
                source_release_label=args.source_release_label,
            )
            print(_frame_response(destination))
            return 0

        if args.command == "frame-partitions":
            destination = build_vp_partition_frame(
                Path(args.partition_root),
                Path(args.output_root),
                source_release_label=args.source_release_label,
            )
            print(_frame_response(destination))
            return 0
    except (CensusFrameBuildError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2

    parser.print_help()
    return 0
