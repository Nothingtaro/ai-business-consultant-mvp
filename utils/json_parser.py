from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


ModelT = TypeVar("ModelT", bound=BaseModel)


class JsonParsingError(ValueError):
    def __init__(self, message: str, raw_output: str) -> None:
        self.raw_output = raw_output
        preview = raw_output.strip()[:2000] or "<empty output>"
        super().__init__(f"{message}\n\nRaw model output:\n{preview}")


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain text, fenced JSON, or surrounding prose."""
    candidate = _extract_json_candidate(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise JsonParsingError(f"Could not parse model output as JSON: {exc}", text) from exc

    if not isinstance(parsed, dict):
        raise JsonParsingError("Expected the model to return a JSON object.", text)
    return parsed


def parse_model_output(text: str, model_type: type[ModelT]) -> ModelT:
    data = parse_json_object(text)
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise JsonParsingError(f"JSON did not match schema `{model_type.__name__}`: {exc}", text) from exc


def model_to_markdown(model: BaseModel) -> str:
    json_text = model.model_dump_json(indent=2)
    return f"```json\n{json_text}\n```"


def _extract_json_candidate(text: str) -> str:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    start = cleaned.find("{")
    if start == -1:
        raise JsonParsingError("No JSON object found in model output.", text)

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]

    raise JsonParsingError("Found the start of a JSON object, but it was not complete.", text)
