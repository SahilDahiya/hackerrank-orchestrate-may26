from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import model_resolver  # noqa: E402


class ModelResolverTests(unittest.TestCase):
    def test_load_dotenv_file_sets_values_without_overriding_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv_path = Path(tmpdir) / ".env"
            dotenv_path.write_text(
                "OPENAI_API_KEY=new-key\nORCHESTRATE_MODEL=openai:test-model\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "existing-key"}, clear=True):
                model_resolver.load_dotenv_file(dotenv_path)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "existing-key")
                self.assertEqual(os.environ["ORCHESTRATE_MODEL"], "openai:test-model")

    def test_resolve_model_name_prefers_explicit_model(self) -> None:
        with patch.dict(os.environ, {"ORCHESTRATE_MODEL": "openai:env-model"}, clear=True):
            self.assertEqual(
                model_resolver.resolve_model_name(explicit_model="anthropic:explicit"),
                "anthropic:explicit",
            )

    def test_resolve_model_name_uses_env_model_before_provider_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ORCHESTRATE_MODEL": "openai:env-model",
                "OPENAI_API_KEY": "k",
            },
            clear=True,
        ):
            self.assertEqual(model_resolver.resolve_model_name(), "openai:env-model")

    def test_resolve_model_name_uses_gpt_5_4_for_openai_provider_default(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "k"}, clear=True):
            self.assertEqual(model_resolver.resolve_model_name(), "openai:gpt-5.4")

    def test_resolve_model_name_rejects_blank_explicit_model(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                model_resolver.resolve_model_name(explicit_model="   ")

    def test_resolve_model_name_rejects_blank_env_model(self) -> None:
        with patch.dict(os.environ, {"ORCHESTRATE_MODEL": "   "}, clear=True):
            with self.assertRaises(RuntimeError):
                model_resolver.resolve_model_name()

    def test_resolve_model_name_raises_when_no_configuration_exists(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                model_resolver.resolve_model_name()


if __name__ == "__main__":
    unittest.main()
