import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from dvcgen.cli import main
from dvcgen.generate import dvc_document, dump_yaml, params_document
from dvcgen.inspect import (
    OutputDeclaration,
    ParamDeclaration,
    PathDeclaration,
    SourceDeclarations,
    StageDeclaration,
)


class GenerateDocumentTest(unittest.TestCase):
    def test_builds_dvc_document_from_declarations(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(PathDeclaration("TRAIN_DATA", "data/processed.csv", 4),),
                outs=(OutputDeclaration("MODEL", "models/model.pkl", 5),),
                params=(ParamDeclaration("LR", "train.lr", 0.001, 7),),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "cmd": "python pipeline/train.py",
                        "deps": [
                            "pipeline/train.py",
                            "data/processed.csv",
                        ],
                        "outs": ["models/model.pkl"],
                        "params": ["train.lr"],
                    },
                },
            },
        )

    def test_builds_dvc_document_with_output_options(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(
                    OutputDeclaration(
                        "MODEL",
                        "models/model.pkl",
                        1,
                        cache=False,
                        persist=True,
                    ),
                ),
                params=(),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "cmd": "python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                        "outs": [
                            {
                                "models/model.pkl": {
                                    "cache": False,
                                    "persist": True,
                                },
                            },
                        ],
                    },
                },
            },
        )

    def test_builds_dvc_document_with_stage_metadata(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(
                    lineno=1,
                    cmd="python -m pipeline.train",
                    wdir=".",
                    desc="Train model",
                    frozen=False,
                    always_changed=True,
                ),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "cmd": "python -m pipeline.train",
                        "deps": ["pipeline/train.py"],
                        "wdir": ".",
                        "desc": "Train model",
                        "frozen": False,
                        "always_changed": True,
                    },
                },
            },
        )

    def test_stage_cmd_override_does_not_emit_omitted_optional_fields(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, cmd="python -m pipeline.train"),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "cmd": "python -m pipeline.train",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_builds_nested_params_document_from_dotted_names(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(
                    ParamDeclaration("LR", "train.lr", 0.001, 1),
                    ParamDeclaration("EPOCHS", "train.epochs", 10, 2),
                    ParamDeclaration("AUGMENT", "data.augment.enabled", True, 3),
                ),
            ),
        )

        self.assertEqual(
            params_document(declarations),
            {
                "data": {"augment": {"enabled": True}},
                "train": {
                    "epochs": 10,
                    "lr": 0.001,
                },
            },
        )

    def test_yaml_output_is_deterministic(self):
        document = {
            "train": {
                "lr": 0.001,
                "epochs": 10,
            },
            "data": {
                "enabled": True,
            },
        }

        self.assertEqual(
            dump_yaml(document),
            textwrap.dedent(
                """\
                "data":
                  "enabled": true
                "train":
                  "epochs": 10
                  "lr": 0.001
                """
            ),
        )

    def test_yaml_quotes_strings_to_preserve_literal_values(self):
        document = {
            "train": {
                "enabled": "false",
                "empty": "",
                "label": "#prod",
                "nothing": "null",
                "ratio": "1.0",
                "with:colon": "path: value # comment",
                "escaped": 'quote " and slash \\',
            },
        }

        self.assertEqual(
            dump_yaml(document),
            textwrap.dedent(
                """\
                "train":
                  "empty": ""
                  "enabled": "false"
                  "escaped": "quote \\" and slash \\\\"
                  "label": "#prod"
                  "nothing": "null"
                  "ratio": "1.0"
                  "with:colon": "path: value # comment"
                """
            ),
        )


class CliGenerateTest(unittest.TestCase):
    def test_readme_quick_start_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pipeline = root / "pipeline"
            pipeline.mkdir()
            script = pipeline / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import dep, out, param

                    TRAIN_DATA = dep("data/processed.csv")
                    MODEL = out("models/model.pkl")

                    LR = param("train.lr", 0.001)
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["pipeline/train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "dvc.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
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
                    """
                ),
            )
            self.assertEqual(
                (root / "params.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    "train":
                      "lr": 0.001
                    """
                ),
            )

    def test_prints_concise_success_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text('MODEL = out("models/model.pkl")\n', encoding="utf-8")
            stdout = io.StringIO()

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["train.py"], stdout=stdout)
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "Wrote dvc.yaml and params.yaml\n")

    def test_writes_output_options(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import out

                    MODEL = out("models/model.pkl", cache=False, persist=True)
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "dvc.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    "stages":
                      "train":
                        "cmd": "python train.py"
                        "deps":
                          - "train.py"
                        "outs":
                          -
                            "models/model.pkl":
                              "cache": false
                              "persist": true
                    """
                ),
            )

    def test_writes_stage_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import stage

                    stage(
                        cmd="python -m pipeline.train",
                        wdir=".",
                        desc="Train model",
                        frozen=False,
                        always_changed=True,
                    )
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "dvc.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    "stages":
                      "train":
                        "always_changed": true
                        "cmd": "python -m pipeline.train"
                        "deps":
                          - "train.py"
                        "desc": "Train model"
                        "frozen": false
                        "wdir": "."
                    """
                ),
            )

    def test_requires_at_least_one_script(self):
        stderr = io.StringIO()

        exit_code = main([], stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertIn("provide at least one Python pipeline script", stderr.getvalue())

    def test_missing_input_fails_with_actionable_message(self):
        stderr = io.StringIO()

        exit_code = main(["missing.py"], stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertIn("input script not found: missing.py", stderr.getvalue())

    def test_rejects_non_python_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pipeline.txt"
            path.write_text("not python\n", encoding="utf-8")
            stderr = io.StringIO()

            exit_code = main([str(path)], stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertIn("input script must be a .py file", stderr.getvalue())

    def test_syntax_error_fails_with_actionable_message(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "train.py"
            path.write_text("if broken\n", encoding="utf-8")
            stderr = io.StringIO()

            exit_code = main([str(path)], stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertIn("failed to parse", stderr.getvalue())
        self.assertIn("expected ':'", stderr.getvalue())

    def test_refuses_to_overwrite_existing_outputs_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text('MODEL = out("models/model.pkl")\n', encoding="utf-8")
            existing_dvc = root / "dvc.yaml"
            existing_dvc.write_text("existing\n", encoding="utf-8")
            stderr = io.StringIO()

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["train.py"], stderr=stderr)
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 2)
            self.assertEqual(existing_dvc.read_text(encoding="utf-8"), "existing\n")
            self.assertIn("use --force to replace them", stderr.getvalue())

    def test_force_overwrites_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text('MODEL = out("models/model.pkl")\n', encoding="utf-8")
            (root / "dvc.yaml").write_text("existing\n", encoding="utf-8")
            (root / "params.yaml").write_text("existing\n", encoding="utf-8")

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["--force", "train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertIn('"stages":', (root / "dvc.yaml").read_text(encoding="utf-8"))
            self.assertEqual((root / "params.yaml").read_text(encoding="utf-8"), "\n")

    def test_writes_to_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            output_dir = root / "generated"
            script.write_text('MODEL = out("models/model.pkl")\n', encoding="utf-8")

            exit_code = main(["--output-dir", str(output_dir), str(script)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "dvc.yaml").exists())
            self.assertTrue((output_dir / "params.yaml").exists())

    def test_writes_dvc_and_params_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import dep, out, param

                    TRAIN_DATA = dep("data/processed.csv")
                    MODEL = out("models/model.pkl")
                    LR = param("train.lr", 0.001)
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "dvc.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    "stages":
                      "train":
                        "cmd": "python train.py"
                        "deps":
                          - "train.py"
                          - "data/processed.csv"
                        "outs":
                          - "models/model.pkl"
                        "params":
                          - "train.lr"
                    """
                ),
            )
            self.assertEqual(
                (root / "params.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    "train":
                      "lr": 0.001
                    """
                ),
            )


if __name__ == "__main__":
    unittest.main()
