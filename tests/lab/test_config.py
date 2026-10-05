import os
import tempfile
import unittest
from pathlib import Path

from conformance.lab.config import load_config


class ConfigTest(unittest.TestCase):
    def test_cwd_lab_toml_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "lab.toml").write_text('org = "x-org"\nruns_dir = "r"\n', encoding="utf-8")
            old = os.getcwd()
            os.chdir(tmp)
            try:
                cfg = load_config()
            finally:
                os.chdir(old)
            self.assertEqual(cfg["org"], "x-org")
            self.assertEqual(cfg["runs_dir"].resolve(), (Path(tmp) / "r").resolve())

    def test_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
            self.assertEqual(cfg["runs_dir"], Path(tmp) / "runs")
            self.assertIsNone(cfg["org"])
