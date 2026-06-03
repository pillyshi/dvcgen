"""Generate DVC pipeline files from Python declarations."""

__version__ = "0.0.0"


def dep(path):
    """Declare a pipeline dependency and return its runtime value."""
    return path


def out(path):
    """Declare a pipeline output and return its runtime value."""
    return path


def param(name, default):
    """Declare a pipeline parameter and return its default runtime value."""
    return default


__all__ = ["__version__", "dep", "out", "param"]
