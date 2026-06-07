import os
import unittest

from dvcgen import dep, out, param, stage


class RuntimeApiTest(unittest.TestCase):
    def test_dep_returns_path(self):
        self.assertEqual(dep("data/input.csv"), "data/input.csv")

    def test_out_returns_path(self):
        self.assertEqual(out("models/model.pkl"), "models/model.pkl")

    def test_out_accepts_dvc_output_options(self):
        self.assertEqual(
            out("models/model.pkl", cache=False, persist=True),
            "models/model.pkl",
        )

    def test_param_returns_default_when_no_params_yaml(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            orig = os.getcwd()
            try:
                os.chdir(d)
                self.assertEqual(param("train.lr", 0.001), 0.001)
            finally:
                os.chdir(orig)

    def test_stage_returns_no_runtime_value(self):
        self.assertIsNone(
            stage(
                cmd="python -m pipeline.train",
                wdir=".",
                desc="Train model",
                frozen=False,
                always_changed=True,
            )
        )


class ParamRuntimeResolutionTest(unittest.TestCase):
    def setUp(self):
        self._orig_dir = os.getcwd()

    def tearDown(self):
        os.chdir(self._orig_dir)

    def _write_params(self, tmp_path, content):
        params_file = tmp_path / "params.yaml"
        params_file.write_text(content)
        os.chdir(tmp_path)

    def test_reads_flat_key_from_params_yaml(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "lr: 0.01\n")
            self.assertEqual(param("lr", 0.001), 0.01)

    def test_reads_nested_key_from_params_yaml(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "train:\n  lr: 0.01\n  epochs: 20\n")
            self.assertAlmostEqual(param("train.lr", 0.001), 0.01)
            self.assertEqual(param("train.epochs", 10), 20)

    def test_returns_default_when_key_missing(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "train:\n  lr: 0.01\n")
            self.assertEqual(param("train.epochs", 10), 10)

    def test_returns_default_when_params_yaml_is_empty(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "")
            self.assertEqual(param("lr", 0.001), 0.001)

    def test_returns_default_when_params_yaml_is_malformed(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "{\ninvalid yaml: [[\n")
            self.assertEqual(param("lr", 0.001), 0.001)

    def test_returns_default_when_value_is_null(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            self._write_params(Path(d), "lr: null\n")
            self.assertEqual(param("lr", 0.001), 0.001)

    def test_reads_params_yaml_from_parent_directory(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "params.yaml").write_text("lr: 0.01\n")
            subdir = root / "src"
            subdir.mkdir()
            os.chdir(subdir)
            self.assertEqual(param("lr", 0.001), 0.01)


if __name__ == "__main__":
    unittest.main()
