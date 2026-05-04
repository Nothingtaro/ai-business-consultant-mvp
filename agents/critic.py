from __future__ import annotations

from core.config import AppConfig
from core.schemas import AgentResult, BusinessProblemInput, CriticOutput
from utils.json_parser import model_to_markdown, parse_model_output
from utils.llm_client import call_llm
from utils.prompt_loader import load_prompt_template, render_prompt


def run(business_input: BusinessProblemInput, prior_results: list[AgentResult], config: AppConfig) -> AgentResult:
    """Run the senior-manager critic review and enforce its structured JSON contract."""
    system_prompt = load_prompt_template(config.prompts_dir, "system")
    template = load_prompt_template(config.prompts_dir, "critic")
    prompt = render_prompt(template, business_input, prior_results, CriticOutput)
    raw_output = call_llm(system_prompt, prompt, config=config)
    parsed = parse_model_output(raw_output, CriticOutput)
    return AgentResult(
        key="critic",
        title="Critic Review",
        content=model_to_markdown(parsed),
        data=parsed.model_dump(),
    )
