from __future__ import annotations

import time

from openai import APIConnectionError, APITimeoutError, BadRequestError, InternalServerError, OpenAI, RateLimitError

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
            request_kwargs = _build_response_kwargs(app_config.model, system_prompt, user_prompt, temperature)
            response = client.responses.create(**request_kwargs)
            return response.output_text.strip()
        except BadRequestError as exc:
            if _temperature_unsupported(exc) and "temperature" in request_kwargs:
                request_kwargs.pop("temperature", None)
                response = client.responses.create(**request_kwargs)
                return response.output_text.strip()
            raise
        except TRANSIENT_ERRORS as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(2**attempt)

    raise RuntimeError("OpenAI request failed after retrying transient errors.") from last_error


def _build_response_kwargs(model: str, system_prompt: str, user_prompt: str, temperature: float) -> dict[str, object]:
    request_kwargs: dict[str, object] = {
        "model": model,
        "instructions": system_prompt,
        "input": user_prompt,
    }
    if _model_supports_temperature(model):
        request_kwargs["temperature"] = temperature
    return request_kwargs


def _model_supports_temperature(model: str) -> bool:
    return not model.strip().lower().startswith("gpt-5.5")


def _temperature_unsupported(exc: BadRequestError) -> bool:
    message = str(exc).lower()
    return "temperature" in message and "unsupported" in message
