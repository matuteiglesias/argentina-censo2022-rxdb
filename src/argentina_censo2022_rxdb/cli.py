import argparse
import json

from .sources import discover_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arg-censo2022")
    sub = parser.add_subparsers(dest="command")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("root")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "inspect":
        parser.print_help()
        return 0
    sources = discover_sources(args.root)
    payload = {
        name: {
            "rxdb": str(getattr(sources, attr).rxdb),
            "rbfx_count": len(getattr(sources, attr).rbfx),
        }
        for name, attr in (("VP", "vp"), ("PO_A_IG", "po_a_ig"), ("VC_PSC", "vc_psc"))
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
