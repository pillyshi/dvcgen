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

    def test_param_returns_default(self):
        self.assertEqual(param("train.lr", 0.001), 0.001)

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


if __name__ == "__main__":
    unittest.main()
