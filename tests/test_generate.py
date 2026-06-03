import tempfile
import textwrap
import unittest
from pathlib import Path

from dvcgen.cli import main
from dvcgen.generate import dvc_document, dump_yaml, params_document
from dvcgen.inspect import ParamDeclaration, PathDeclaration, SourceDeclarations


class GenerateDocumentTest(unittest.TestCase):
    def test_builds_dvc_document_from_declarations(self):
        declarations = (
            SourceDeclarations(
                source="pipeline/train.py",
                deps=(PathDeclaration("TRAIN_DATA", "data/processed.csv", 4),),
                outs=(PathDeclaration("MODEL", "models/model.pkl", 5),),
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
                data:
                  enabled: true
                train:
                  epochs: 10
                  lr: 0.001
                """
            ),
        )


class CliGenerateTest(unittest.TestCase):
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
                    stages:
                      train:
                        cmd: python train.py
                        deps:
                          - train.py
                          - data/processed.csv
                        outs:
                          - models/model.pkl
                        params:
                          - train.lr
                    """
                ),
            )
            self.assertEqual(
                (root / "params.yaml").read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    train:
                      lr: 0.001
                    """
                ),
            )


if __name__ == "__main__":
    unittest.main()
