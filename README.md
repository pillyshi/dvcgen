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
- Public declaration helpers: `dep()`, `out()`, and `param()`
- Python script inspection for top-level literal declarations
- `dvc.yaml` generation
- `params.yaml` generation

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

The command writes `dvc.yaml` and `params.yaml` in the current directory.
Stage names are derived from input Python filenames.

Inspect declarations from Python without executing the pipeline script:

```python
from dvcgen.inspect import inspect_file

declarations = inspect_file("pipeline/train.py")
print(declarations.deps)
print(declarations.outs)
print(declarations.params)
```

## Planned MVP

The intended MVP is:

1. Pipeline scripts declare dependencies, outputs, and parameters in Python.
2. `dvcgen` inspects those declarations without executing the scripts.
3. `dvcgen` writes `dvc.yaml` and `params.yaml`.

Example API:

```python
from dvcgen import dep, out, param

TRAIN_DATA = dep("data/processed.csv")
MODEL = out("models/model.pkl")

LR = param("train.lr", 0.001)
```

Running:

```bash
dvcgen pipeline/train.py
```

Generates `dvc.yaml`:

```yaml
"stages":
  "train":
    "cmd": "python pipeline/train.py"
    "deps":
      - "pipeline/train.py"
      - "data/processed.csv"
    "outs":
      - "models/model.pkl"
    "params":
      - "train.lr"
```

And `params.yaml`:

```yaml
"train":
  "lr": 0.001
```
