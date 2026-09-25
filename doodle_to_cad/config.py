from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    api_key: str = os.getenv("OPENAI_API_KEY", "not-needed")
    requested_model: str = os.getenv("OPENAI_MODEL", "").strip()
    timeout: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "300"))
    max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))
    enable_thinking: bool = os.getenv("OPENAI_ENABLE_THINKING", "false").lower() in {"1", "true", "yes", "on"}
    thinking_budget: int = int(os.getenv("OPENAI_THINKING_BUDGET", "4096"))
    structured_enable_thinking: bool = os.getenv(
        "OPENAI_STRUCTURED_ENABLE_THINKING", os.getenv("OPENAI_ENABLE_THINKING", "false")
    ).lower() in {"1", "true", "yes", "on"}
    code_enable_thinking: bool = os.getenv("OPENAI_CODE_ENABLE_THINKING", "false").lower() in {"1", "true", "yes", "on"}
    code_max_tokens: int = int(os.getenv("OPENAI_CODE_MAX_TOKENS", "8192"))
    code_validation_repairs: int = max(0, min(4, int(os.getenv("CAD_CODE_VALIDATION_REPAIRS", "2"))))
    supervisor_timeout: float = max(10.0, float(os.getenv("CAD_SUPERVISOR_TIMEOUT_SECONDS", "90")))
    transport_retries: int = max(0, min(4, int(os.getenv("CAD_TRANSPORT_RETRIES", "2"))))
    agent_max_attempts: int = max(1, min(6, int(os.getenv("CAD_AGENT_MAX_ATTEMPTS", "3"))))
    agent_accept_score: float = float(os.getenv("CAD_AGENT_ACCEPT_SCORE", "70"))
    openscad_bin: str = os.getenv("OPENSCAD_BIN", "openscad")
    host: str = os.getenv("DOODLE_HOST", "127.0.0.1")
    port: int = int(os.getenv("DOODLE_PORT", "8080"))
    results_dir: Path = ROOT / os.getenv("DOODLE_RESULTS_DIR", "results")


settings = Settings()
