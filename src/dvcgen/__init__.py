"""Generate DVC pipeline files from Python declarations."""

__version__ = "0.7.0"


def stage(
    *,
    name=None,
    cmd=None,
    wdir=None,
    desc=None,
    frozen=None,
    always_changed=None,
    foreach=None,
):
    """Declare generated DVC stage metadata.

    All parameters are static-only: they are read by the dvcgen code
    generator at build time and have no effect at runtime.
    """
    return None


def dep(path):
    """Declare a pipeline dependency and return its runtime value."""
    return path


def out(
    path,
    *,
    cache=None,
    remote=None,
    persist=None,
    desc=None,
    push=None,
):
    """Declare a pipeline output and return its runtime value."""
    return path


def param(name, default):
    """Declare a pipeline parameter and return its default runtime value."""
    try:
        import yaml
        params_path = _find_params_yaml()
        if params_path is not None:
            with params_path.open() as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                cursor = data
                for part in name.split("."):
                    if not isinstance(cursor, dict) or part not in cursor:
                        return default
                    cursor = cursor[part]
                return cursor if cursor is not None else default
    except Exception:
        pass
    return default


def _find_params_yaml():
    from pathlib import Path
    path = Path.cwd()
    while True:
        candidate = path / "params.yaml"
        if candidate.exists():
            return candidate
        parent = path.parent
        if parent == path:
            return None
        path = parent


__all__ = ["__version__", "dep", "out", "param", "stage"]
