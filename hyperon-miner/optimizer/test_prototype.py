import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from pathlib import Path

from prototype import (
    Config,
    analyze_dataset,
    experiment_main,
    load_project_env,
    llm_candidates,
    make_script,
    llm_api_key,
    parse_pattern_set,
    parse_results,
    run_miner,
    select_best,
    validate_config,
)


REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "experiments" / "data" / "very-small-ugly.metta"


class PrototypeTests(unittest.TestCase):
    def test_pattern_set_parser_extracts_unique_support_patterns(self):
        output = """
        OPTIMIZER_RESULTS_BEGIN
        (supportOf (Inheritance $x ugly) 21)
        (supportOf (Inheritance $x man) 27)
        (supportOf (Inheritance $x ugly) 21)
        OPTIMIZER_RESULTS_END
        """
        self.assertEqual(parse_pattern_set(output), [
            "(Inheritance $x man)",
            "(Inheritance $x ugly)",
        ])

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

    def test_llm_api_key_prefers_gemini_then_openai(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
        }, clear=True):
            key, provider = llm_api_key()
            self.assertEqual(key, "gemini-test-key")
            self.assertEqual(provider, "gemini")
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "openai-test-key",
        }, clear=True):
            key, provider = llm_api_key()
            self.assertEqual(key, "openai-test-key")
            self.assertEqual(provider, "openai")

    def test_gemini_is_default_and_does_not_fall_through_to_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "openai-test-key"}, clear=True):
            key, provider = llm_api_key()
        self.assertIsNone(key)
        self.assertEqual(provider, "gemini")

    def test_project_env_loads_gemini_settings_without_overriding_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                'LLM_PROVIDER=gemini\nGEMINI_API_KEY="file-key"\nGEMINI_MODEL=file-model\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"GEMINI_MODEL": "shell-model"}, clear=True):
                load_project_env(env_file)
                self.assertEqual(os.environ["LLM_PROVIDER"], "gemini")
                self.assertEqual(os.environ["GEMINI_API_KEY"], "file-key")
                self.assertEqual(os.environ["GEMINI_MODEL"], "shell-model")

    def test_gemini_request_normalizes_model_name_and_parses_proposal(self):
        response = io.BytesIO(json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": json.dumps({"configurations": [{
                    "min_support": 2,
                    "depth": 0,
                    "mode": "none",
                    "normalization": "none",
                    "db_ratio": "none",
                    "conj_exp": True,
                    "init_pattern": "$x",
                }]})}]},
            }],
            "usageMetadata": {"promptTokenCount": 17, "candidatesTokenCount": 9},
        }).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "gemini-test-key",
            "GEMINI_MODEL": "models/gemini-2.5-flash",
        }, clear=True), patch("prototype.urllib.request.urlopen", return_value=response) as urlopen:
            configs, metadata = llm_candidates(analyze_dataset(DATASET), [], 1)

        request = urlopen.call_args.args[0]
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 180)
        request_body = json.loads(request.data)
        self.assertEqual(request_body["generationConfig"]["maxOutputTokens"], 512)
        self.assertIn("responseSchema", request_body["generationConfig"])
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        )
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-test-key")
        self.assertEqual(metadata["provider"], "gemini")
        self.assertEqual(metadata["model"], "gemini-2.5-flash")
        self.assertEqual(metadata["prompt_tokens"], 17)
        self.assertTrue(metadata["real_llm"])
        self.assertEqual(configs[0].min_support, 2)

    def test_truncated_gemini_json_is_reported_as_fallback(self):
        response = io.BytesIO(json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": '{"configurations":[{"min_support":'}]},
                "finishReason": "MAX_TOKENS",
            }],
        }).encode())
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "gemini-test-key",
            "GEMINI_MODEL": "gemini-3.1-flash-lite",
        }, clear=True), patch("prototype.urllib.request.urlopen", return_value=response):
            configs, metadata = llm_candidates(analyze_dataset(DATASET), [], 1)

        self.assertEqual(metadata["provider"], "fallback-after-llm-error")
        self.assertEqual(metadata["finish_reason"], "MAX_TOKENS")
        self.assertIn("Expecting", metadata["error"])
        self.assertEqual(len(configs), 1)

    def test_gemini_http_failure_records_endpoint_details_without_key(self):
        error = urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            404,
            "Not Found",
            {},
            io.BytesIO(b'{"error":{"message":"model not found"}}'),
        )
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "gemini-secret-test-key",
            "GEMINI_MODEL": "gemini-2.5-flash",
        }, clear=True), patch("prototype.urllib.request.urlopen", side_effect=error):
            _, metadata = llm_candidates(analyze_dataset(DATASET), [], 1)

        self.assertEqual(metadata["provider"], "fallback-after-llm-error")
        self.assertEqual(metadata["model"], "gemini-2.5-flash")
        self.assertIn("models/gemini-2.5-flash:generateContent", metadata["endpoint"])
        self.assertIn("model not found", metadata["error"])
        self.assertNotIn("gemini-secret-test-key", metadata["error"])
        self.assertFalse(metadata["real_llm"])

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
