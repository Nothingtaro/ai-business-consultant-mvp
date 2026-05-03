from __future__ import annotations

from core.config import AppConfig
from core.schemas import AgentResult, BusinessProblemInput, IssueTreeOutput
from utils.json_parser import model_to_markdown, parse_model_output
from utils.llm_client import call_llm
from utils.prompt_loader import load_prompt_template, render_prompt


def run(business_input: BusinessProblemInput, prior_results: list[AgentResult], config: AppConfig) -> AgentResult:
    system_prompt = load_prompt_template(config.prompts_dir, "system")
    template = load_prompt_template(config.prompts_dir, "issue_tree")
    prompt = render_prompt(template, business_input, prior_results, IssueTreeOutput)
    raw_output = call_llm(system_prompt, prompt, config=config)
    parsed = parse_model_output(raw_output, IssueTreeOutput)
    return AgentResult(
        key="issue_tree",
        title="MECE Issue Tree",
        content=model_to_markdown(parsed),
        data=parsed.model_dump(),
    )
