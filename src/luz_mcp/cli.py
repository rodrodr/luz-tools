"""Command line: run the MCP server (default) or manage the local data from a terminal."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="luz-mcp",
                                 description="Luz y Taquígrafos + Afinidades Elegidas MCP server. "
                                             "Without a command it serves MCP over stdio.")
    ap.add_argument("--version", action="version", version=f"luz-mcp {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="serve MCP over stdio (default)")
    d = sub.add_parser("download", help="download both datasets from Harvard Dataverse and load them")
    d.add_argument("--force", action="store_true", help="download again even if current")
    sub.add_parser("status", help="show what is loaded and the checks run on import")
    sub.add_parser("reindex", help="after upgrading: reload from the files already on disk")
    args = ap.parse_args(argv)

    from . import profile  # noqa: F401  (activates the Luz profile)
    if args.cmd in (None, "serve"):
        from .server import main as serve
        serve()
        return 0
    from parlaibero_mcp import store
    from . import data
    if args.cmd == "download":
        def bar(name, done, total):
            if total and total >= 2**20:
                sys.stderr.write(f"\r  {name}: {done / 2**20:6.0f} / {total / 2**20:.0f} MB")
                if done >= total:
                    sys.stderr.write("\n")
        r = data.download_all(args.force, bar)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str), file=sys.stderr)
    elif args.cmd == "status":
        print(f"data: {store.HOME}")
        print(json.dumps(store.loaded(), ensure_ascii=False, indent=1, default=str))
        try:
            print(store.run_query("SELECT report FROM ae_checks")[1][0][0])
        except Exception:
            print("Afinidades Elegidas: not loaded")
    elif args.cmd == "reindex":
        print("  ✓", store.reindex_all(lambda c: print(f"▸ {c}", file=sys.stderr)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
