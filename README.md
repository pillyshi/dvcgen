# dvcgen

Write your DVC pipeline once, in Python.

`dvcgen` is an early-stage command-line tool for generating DVC pipeline files
from lightweight declarations embedded in Python pipeline scripts.

## Current Status

Implemented:

- A Python package named `dvcgen`
- A `dvcgen` console command
- CLI argument parsing for pipeline script paths
- CLI input validation and overwrite protection
- Public declaration helpers: `stage()`, `dep()`, `out()`, and `param()`
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

Generate DVC files from one or more Python pipeline scripts:

```bash
dvcgen pipeline/*.py
```

The command writes `dvc.yaml` and `params.yaml` in the current directory.
Stage names are derived from input Python filenames. For example,
`pipeline/train.py` becomes the `train` stage.

By default, `dvcgen` refuses to overwrite existing `dvc.yaml` or `params.yaml`
files. Use `--force` when you intentionally want to replace them:

```bash
dvcgen --force pipeline/*.py
```

Write files to another directory with `--output-dir`:

```bash
dvcgen --output-dir generated pipeline/*.py
```

Bad inputs fail with an error message and a non-zero exit code. Successful runs
print the files that were written.

Inspect declarations from Python without executing the pipeline script:

```python
from dvcgen.inspect import inspect_file

declarations = inspect_file("pipeline/train.py")
print(declarations.deps)
print(declarations.outs)
print(declarations.params)
```

## Release

Publishing is intentionally manual while the project is early stage. Build and
validate artifacts before uploading anything:

```bash
uv run python -m build
uv run twine check dist/*
```

Use TestPyPI first when rehearsing a release. Create a TestPyPI API token, then
upload with the token as the password:

```bash
uv run twine upload --repository testpypi dist/*
```

Use the production PyPI repository only when the version, changelog, and package
name decision are ready:

```bash
uv run twine upload dist/*
```

For both repositories, use `__token__` as the username and the repository API
token as the password. Avoid committing tokens or storing them in project files.

Before the first production upload, decide whether to publish the current
minimal release to reserve the `dvcgen` package name on PyPI. Once a version is
uploaded to PyPI or TestPyPI, that exact version cannot be uploaded again; bump
the version before retrying with changed artifacts.

## Planned MVP

The intended MVP is:

1. Pipeline scripts declare dependencies, outputs, and parameters in Python.
2. `dvcgen` inspects those declarations without executing the scripts.
3. `dvcgen` writes `dvc.yaml` and `params.yaml`.

Example API:

```python
from dvcgen import dep, out, param, stage

stage(
    cmd="python -m pipeline.train",
    wdir=".",
    desc="Train model",
    frozen=False,
    always_changed=False,
)

TRAIN_DATA = dep("data/processed.csv")
MODEL = out("models/model.pkl")

LR = param("train.lr", 0.001)
```

`stage()` declares metadata for the generated DVC stage. It is optional; when it
is omitted, `dvcgen` keeps the default command:

```yaml
"cmd": "python pipeline/train.py"
```

Supported stage fields are:

- `cmd`: override the command DVC runs for this stage
- `wdir`: stage working directory
- `desc`: human-readable stage description
- `frozen`: protect the stage from reproduction
- `always_changed`: always consider the stage changed

`wdir`, `desc`, `frozen`, and `always_changed` are emitted only when explicitly
provided. Each pipeline script may declare at most one `stage()`.

`out()` also accepts DVC output options as keyword arguments:

```python
MODEL = out("models/model.pkl", cache=False, persist=True)
```

Supported output options are `cache`, `remote`, `persist`, `desc`, and `push`.
Plain `out("path")` declarations continue to generate simple string entries.
Metrics and plots are separate DVC stage metadata and are not modeled as
`out()` options.

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
