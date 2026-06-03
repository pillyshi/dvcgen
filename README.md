# dvcgen

Write your DVC pipeline once, in Python.

`dvcgen` is an early-stage command-line tool for generating DVC pipeline files
from lightweight declarations embedded in Python pipeline scripts.

## Current Status

This package is currently in scaffold form.

Implemented today:

- A Python package named `dvcgen`
- A `dvcgen` console command
- CLI argument parsing for pipeline script paths

Not implemented yet:

- Public declaration helpers such as `dep()`, `out()`, and `param()`
- Python script inspection
- `dvc.yaml` generation
- `params.yaml` generation

Those features are planned for the first MVP milestone.

## Installation

```bash
uv tool install dvcgen
```

Or run without installing:

```bash
uvx dvcgen --help
```

## Usage

Show CLI help:

```bash
dvcgen --help
```

The command currently accepts Python pipeline scripts as positional arguments:

```bash
dvcgen pipeline/preprocess.py pipeline/train.py
```

At this stage, the command validates the CLI shape and exits without generating
files. Generation behavior will be added in later MVP issues.

## Planned MVP

The intended MVP is:

1. Pipeline scripts declare dependencies, outputs, and parameters in Python.
2. `dvcgen` inspects those declarations without executing the scripts.
3. `dvcgen` writes `dvc.yaml` and `params.yaml`.

Example of the planned API:

```python
from dvcgen import dep, out, param

TRAIN_DATA = dep("data/processed.csv")
MODEL = out("models/model.pkl")

LR = param("train.lr", 0.001)
```

This API is not available yet.
