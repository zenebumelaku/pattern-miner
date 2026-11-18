import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from prototype import (
    Config,
    analyze_dataset,
    llm_candidates,
    make_script,
    parse_results,
    run_miner,
    select_best,
    validate_config,
)


REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "experiments" / "data" / "very-small-ugly.metta"


class PrototypeTests(unittest.TestCase):
    def test_dataset_analysis_and_validation(self):
        profile = analyze_dataset(DATASET)
        self.assertEqual(profile.atom_lines, 9)
        self.assertEqual(profile.predicates, {"Inheritance": 9})
        self.assertEqual(validate_config(Config(3, 0), profile), [])
        self.assertIn("depth greater than zero", validate_config(Config(3, 1, conj_exp=False), profile)[0])

    def test_result_parser_preserves_symbolic_metrics(self):
        output = """
        (supportOf (, (Inheritance A human) (Inheritance A ugly)) 4)
        (supportOf (Inheritance B man) 2)
        """
        count, supports, surprises = parse_results(output)
        self.assertEqual(count, 2)
        self.assertEqual(supports, [4.0, 2.0])
        self.assertEqual(surprises, [])

    def test_llm_fallback_is_deterministic_and_offline(self):
        profile = analyze_dataset(DATASET)
        with patch.dict(os.environ, {}, clear=True):
            configs, metadata = llm_candidates(profile, [], 2)
        self.assertEqual(metadata["provider"], "deterministic-fallback")
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0].min_support, 1)

    def test_generated_script_uses_actual_nine_argument_signature(self):
        script = make_script(REPO, DATASET, Config(3, 1, conj_exp=True))
        try:
            text = script.read_text(encoding="utf-8")
            self.assertIn("(pattern-miner &res &db $x 3 1 none none none True)", text)
            self.assertIn(str(DATASET), text)
            self.assertIn("frequent-pattern-miner-generic", text)
            self.assertNotIn("frequent-pattern-miner.metta", text)
            self.assertNotIn("boost_petta.py", text)
        finally:
            script.unlink(missing_ok=True)

    def test_runner_and_selection_with_fake_petta(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake-petta.sh"
            fake.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' 'OPTIMIZER_RESULTS_BEGIN'\n"
                "printf '%s\\n' '(supportOf (link A B) 4)'\n"
                "printf '%s\\n' '(supportOf (link B C) 2)'\n"
                "printf '%s\\n' 'OPTIMIZER_RESULTS_END'\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            result = run_miner(REPO, str(fake), DATASET, Config(3, 0), 10)
            self.assertEqual(result.status, "ok")
            self.assertEqual(result.pattern_count, 2)
            self.assertEqual(result.support_values, [4.0, 2.0])
            self.assertIsNotNone(select_best([result], None, 1))

    def test_timeout_is_serializable(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "slow-petta.sh"
            fake.write_text("#!/bin/sh\nsleep 2\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            result = run_miner(REPO, str(fake), DATASET, Config(3, 0), 0)
            self.assertEqual(result.status, "timeout")
            self.assertIsInstance(result.stdout, str)
            self.assertIsInstance(result.stderr, str)
            json.dumps(result.__dict__)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake-petta.sh"
            fake.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' 'OPTIMIZER_RESULTS_BEGIN'\n"
                "printf '%s\\n' '(supportOf (link A B) 4)'\n"
                "printf '%s\\n' 'OPTIMIZER_RESULTS_END'\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            config = Path(directory) / "config.json"
            config.write_text(json.dumps([{
                "min_support": 3,
                "depth": 0,
                "mode": "none",
                "normalization": "none",
                "db_ratio": "none",
                "conj_exp": True,
                "init_pattern": "$x",
            }]), encoding="utf-8")
            report = Path(directory) / "report.json"
            command = [sys.executable, str(REPO / "optimizer" / "prototype.py"),
                       "--repo", str(REPO), "--dataset", str(DATASET), "--petta", str(fake),
                       "--config-file", str(config), "--output", str(report)]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["results"][0]["status"], "ok")
            self.assertEqual(payload["best"]["pattern_count"], 1)


if __name__ == "__main__":
    unittest.main()
