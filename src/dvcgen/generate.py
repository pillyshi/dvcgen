"""Generate DVC configuration files from extracted declarations."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from dvcgen.inspect import OutputDeclaration, SourceDeclarations


def _validate_stage_names(declaration_list: list[SourceDeclarations]) -> None:
    for d in declaration_list:
        if d.stage is not None and d.stage.name is not None and not d.stage.name.strip():
            raise ValueError(f"empty stage name in {d.source}")


def dvc_document(declarations: Iterable[SourceDeclarations], runner: str | None = None) -> dict[str, Any]:
    """Build a dvc.yaml document from source declarations.

    runner: optional prefix prepended to the default command (e.g. "uv run").
    Ignored when a stage declares cmd= explicitly. Falsy or whitespace-only values
    are treated as absent (stripped before use). The caller is responsible for
    ensuring runner contains only trusted input; its value is written verbatim
    into dvc.yaml.
    """
    declaration_list = list(declarations)
    _validate_stage_names(declaration_list)
    effective_runner = runner.strip() if runner else None

    stages: dict[str, dict[str, Any]] = {}

    for source_declarations, stage_name in (
        (d, _stage_name(d)) for d in sorted(declaration_list, key=_stage_name)
    ):
        if stage_name in stages:
            raise ValueError(f"duplicate stage name: {stage_name}")

        stage_metadata = source_declarations.stage
        default_cmd = f"python {source_declarations.source}"
        stage: dict[str, Any] = {
            "cmd": (
                stage_metadata.cmd
                if stage_metadata is not None and stage_metadata.cmd is not None
                else f"{effective_runner} {default_cmd}"
                if effective_runner
                else default_cmd
            ),
            "deps": [
                source_declarations.source,
                *(dep.path for dep in source_declarations.deps),
            ],
        }

        if stage_metadata is not None:
            for name in ("wdir", "desc", "frozen", "always_changed"):
                value = getattr(stage_metadata, name)
                if value is not None:
                    stage[name] = value
        if source_declarations.outs:
            stage["outs"] = [_out_entry(out) for out in source_declarations.outs]
        if source_declarations.params:
            stage["params"] = sorted(param.name for param in source_declarations.params)

        if stage_metadata is not None and stage_metadata.foreach is not None:
            stages[stage_name] = {"do": stage, "foreach": stage_metadata.foreach}
        else:
            stages[stage_name] = stage

    return {"stages": stages}


def params_document(declarations: Iterable[SourceDeclarations]) -> dict[str, Any]:
    """Build a params.yaml document from source declarations."""
    declaration_list = list(declarations)
    _validate_stage_names(declaration_list)

    params: dict[str, Any] = {}

    for source_declarations in sorted(declaration_list, key=_stage_name):
        for param in sorted(source_declarations.params, key=lambda item: item.name):
            _assign_dotted(params, param.name, param.default)

    return params


def _merge_params(existing: dict, new: dict) -> dict:
    result = dict(existing)
    for key, value in new.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_params(result[key], value)
        # else: existing value wins — do nothing
    return result


def write_files(
    declarations: Sequence[SourceDeclarations],
    dvc_path: str | Path = "dvc.yaml",
    params_path: str | Path = "params.yaml",
    runner: str | None = None,
    only_params: bool = False,
    force: bool = False,
) -> None:
    """Write dvc.yaml and/or params.yaml for the supplied declarations."""
    if not only_params:
        Path(dvc_path).write_text(
            dump_yaml(dvc_document(declarations, runner=runner)),
            encoding="utf-8",
        )
    new_params = params_document(declarations)
    params_file = Path(params_path)
    if not force and params_file.exists():
        existing = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
        new_params = _merge_params(existing, new_params)
    params_file.write_text(dump_yaml(new_params), encoding="utf-8")


def dump_yaml(value: Any) -> str:
    """Serialize a small, deterministic YAML subset."""
    return "\n".join(_yaml_lines(value, indent=0)) + "\n"


def _stage_name(declarations: SourceDeclarations) -> str:
    if declarations.stage is not None and declarations.stage.name is not None:
        return declarations.stage.name.strip()
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
