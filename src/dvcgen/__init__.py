"""Generate DVC pipeline files from Python declarations."""

__version__ = "0.1.0"


def stage(
    *,
    cmd=None,
    wdir=None,
    desc=None,
    frozen=None,
    always_changed=None,
):
    """Declare generated DVC stage metadata."""
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
    return default


__all__ = ["__version__", "dep", "out", "param", "stage"]
