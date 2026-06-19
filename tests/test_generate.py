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

    def test_stage_name_is_stripped_in_stage_name(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name=" v1_train "),
            ),
        )

        result = dvc_document(declarations)

        self.assertIn("v1_train", result["stages"])
        self.assertNotIn(" v1_train ", result["stages"])

    def test_stage_name_override_uses_provided_name(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name="v1_train"),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "v1_train": {
                        "cmd": "python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_stage_name_defaults_to_filename_stem(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
            ),
        )

        result = dvc_document(declarations)

        self.assertIn("train", result["stages"])

    def test_stage_empty_name_raises_value_error(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name=""),
            ),
        )

        with self.assertRaisesRegex(ValueError, "empty stage name"):
            dvc_document(declarations)

    def test_stage_whitespace_only_name_raises_value_error(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name="  "),
            ),
        )

        with self.assertRaisesRegex(ValueError, "empty stage name"):
            dvc_document(declarations)

    def test_stage_duplicate_name_override_raises_value_error(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name="shared"),
            ),
            SourceDeclarations(
                source="pipeline/evaluate.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name="shared"),
            ),
        )

        with self.assertRaisesRegex(ValueError, "duplicate stage name"):
            dvc_document(declarations)

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

    def test_foreach_list_of_scalars_wraps_stage_in_do(self):
        declarations = (
            SourceDeclarations(
                source="train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, foreach=[0, 1, 2, 3, 4]),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "do": {
                            "cmd": "python train.py",
                            "deps": ["train.py"],
                        },
                        "foreach": [0, 1, 2, 3, 4],
                    },
                },
            },
        )

    def test_foreach_list_of_dicts_wraps_stage_in_do(self):
        declarations = (
            SourceDeclarations(
                source="train.py",
                deps=(),
                outs=(OutputDeclaration("MODEL", "model_${item.lr}.pkl", 2),),
                params=(),
                stage=StageDeclaration(lineno=1, foreach=[{"lr": 0.001}, {"lr": 0.01}]),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "do": {
                            "cmd": "python train.py",
                            "deps": ["train.py"],
                            "outs": ["model_${item.lr}.pkl"],
                        },
                        "foreach": [{"lr": 0.001}, {"lr": 0.01}],
                    },
                },
            },
        )

    def test_foreach_dict_wraps_stage_in_do(self):
        declarations = (
            SourceDeclarations(
                source="train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(
                    lineno=1,
                    foreach={"small": {"size": 100}, "large": {"size": 1000}},
                ),
            ),
        )

        self.assertEqual(
            dvc_document(declarations),
            {
                "stages": {
                    "train": {
                        "do": {
                            "cmd": "python train.py",
                            "deps": ["train.py"],
                        },
                        "foreach": {"large": {"size": 1000}, "small": {"size": 100}},
                    },
                },
            },
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

    def test_merges_existing_params_in_normal_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import param
                    LR = param("train.lr", 0.001)
                    EPOCHS = param("train.epochs", 10)
                    """
                ),
                encoding="utf-8",
            )
            # Existing file has lr hand-tuned; epochs is missing (will be added)
            (root / "params.yaml").write_text(
                '"train":\n  "lr": 0.5\n',
                encoding="utf-8",
            )

            exit_code = main(["--output-dir", str(root), str(script)])

            self.assertEqual(exit_code, 0)
            content = (root / "params.yaml").read_text(encoding="utf-8")
            # Hand-tuned value preserved
            self.assertIn("0.5", content)
            # New key added
            self.assertIn('"epochs"', content)
            self.assertIn("10", content)

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


class RunnerFlagTest(unittest.TestCase):
    def test_whitespace_only_runner_falls_back_to_default_cmd(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner="   "),
            {
                "stages": {
                    "train": {
                        "cmd": "python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_runner_with_trailing_space_is_stripped(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner="uv run "),
            {
                "stages": {
                    "train": {
                        "cmd": "uv run python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_empty_runner_falls_back_to_default_cmd(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner=""),
            {
                "stages": {
                    "train": {
                        "cmd": "python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_runner_applies_when_stage_has_name_but_no_cmd(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, name="custom_name"),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner="uv run"),
            {
                "stages": {
                    "custom_name": {
                        "cmd": "uv run python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_runner_prepends_to_default_cmd(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner="uv run"),
            {
                "stages": {
                    "train": {
                        "cmd": "uv run python pipeline/train.py",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_runner_ignored_when_stage_cmd_is_set(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(),
                outs=(),
                params=(),
                stage=StageDeclaration(lineno=1, cmd="custom_runner train"),
            ),
        )

        self.assertEqual(
            dvc_document(declarations, runner="uv run"),
            {
                "stages": {
                    "train": {
                        "cmd": "custom_runner train",
                        "deps": ["pipeline/train.py"],
                    },
                },
            },
        )

    def test_runner_cli_flag_prepends_to_default_cmd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import dep, out

                    DATA = dep("data/raw")
                    MODEL = out("models/model.pkl")
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["--runner", "uv run", "train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            self.assertIn(
                '"cmd": "uv run python train.py"',
                (root / "dvc.yaml").read_text(encoding="utf-8"),
            )

    def test_runner_cli_flag_ignored_when_stage_cmd_is_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            script.write_text(
                textwrap.dedent(
                    """\
                    from dvcgen import stage
                    stage(cmd="custom_runner train")
                    """
                ),
                encoding="utf-8",
            )

            original_directory = Path.cwd()
            try:
                import os

                os.chdir(root)
                exit_code = main(["--runner", "uv run", "train.py"])
            finally:
                os.chdir(original_directory)

            self.assertEqual(exit_code, 0)
            dvc_yaml = (root / "dvc.yaml").read_text(encoding="utf-8")
            self.assertIn('"cmd": "custom_runner train"', dvc_yaml)
            self.assertNotIn("uv run", dvc_yaml)


class OnlyParamsFlagTest(unittest.TestCase):
    def _write_script(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                from dvcgen import dep, param
                DATA = dep("data/train.csv")
                LR = param("train.lr", default=0.01)
                """
            ),
            encoding="utf-8",
        )

    def test_writes_params_but_not_dvc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)

            stdout = io.StringIO()
            exit_code = main(
                ["--only-params", str(script), "--output-dir", str(root)],
                stdout=stdout,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((root / "params.yaml").exists())
            self.assertFalse((root / "dvc.yaml").exists())

    def test_success_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)

            stdout = io.StringIO()
            exit_code = main(
                ["--only-params", str(script), "--output-dir", str(root)],
                stdout=stdout,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("params.yaml", stdout.getvalue())
            self.assertNotIn("dvc.yaml", stdout.getvalue())

    def test_skips_dvc_yaml_overwrite_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)
            (root / "dvc.yaml").write_text("existing", encoding="utf-8")

            exit_code = main(["--only-params", str(script), "--output-dir", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertEqual((root / "dvc.yaml").read_text(encoding="utf-8"), "existing")

    def test_merges_existing_params_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)
            # Existing file has lr hand-tuned and an extra key not in the script
            (root / "params.yaml").write_text(
                '"train":\n  "lr": 0.5\n  "extra": 99\n',
                encoding="utf-8",
            )

            exit_code = main(
                ["--only-params", str(script), "--output-dir", str(root)]
            )

            self.assertEqual(exit_code, 0)
            content = (root / "params.yaml").read_text(encoding="utf-8")
            # Existing value preserved
            self.assertIn("0.5", content)
            # Extra key preserved
            self.assertIn('"extra"', content)

    def test_force_discards_existing_params_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)
            (root / "params.yaml").write_text(
                '"train":\n  "lr": 0.5\n  "extra": 99\n',
                encoding="utf-8",
            )

            exit_code = main(
                ["--only-params", "--force", str(script), "--output-dir", str(root)]
            )

            self.assertEqual(exit_code, 0)
            content = (root / "params.yaml").read_text(encoding="utf-8")
            # Extra key from existing file must be discarded (not merged in)
            self.assertNotIn('"extra"', content)
            # Hand-edited value must not be preserved
            self.assertNotIn("0.5", content)

    def test_force_overwrites_existing_params(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)
            (root / "params.yaml").write_text("existing", encoding="utf-8")

            exit_code = main(
                ["--only-params", "--force", str(script), "--output-dir", str(root)]
            )

            self.assertEqual(exit_code, 0)
            self.assertNotEqual(
                (root / "params.yaml").read_text(encoding="utf-8"), "existing"
            )

    def test_runner_with_only_params_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "train.py"
            self._write_script(script)

            stderr = io.StringIO()
            exit_code = main(
                ["--only-params", "--runner", "uv run", str(script), "--output-dir", str(root)],
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("--runner", stderr.getvalue())
            self.assertIn("ignored", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
