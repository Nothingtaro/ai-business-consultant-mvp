from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass

from agents import (
    analysis_planner,
    critic,
    deck_outline_writer,
    financial_analyst,
    hypothesis_generator,
    issue_tree_builder,
    memo_writer,
    problem_framer,
)
from core.config import AppConfig
from core.schemas import (
    AgentResult,
    AnalysisPlanOutput,
    BusinessProblemInput,
    CriticOutput,
    DeckOutlineOutput,
    ExecutiveMemoOutput,
    FinalConsultingReport,
    FinancialAssumptionOutput,
    HypothesisOutput,
    IssueTreeOutput,
    ProblemFramingOutput,
)


AgentRunner = Callable[[BusinessProblemInput, list[AgentResult], AppConfig], AgentResult]


@dataclass(frozen=True)
class WorkflowStep:
    key: str
    title: str
    runner: AgentRunner


WORKFLOW_STEPS = [
    WorkflowStep("problem_framing", "Decision Question", problem_framer.run),
    WorkflowStep("issue_tree", "MECE Issue Tree", issue_tree_builder.run),
    WorkflowStep("hypotheses", "Key Hypotheses", hypothesis_generator.run),
    WorkflowStep("analysis_plan", "Analysis Plan", analysis_planner.run),
    WorkflowStep("financial_assumptions", "Financial Assumption Table", financial_analyst.run),
    WorkflowStep("executive_memo", "Executive Memo", memo_writer.run),
    WorkflowStep("deck_outline", "10-Slide Pitch Deck Outline", deck_outline_writer.run),
    WorkflowStep("critic", "Critic Review", critic.run),
]


def run_consulting_workflow(
    input_data: BusinessProblemInput,
    config: AppConfig | None = None,
    progress_callback: Callable[[int, WorkflowStep, AgentResult], None] | None = None,
) -> FinalConsultingReport:
    """Run the full consulting workflow and return a structured final report.

    Each agent receives all prior AgentResult objects. This gives later steps useful context
    such as the framed decision question, issue tree, hypotheses, and recommendation draft.
    The returned report also keeps those intermediate results for Streamlit display/export.
    """
    app_config = config or AppConfig.from_env()
    intermediate_results: list[AgentResult] = []

    for index, step in enumerate(WORKFLOW_STEPS, start=1):
        # Prior outputs are intentionally passed forward so every step can build on the work
        # already completed instead of re-solving the original business problem in isolation.
        result = step.runner(input_data, intermediate_results, app_config)
        intermediate_results.append(result)

        if progress_callback:
            progress_callback(index, step, result)

    return _build_final_report(input_data, intermediate_results)


class ConsultingWorkflow:
    """Compatibility wrapper around the main workflow function."""

    steps = WORKFLOW_STEPS

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def run_iter(self, business_input: BusinessProblemInput) -> Generator[AgentResult, None, None]:
        results: list[AgentResult] = []

        for step in self.steps:
            result = step.runner(business_input, results, self.config)
            results.append(result)
            yield result

    def run(self, business_input: BusinessProblemInput) -> FinalConsultingReport:
        return run_consulting_workflow(business_input, self.config)


def _build_final_report(
    business_input: BusinessProblemInput,
    results: list[AgentResult],
) -> FinalConsultingReport:
    result_map = {result.key: result for result in results}

    return FinalConsultingReport(
        business_input=business_input,
        problem_framing=_as_model(result_map, "problem_framing", ProblemFramingOutput),
        issue_tree=_as_model(result_map, "issue_tree", IssueTreeOutput),
        hypotheses=_as_model(result_map, "hypotheses", HypothesisOutput),
        analysis_plan=_as_model(result_map, "analysis_plan", AnalysisPlanOutput),
        financial_assumptions=_as_model(result_map, "financial_assumptions", FinancialAssumptionOutput),
        executive_memo=_as_model(result_map, "executive_memo", ExecutiveMemoOutput),
        deck_outline=_as_model(result_map, "deck_outline", DeckOutlineOutput),
        critic=_as_model(result_map, "critic", CriticOutput),
        intermediate_results=results,
    )


def _as_model(
    result_map: dict[str, AgentResult],
    key: str,
    model_type: type[
        ProblemFramingOutput
        | IssueTreeOutput
        | HypothesisOutput
        | AnalysisPlanOutput
        | FinancialAssumptionOutput
        | ExecutiveMemoOutput
        | DeckOutlineOutput
        | CriticOutput
    ],
):
    result = result_map.get(key)
    if result is None:
        return None
    return model_type.model_validate(result.data)
