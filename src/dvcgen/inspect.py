"""Inspect Python pipeline scripts for dvcgen declarations."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Union


@dataclass(frozen=True)
class PathDeclaration:
    """A dependency or output declaration extracted from source code."""

    target: str
    path: str
    lineno: int


@dataclass(frozen=True)
class OutputDeclaration:
    """An output declaration extracted from source code."""

    target: str
    path: str
    lineno: int
    cache: Optional[bool] = None
    remote: Optional[str] = None
    persist: Optional[bool] = None
    desc: Optional[str] = None
    push: Optional[bool] = None


@dataclass(frozen=True)
class ParamDeclaration:
    """A parameter declaration extracted from source code."""

    target: str
    name: str
    default: Any
    lineno: int


@dataclass(frozen=True)
class StageDeclaration:
    """Stage metadata extracted from source code."""

    lineno: int
    name: Optional[str] = None
    cmd: Optional[str] = None
    wdir: Optional[str] = None
    desc: Optional[str] = None
    frozen: Optional[bool] = None
    always_changed: Optional[bool] = None


@dataclass(frozen=True)
class SourceDeclarations:
    """Declarations extracted from a single Python source file."""

    source: str
    deps: tuple[PathDeclaration, ...]
    outs: tuple[OutputDeclaration, ...]
    params: tuple[ParamDeclaration, ...]
    stage: Optional[StageDeclaration] = None


PathLike = Union[str, Path]


def inspect_file(path: PathLike) -> SourceDeclarations:
    """Parse a Python file and return supported dvcgen declarations."""
    source_path = Path(path)
    return inspect_source(
        source_path.read_text(encoding="utf-8"),
        source=str(source_path),
    )


def inspect_files(paths: Iterable[PathLike]) -> tuple[SourceDeclarations, ...]:
    """Parse multiple Python files and return declarations per file."""
    return tuple(inspect_file(path) for path in paths)


def inspect_source(source_code: str, source: str = "<string>") -> SourceDeclarations:
    """Parse Python source and return supported top-level declarations."""
    tree = ast.parse(source_code, filename=source)
    deps: list[PathDeclaration] = []
    outs: list[OutputDeclaration] = []
    params: list[ParamDeclaration] = []
    stage_declaration: Optional[StageDeclaration] = None

    for statement in tree.body:
        expression_call = _expression_call(statement)
        if expression_call is not None and _simple_call_name(expression_call) == "stage":
            new_declaration = _stage_declaration(expression_call)
            if new_declaration is not None:
                if stage_declaration is not None:
                    raise ValueError(f"duplicate stage() declaration in {source}")
                stage_declaration = new_declaration
            continue

        target = _assignment_target(statement)
        if target is None:
            continue

        value = _assignment_value(statement)
        if not isinstance(value, ast.Call):
            continue

        call_name = _simple_call_name(value)
        if call_name == "dep":
            path_declaration = _path_declaration(target, value)
            if path_declaration is not None:
                deps.append(path_declaration)
        elif call_name == "out":
            output_declaration = _output_declaration(target, value)
            if output_declaration is not None:
                outs.append(output_declaration)
        elif call_name == "param":
            param_declaration = _param_declaration(target, value)
            if param_declaration is not None:
                params.append(param_declaration)

    return SourceDeclarations(
        source=source,
        deps=tuple(deps),
        outs=tuple(outs),
        params=tuple(params),
        stage=stage_declaration,
    )


def _expression_call(statement: ast.stmt) -> Optional[ast.Call]:
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return statement.value
    return None


def _assignment_target(statement: ast.stmt) -> Optional[str]:
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
    elif isinstance(statement, ast.AnnAssign) and statement.simple:
        target = statement.target
    else:
        return None

    if isinstance(target, ast.Name):
        return target.id
    return None


def _assignment_value(statement: ast.stmt) -> Optional[ast.expr]:
    if isinstance(statement, ast.Assign):
        return statement.value
    if isinstance(statement, ast.AnnAssign):
        return statement.value
    return None


def _simple_call_name(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _path_declaration(target: str, call: ast.Call) -> Optional[PathDeclaration]:
    if len(call.args) != 1 or call.keywords:
        return None

    path = _literal(call.args[0])
    if not isinstance(path, str):
        return None

    return PathDeclaration(target=target, path=path, lineno=call.lineno)


def _output_declaration(target: str, call: ast.Call) -> Optional[OutputDeclaration]:
    if len(call.args) != 1:
        return None

    path = _literal(call.args[0])
    if not isinstance(path, str):
        return None

    options: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg not in _OUTPUT_OPTION_TYPES:
            return None
        value = _literal(keyword.value)
        if value is _UNSUPPORTED:
            return None
        expected_type = _OUTPUT_OPTION_TYPES[keyword.arg]
        if not isinstance(value, expected_type):
            return None
        options[keyword.arg] = value

    return OutputDeclaration(
        target=target,
        path=path,
        lineno=call.lineno,
        **options,
    )


def _param_declaration(target: str, call: ast.Call) -> Optional[ParamDeclaration]:
    if len(call.args) != 2 or call.keywords:
        return None

    name = _literal(call.args[0])
    if not isinstance(name, str):
        return None

    default = _literal(call.args[1])
    if default is _UNSUPPORTED:
        return None

    return ParamDeclaration(
        target=target,
        name=name,
        default=default,
        lineno=call.lineno,
    )


def _stage_declaration(call: ast.Call) -> Optional[StageDeclaration]:
    if call.args:
        return None

    options: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg not in _STAGE_OPTION_TYPES:
            return None
        value = _literal(keyword.value)
        if value is _UNSUPPORTED:
            return None
        expected_type = _STAGE_OPTION_TYPES[keyword.arg]
        if not isinstance(value, expected_type):
            return None
        options[keyword.arg] = value

    if "name" in options:
        options["name"] = options["name"].strip()
        if not options["name"]:
            del options["name"]

    return StageDeclaration(lineno=call.lineno, **options)


_UNSUPPORTED = object()
_OUTPUT_OPTION_TYPES = {
    "cache": bool,
    "remote": str,
    "persist": bool,
    "desc": str,
    "push": bool,
}
_STAGE_OPTION_TYPES = {
    "name": str,
    "cmd": str,
    "wdir": str,
    "desc": str,
    "frozen": bool,
    "always_changed": bool,
}


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return _UNSUPPORTED
