# dvcgen

Write your pipeline once, in Python.

Generate both `dvc.yaml` and `params.yaml` from lightweight declarations embedded directly in your pipeline scripts.

No duplicated metadata.
No manually maintained `dvc.yaml`.
No manually maintained `params.yaml`.

## Installation

```bash
uv tool install dvcgen
```

Or run without installing:

```bash
uvx dvcgen pipeline/*.py
```

---

## Motivation

DVC requires metadata in multiple places:

* Python code
* `dvc.yaml`
* `params.yaml`

A typical pipeline ends up maintaining the same information repeatedly.

Instead of:

```text
pipeline/
├── preprocess.py
├── train.py
├── evaluate.py
├── dvc.yaml
└── params.yaml
```

`dvcgen` treats Python as the source of truth:

```text
pipeline/
├── preprocess.py
├── train.py
└── evaluate.py
```

and generates everything else.

---

## Quick Start

### preprocess.py

```python
from dvcgen import dep, out

RAW = dep("data/raw.csv")
PROCESSED = out("data/processed.csv")


def main():
    ...
```

### train.py

```python
from dvcgen import dep, out, param

TRAIN_DATA = dep("data/processed.csv")
MODEL = out("models/model.pkl")

LR = param("train.lr", 0.001)
EPOCHS = param("train.epochs", 10)


def main():
    ...
```

Generate pipeline files:

```bash
uvx dvcgen pipeline/*.py
```

Generated:

### dvc.yaml

```yaml
stages:
  preprocess:
    cmd: python pipeline/preprocess.py
    deps:
      - pipeline/preprocess.py
      - data/raw.csv
    outs:
      - data/processed.csv

  train:
    cmd: python pipeline/train.py
    deps:
      - pipeline/train.py
      - data/processed.csv
    outs:
      - models/model.pkl
    params:
      - train.lr
      - train.epochs
```

### params.yaml

```yaml
train:
  lr: 0.001
  epochs: 10
```

---

# API

## dep()

Declare a DVC dependency.

```python
RAW = dep("data/raw.csv")
```

Adds:

```yaml
deps:
  - data/raw.csv
```

---

## out()

Declare a DVC output.

```python
MODEL = out("models/model.pkl")
```

Adds:

```yaml
outs:
  - models/model.pkl
```

---

## param()

Declare a DVC parameter and its default value.

```python
LR = param("train.lr", 0.001)
```

Adds:

```yaml
params:
  - train.lr
```

and contributes to:

```yaml
train:
  lr: 0.001
```

in `params.yaml`.

---

# Runtime Behavior

`dep()` and `out()` return the path unchanged.

```python
DATA = dep("data/raw.csv")

print(DATA)
```

```text
data/raw.csv
```

This means pipeline scripts can run normally without DVC.

Similarly:

```python
LR = param("train.lr", 0.001)
```

returns:

```python
0.001
```

by default.

---

# Parameter Loading

If a `params.yaml` file exists, `param()` automatically loads values from it.

Given:

```yaml
train:
  lr: 0.01
```

and:

```python
LR = param("train.lr", 0.001)
```

then:

```python
print(LR)
```

outputs:

```text
0.01
```

The default value is only used when the parameter is missing.

---

# Automatic DAG Inference

Dependencies between stages are inferred automatically.

### preprocess.py

```python
PROCESSED = out("data/processed.csv")
```

### train.py

```python
PROCESSED = dep("data/processed.csv")
MODEL = out("models/model.pkl")
```

`dvcgen` detects that:

```text
preprocess
    ↓
data/processed.csv
    ↓
train
```

No explicit stage ordering is required.

---

# Stage Names

Stage names are derived from filenames.

```text
pipeline/
├── preprocess.py
├── train.py
└── evaluate.py
```

Generates:

```yaml
stages:
  preprocess:
  train:
  evaluate:
```

---

# Static Analysis

`dvcgen` uses Python AST analysis.

Scripts are never executed during generation.

Only declarations are collected:

```python
dep(...)
out(...)
param(...)
```

Generation is therefore:

* fast
* deterministic
* CI-friendly
* safe

---

# Example

### preprocess.py

```python
from dvcgen import dep, out

RAW = dep("data/raw.csv")
PROCESSED = out("data/processed.csv")
```

### train.py

```python
from dvcgen import dep, out, param

TRAIN = dep("data/processed.csv")

MODEL = out("models/model.pkl")

LR = param("train.lr", 0.001)
BATCH_SIZE = param("train.batch_size", 32)
```

### evaluate.py

```python
from dvcgen import dep, out

MODEL = dep("models/model.pkl")
REPORT = out("reports/evaluation.json")
```

### Generate

```bash
uvx dvcgen pipeline/*.py
```

### Result

```text
raw.csv
   ↓
preprocess
   ↓
processed.csv
   ↓
train
   ↓
model.pkl
   ↓
evaluate
```

---

# Philosophy

DVC pipelines should be declared where they are used.

Instead of maintaining:

```text
Python
  ↓
dvc.yaml

Python
  ↓
params.yaml
```

maintain only:

```text
Python
```

and generate everything else.

Python is the source of truth.
`dvc.yaml` and `params.yaml` are build artifacts.

