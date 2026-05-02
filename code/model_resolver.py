from __future__ import annotations

import os
from pathlib import Path


DEFAULT_OPENAI_MODEL = "openai:gpt-5.4"
DEFAULT_ANTHROPIC_MODEL = "anthropic:claude-3-5-sonnet-latest"


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        normalized = value.strip().strip('"').strip("'")
        os.environ[key] = normalized


def resolve_model_name(*, explicit_model: str | None = None) -> str:
    if explicit_model is not None:
        normalized_explicit = explicit_model.strip()
        if not normalized_explicit:
            raise RuntimeError("Explicit model must not be blank.")
        return normalized_explicit
    env_model = os.getenv("ORCHESTRATE_MODEL")
    if env_model is not None:
        normalized_env_model = env_model.strip()
        if not normalized_env_model:
            raise RuntimeError("ORCHESTRATE_MODEL must not be blank.")
        return normalized_env_model
    if os.getenv("OPENAI_API_KEY"):
        return DEFAULT_OPENAI_MODEL
    if os.getenv("ANTHROPIC_API_KEY"):
        return DEFAULT_ANTHROPIC_MODEL
    raise RuntimeError(
        "No model configuration found. Set ORCHESTRATE_MODEL or provide "
        "OPENAI_API_KEY / ANTHROPIC_API_KEY in the environment or .env file."
    )
