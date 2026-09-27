import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class RunnerContractTest(unittest.TestCase):
    def run_cli(self, payload: dict):
        return subprocess.run(
            [sys.executable, str(ROOT / "runner.py"), "--validate-only"],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_pt_br_and_reports_normalized_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "ref.wav"
            reference.touch()
            output = Path(tmp) / "out.wav"
            result = self.run_cli(
                {
                    "text": "Texto de teste.",
                    "locale": "pt-BR",
                    "reference_audio": str(reference),
                    "output": str(output),
                    "seed": 1234,
                }
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["language_id"], "pt")
        self.assertEqual(response["seed"], 1234)
        self.assertEqual(response["cfg_weight"], 0.5)
        self.assertEqual(response["exaggeration"], 0.5)

    def test_rejects_locale_other_than_pt_br(self):
        result = self.run_cli(
            {
                "text": "Texto de teste.",
                "locale": "pt-PT",
                "reference_audio": __file__,
                "output": "out.wav",
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("locale deve ser pt-BR", result.stderr)

    def test_rejects_missing_reference_audio(self):
        result = self.run_cli(
            {
                "text": "Texto de teste.",
                "locale": "pt-BR",
                "reference_audio": "nao-existe.wav",
                "output": "out.wav",
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference_audio nao existe", result.stderr)


if __name__ == "__main__":
    unittest.main()
