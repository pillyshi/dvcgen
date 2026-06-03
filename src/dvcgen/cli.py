"""Command-line interface for dvcgen."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dvcgen import __version__
from dvcgen.generate import write_files
from dvcgen.inspect import inspect_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dvcgen",
        description="Initial dvcgen CLI scaffold for Python pipeline script paths.",
    )
    parser.add_argument(
        "scripts",
        nargs="*",
        help="Python pipeline scripts to inspect.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.scripts:
        write_files(inspect_files(args.scripts))
    return 0
