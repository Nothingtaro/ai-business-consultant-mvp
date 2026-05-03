from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from pydantic import BaseModel

from core.schemas import AgentResult, BusinessProblemInput


def load_prompt_template(prompts_dir: Path, name: str) -> str:
    path = prompts_dir / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def render_prompt(
    template: str,
    business_input: BusinessProblemInput,
    prior_results: list[AgentResult],
    output_schema: Type[BaseModel] | None = None,
) -> str:
    prompt = template.format(
        business_problem=business_input.problem,
        budget=business_input.budget,
        geography=business_input.geography,
        target_customers=business_input.target_customers,
        constraints=business_input.constraints,
        expected_output=business_input.expected_output,
        prior_work=_format_prior_work(prior_results),
    )
    if output_schema is None:
        return prompt

    schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
    return (
        f"{prompt}\n\n"
        "Return only a valid JSON object. Do not include markdown fences, commentary, or extra text.\n"
        "The JSON object must match this schema:\n"
        f"{schema_json}"
    )


def _format_prior_work(prior_results: list[AgentResult]) -> str:
    return "\n\n".join(result.to_markdown() for result in prior_results) or "No prior workflow outputs yet."
