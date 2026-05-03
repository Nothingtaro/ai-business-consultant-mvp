from __future__ import annotations

import time

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from core.config import AppConfig


TRANSIENT_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    *,
    config: AppConfig | None = None,
    max_retries: int = 2,
) -> str:
    """Call the configured OpenAI model and return plain text."""
    app_config = config or AppConfig.from_env()
    if not app_config.has_api_key:
        raise ValueError(app_config.missing_api_key_message)

    client = OpenAI(api_key=app_config.api_key)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.responses.create(
                model=app_config.model,
                instructions=system_prompt,
                input=user_prompt,
                temperature=temperature,
            )
            return response.output_text.strip()
        except TRANSIENT_ERRORS as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(2**attempt)

    raise RuntimeError("OpenAI request failed after retrying transient errors.") from last_error
