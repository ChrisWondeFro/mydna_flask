"""Command line interface: ``mydna``."""

from __future__ import annotations

import argparse
import sys

from mydna import __version__
from mydna.config import Config
from mydna.data.schema import SOURCE_URL


def _cmd_serve(args: argparse.Namespace) -> int:
    from mydna import create_app

    config = Config()
    app = create_app(config)
    host = args.host or config.host
    port = args.port or config.port

    if args.dev:
        # Debug mode enables the Werkzeug debugger, which is a remote code
        # execution console. Bound to loopback and opt-in only.
        if host not in {"127.0.0.1", "localhost", "::1"}:
            print(
                "Refusing to run the debugger on a non-loopback interface.",
                file=sys.stderr,
            )
            return 2
        app.run(host=host, port=port, debug=True)
        return 0

    from waitress import serve

    print(f"MyDNA running on http://{host}:{port}", file=sys.stderr)
    print("Your genome is parsed in memory and never written to disk.", file=sys.stderr)
    serve(app, host=host, port=port, threads=4, ident="mydna")
    return 0


def _cmd_index_build(args: argparse.Namespace) -> int:
    from mydna.data.build_index import build_index

    config = Config()
    target = args.database_url or config.database_url
    source = args.source or SOURCE_URL

    print(f"Building ClinVar index at {target}", file=sys.stderr)
    print(f"Source: {source}", file=sys.stderr)

    stats = build_index(target, source)

    print(
        f"Done. Kept {stats.rows_kept:,} of {stats.rows_read:,} rows "
        f"({stats.rows_dropped:,} dropped: other assembly or no dbSNP id).",
        file=sys.stderr,
    )
    return 0


def _cmd_index_info(args: argparse.Namespace) -> int:
    from mydna.core.repository import create_index_engine
    from mydna.data.build_index import index_row_count, read_index_metadata

    config = Config()
    engine = create_index_engine(args.database_url or config.database_url)
    try:
        metadata = read_index_metadata(engine)
        if not metadata:
            print("No index found. Run `mydna index build`.", file=sys.stderr)
            return 1
        for key in sorted(metadata):
            print(f"{key}: {metadata[key]}")
        print(f"rows_present: {index_row_count(engine):,}")
    finally:
        engine.dispose()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mydna",
        description="Look up your DNA variants in a local copy of ClinVar.",
    )
    parser.add_argument("--version", action="version", version=f"mydna {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the web interface.")
    serve.add_argument("--host", help="Interface to bind (default 127.0.0.1).")
    serve.add_argument("--port", type=int, help="Port to bind (default 8000).")
    serve.add_argument(
        "--dev",
        action="store_true",
        help="Run the Flask development server with the debugger (loopback only).",
    )
    serve.set_defaults(func=_cmd_serve)

    index = subparsers.add_parser("index", help="Manage the local ClinVar index.")
    index_subparsers = index.add_subparsers(dest="index_command", required=True)

    build = index_subparsers.add_parser("build", help="Download and build the index.")
    build.add_argument(
        "--source",
        help="Path or URL of variant_summary.txt or .txt.gz (defaults to NCBI's FTP copy).",
    )
    build.add_argument("--database-url", help="Override the target database URL.")
    build.set_defaults(func=_cmd_index_build)

    info = index_subparsers.add_parser("info", help="Show index provenance.")
    info.add_argument("--database-url", help="Override the database URL.")
    info.set_defaults(func=_cmd_index_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
