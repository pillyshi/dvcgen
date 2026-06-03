"""Command-line interface for dvcgen."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys
from typing import TextIO

from dvcgen import __version__
from dvcgen.generate import write_files
from dvcgen.inspect import inspect_files


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
        "-o",
        "--output-dir",
        default=".",
        help="Directory where dvc.yaml and params.yaml are written. Defaults to the current directory.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing dvc.yaml and params.yaml files.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.scripts:
        print("dvcgen: error: provide at least one Python pipeline script", file=stderr)
        print("Try 'dvcgen --help' for usage.", file=stderr)
        return 2

    script_paths = tuple(Path(script) for script in args.scripts)
    output_dir = Path(args.output_dir)
    dvc_path = output_dir / "dvc.yaml"
    params_path = output_dir / "params.yaml"

    validation_message = _validation_error(
        script_paths,
        output_dir,
        (dvc_path, params_path),
        args.force,
    )
    if validation_message is not None:
        print(f"dvcgen: error: {validation_message}", file=stderr)
        return 2

    try:
        declarations = inspect_files(script_paths)
        write_files(declarations, dvc_path=dvc_path, params_path=params_path)
    except SyntaxError as syntax_error:
        print(
            f"dvcgen: error: failed to parse {syntax_error.filename}: {syntax_error.msg}",
            file=stderr,
        )
        return 2
    except OSError as os_error:
        print(f"dvcgen: error: {os_error}", file=stderr)
        return 2
    except ValueError as value_error:
        print(f"dvcgen: error: {value_error}", file=stderr)
        return 2

    print(f"Wrote {dvc_path} and {params_path}", file=stdout)
    return 0


def _validation_error(
    script_paths: Sequence[Path],
    output_dir: Path,
    output_paths: Sequence[Path],
    force: bool,
) -> str | None:
    for script_path in script_paths:
        if not script_path.exists():
            return f"input script not found: {script_path}"
        if not script_path.is_file():
            return f"input script is not a file: {script_path}"
        if script_path.suffix != ".py":
            return f"input script must be a .py file: {script_path}"

    if output_dir.exists() and not output_dir.is_dir():
        return f"output directory is not a directory: {output_dir}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not force:
        existing_paths = [path for path in output_paths if path.exists()]
        if existing_paths:
            joined_paths = ", ".join(str(path) for path in existing_paths)
            return f"refusing to overwrite existing file(s): {joined_paths}; use --force to replace them"

    return None
