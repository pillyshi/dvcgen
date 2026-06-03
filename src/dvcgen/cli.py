"""Command-line interface for dvcgen."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dvcgen import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dvcgen",
        description="Generate dvc.yaml and params.yaml from Python pipeline scripts.",
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
    parser.parse_args(argv)
    return 0
