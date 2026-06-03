"""Generate DVC configuration files from extracted declarations."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from dvcgen.inspect import OutputDeclaration, SourceDeclarations


def dvc_document(declarations: Iterable[SourceDeclarations]) -> dict[str, Any]:
    """Build a dvc.yaml document from source declarations."""
    stages: dict[str, dict[str, Any]] = {}

    for source_declarations in sorted(declarations, key=_stage_name):
        stage_name = _stage_name(source_declarations)
        if stage_name in stages:
            raise ValueError(f"duplicate stage name: {stage_name}")

        stage: dict[str, Any] = {
            "cmd": f"python {source_declarations.source}",
            "deps": [
                source_declarations.source,
                *(dep.path for dep in source_declarations.deps),
            ],
        }

        if source_declarations.outs:
            stage["outs"] = [_out_entry(out) for out in source_declarations.outs]
        if source_declarations.params:
            stage["params"] = sorted(param.name for param in source_declarations.params)

        stages[stage_name] = stage

    return {"stages": stages}


def params_document(declarations: Iterable[SourceDeclarations]) -> dict[str, Any]:
    """Build a params.yaml document from source declarations."""
    params: dict[str, Any] = {}

    for source_declarations in sorted(declarations, key=_stage_name):
        for param in sorted(source_declarations.params, key=lambda item: item.name):
            _assign_dotted(params, param.name, param.default)

    return params


def write_files(
    declarations: Sequence[SourceDeclarations],
    dvc_path: str | Path = "dvc.yaml",
    params_path: str | Path = "params.yaml",
) -> None:
    """Write dvc.yaml and params.yaml for the supplied declarations."""
    Path(dvc_path).write_text(
        dump_yaml(dvc_document(declarations)),
        encoding="utf-8",
    )
    Path(params_path).write_text(
        dump_yaml(params_document(declarations)),
        encoding="utf-8",
    )


def dump_yaml(value: Any) -> str:
    """Serialize a small, deterministic YAML subset."""
    return "\n".join(_yaml_lines(value, indent=0)) + "\n"


def _stage_name(declarations: SourceDeclarations) -> str:
    return Path(declarations.source).stem


def _out_entry(output: OutputDeclaration) -> str | dict[str, dict[str, Any]]:
    options = {
        name: value
        for name, value in {
            "cache": output.cache,
            "remote": output.remote,
            "persist": output.persist,
            "desc": output.desc,
            "push": output.push,
        }.items()
        if value is not None
    }
    if not options:
        return output.path
    return {output.path: options}


def _assign_dotted(document: dict[str, Any], name: str, value: Any) -> None:
    parts = name.split(".")
    if not all(parts):
        raise ValueError(f"invalid parameter name: {name}")

    cursor = document
    for part in parts[:-1]:
        existing = cursor.setdefault(part, {})
        if not isinstance(existing, dict):
            raise ValueError(f"conflicting parameter name: {name}")
        cursor = existing

    leaf = parts[-1]
    if leaf in cursor and isinstance(cursor[leaf], dict):
        raise ValueError(f"conflicting parameter name: {name}")
    cursor[leaf] = value


def _yaml_lines(value: Any, indent: int) -> list[str]:
    if isinstance(value, Mapping):
        return _mapping_lines(value, indent)
    if isinstance(value, list):
        return _list_lines(value, indent)
    return [" " * indent + _scalar(value)]


def _mapping_lines(value: Mapping[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent

    for key in sorted(value):
        item = value[key]
        yaml_key = _string(key)
        if isinstance(item, (Mapping, list)):
            lines.append(f"{prefix}{yaml_key}:")
            lines.extend(_yaml_lines(item, indent + 2))
        else:
            lines.append(f"{prefix}{yaml_key}: {_scalar(item)}")

    return lines


def _list_lines(value: list[Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent

    for item in value:
        if isinstance(item, (Mapping, list)):
            lines.append(f"{prefix}-")
            lines.extend(_yaml_lines(item, indent + 2))
        else:
            lines.append(f"{prefix}- {_scalar(item)}")

    return lines


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _string(value)
    raise TypeError(f"unsupported YAML value: {value!r}")


def _string(value: str) -> str:
    return json.dumps(value)
