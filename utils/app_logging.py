from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path("logs")
APP_LOG_PATH = LOG_DIR / "app.log"
FAILED_OUTPUT_DIR = LOG_DIR / "failed_llm_outputs"
SENSITIVE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)(OPENAI_API_KEY|API_KEY|TOKEN|SECRET|PASSWORD)=([^,\s]+)"),
)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_sensitive(super().format(record))


def redact_sensitive(text: str) -> str:
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(r"\1=[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def get_app_logger() -> logging.Logger:
    logger = logging.getLogger("ai_business_consultant")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            APP_LOG_PATH,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError:
        fallback_path = Path(tempfile.gettempdir()) / "ai_business_consultant.log"
        handler = RotatingFileHandler(
            fallback_path,
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger


def save_failed_llm_output(step_key: str, raw_output: str) -> Path:
    output_dir = FAILED_OUTPUT_DIR
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        output_dir = Path(tempfile.gettempdir()) / "failed_llm_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_step = "".join(char if char.isalnum() or char in ("_", "-") else "_" for char in step_key)
    path = output_dir / f"{timestamp}_{safe_step}.txt"
    path.write_text(redact_sensitive(raw_output or "<empty output>"), encoding="utf-8")
    return path
