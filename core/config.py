from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODEL = "gpt-5.2"
DEFAULT_PROMPTS_DIR = Path("prompts")
ENV_FILE = Path(".env")


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    prompts_dir: Path = DEFAULT_PROMPTS_DIR

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv(dotenv_path=ENV_FILE)
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            prompts_dir=Path(os.getenv("PROMPTS_DIR", str(DEFAULT_PROMPTS_DIR)).strip() or DEFAULT_PROMPTS_DIR),
        )

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def missing_api_key_message(self) -> str:
        return (
            "Missing OpenAI API key. Create a `.env` file from `.env.example`, "
            "then set `OPENAI_API_KEY` before running an analysis."
        )

    def with_model(self, model: str) -> "AppConfig":
        clean_model = model.strip() or self.model
        return AppConfig(api_key=self.api_key, model=clean_model, prompts_dir=self.prompts_dir)
