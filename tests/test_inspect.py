import tempfile
import textwrap
import unittest
from pathlib import Path

from dvcgen.inspect import (
    OutputDeclaration,
    ParamDeclaration,
    PathDeclaration,
    SourceDeclarations,
    StageDeclaration,
    inspect_file,
    inspect_files,
    inspect_source,
)


class InspectSourceTest(unittest.TestCase):
    def test_extracts_readme_level_declarations(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                from dvcgen import dep, out, param, stage

                stage(cmd="python -m pipeline.train")

                TRAIN_DATA = dep("data/processed.csv")
                MODEL = out("models/model.pkl")

                LR = param("train.lr", 0.001)
                """
            ),
            source="pipeline/train.py",
        )

        self.assertEqual(
            declarations,
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(
                    PathDeclaration(
                        target="TRAIN_DATA",
                        path="data/processed.csv",
                        lineno=6,
                    ),
                ),
                outs=(
                    OutputDeclaration(
                        target="MODEL",
                        path="models/model.pkl",
                        lineno=7,
                    ),
                ),
                params=(
                    ParamDeclaration(
                        target="LR",
                        name="train.lr",
                        default=0.001,
                        lineno=9,
                    ),
                ),
                stage=StageDeclaration(
                    lineno=4,
                    cmd="python -m pipeline.train",
                ),
            ),
        )

    def test_extracts_literal_parameter_defaults(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                EPOCHS = param("train.epochs", 10)
                NAME = param("train.name", "baseline")
                ENABLED = param("train.enabled", True)
                """
            )
        )

        self.assertEqual(
            declarations.params,
            (
                ParamDeclaration("EPOCHS", "train.epochs", 10, 2),
                ParamDeclaration("NAME", "train.name", "baseline", 3),
                ParamDeclaration("ENABLED", "train.enabled", True, 4),
            ),
        )

    def test_ignores_unsupported_forms(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                import dvcgen

                dynamic_path = "data/input.csv"
                DEP = dep(dynamic_path)
                OUT = dvcgen.out("models/model.pkl")
                PARAM = param("train.lr", compute_default())
                KWARG = dep(path="data/kwarg.csv")
                FIRST = SECOND = dep("data/multiple.csv")

                def build():
                    NESTED = dep("data/nested.csv")
                """
            )
        )

        self.assertEqual(declarations.deps, ())
        self.assertEqual(declarations.outs, ())
        self.assertEqual(declarations.params, ())

    def test_does_not_execute_source_code(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                DATA = dep("data/input.csv")
                raise RuntimeError("should not execute")
                """
            )
        )

        self.assertEqual(
            declarations.deps,
            (PathDeclaration("DATA", "data/input.csv", 2),),
        )

    def test_supports_simple_annotated_assignments(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                TRAIN_DATA: str = dep("data/processed.csv")
                LR: float = param("train.lr", 0.001)
                """
            )
        )

        self.assertEqual(
            declarations.deps,
            (PathDeclaration("TRAIN_DATA", "data/processed.csv", 2),),
        )
        self.assertEqual(
            declarations.params,
            (ParamDeclaration("LR", "train.lr", 0.001, 3),),
        )

    def test_extracts_stage_metadata(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                stage(
                    cmd="python -m pipeline.train",
                    wdir=".",
                    desc="Train model",
                    frozen=False,
                    always_changed=True,
                )
                """
            )
        )

        self.assertEqual(
            declarations.stage,
            StageDeclaration(
                lineno=2,
                cmd="python -m pipeline.train",
                wdir=".",
                desc="Train model",
                frozen=False,
                always_changed=True,
            ),
        )

    def test_rejects_duplicate_stage_declarations(self):
        with self.assertRaisesRegex(ValueError, r"duplicate stage\(\) declaration"):
            inspect_source(
                textwrap.dedent(
                    """
                    stage(cmd="python train.py")
                    stage(cmd="python other.py")
                    """
                ),
                source="pipeline/train.py",
            )

    def test_ignores_stage_with_unsupported_options(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                stage(cmd=build_command())
                stage(wdir=1)
                stage(unknown=True)
                stage("python train.py")
                """
            )
        )

        self.assertIsNone(declarations.stage)


class InspectFileTest(unittest.TestCase):
    def test_inspect_file_returns_declarations_for_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pipeline.py"
            path.write_text('DATA = dep("data/input.csv")\n', encoding="utf-8")

            declarations = inspect_file(path)

        self.assertEqual(
            declarations,
            SourceDeclarations(
                source=str(path),
                deps=(PathDeclaration("DATA", "data/input.csv", 1),),
                outs=(),
                params=(),
            ),
        )

    def test_inspect_files_returns_declarations_per_file(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.py"
            second = Path(directory) / "second.py"
            first.write_text('DATA = dep("data/input.csv")\n', encoding="utf-8")
            second.write_text('MODEL = out("models/model.pkl")\n', encoding="utf-8")

            declarations = inspect_files([first, second])

        self.assertEqual(len(declarations), 2)
        self.assertEqual(
            declarations[0].deps,
            (PathDeclaration("DATA", "data/input.csv", 1),),
        )
        self.assertEqual(
            declarations[1].outs,
            (OutputDeclaration("MODEL", "models/model.pkl", 1),),
        )

    def test_extracts_output_options(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                MODEL = out(
                    "models/model.pkl",
                    cache=False,
                    remote="s3",
                    persist=True,
                    desc="trained model",
                    push=False,
                )
                """
            )
        )

        self.assertEqual(
            declarations.outs,
            (
                OutputDeclaration(
                    target="MODEL",
                    path="models/model.pkl",
                    lineno=2,
                    cache=False,
                    remote="s3",
                    persist=True,
                    desc="trained model",
                    push=False,
                ),
            ),
        )

    def test_ignores_outputs_with_unsupported_options(self):
        declarations = inspect_source(
            textwrap.dedent(
                """
                BAD_NAME = out("models/name.pkl", unknown=True)
                BAD_VALUE = out("models/value.pkl", cache="false")
                DYNAMIC = out("models/dynamic.pkl", persist=compute_value())
                """
            )
        )

        self.assertEqual(declarations.outs, ())


if __name__ == "__main__":
    unittest.main()
