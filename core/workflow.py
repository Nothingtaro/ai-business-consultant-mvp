from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

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
from utils.app_logging import get_app_logger, save_failed_llm_output
from utils.json_parser import JsonParsingError
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
        result = _run_step_with_logging(step, input_data, intermediate_results, app_config)
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
            result = _run_step_with_logging(step, business_input, results, self.config)
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


def _run_step_with_logging(
    step: WorkflowStep,
    input_data: BusinessProblemInput,
    prior_results: list[AgentResult],
    config: AppConfig,
) -> AgentResult:
    logger = get_app_logger()
    start_time = datetime.now()
    timer = perf_counter()

    logger.info(
        "workflow_step_start step_key=%s step_title=%r start_time=%s prior_results=%s model=%s",
        step.key,
        step.title,
        start_time.isoformat(timespec="seconds"),
        len(prior_results),
        config.model,
    )

    try:
        result = step.runner(input_data, prior_results, config)
    except JsonParsingError as exc:
        end_time = datetime.now()
        duration_seconds = round(perf_counter() - timer, 2)
        raw_output_path = save_failed_llm_output(step.key, exc.raw_output)
        setattr(exc, "raw_output_path", str(raw_output_path))
        logger.error(
            "workflow_step_end step_key=%s step_title=%r status=json_parse_failed start_time=%s end_time=%s duration_seconds=%s raw_output_path=%s error_type=%s",
            step.key,
            step.title,
            start_time.isoformat(timespec="seconds"),
            end_time.isoformat(timespec="seconds"),
            duration_seconds,
            raw_output_path,
            type(exc).__name__,
        )
        raise
    except Exception as exc:
        end_time = datetime.now()
        duration_seconds = round(perf_counter() - timer, 2)
        logger.exception(
            "workflow_step_end step_key=%s step_title=%r status=failed start_time=%s end_time=%s duration_seconds=%s error_type=%s",
            step.key,
            step.title,
            start_time.isoformat(timespec="seconds"),
            end_time.isoformat(timespec="seconds"),
            duration_seconds,
            type(exc).__name__,
        )
        raise

    end_time = datetime.now()
    duration_seconds = round(perf_counter() - timer, 2)
    logger.info(
        "workflow_step_end step_key=%s step_title=%r status=success start_time=%s end_time=%s duration_seconds=%s",
        step.key,
        step.title,
        start_time.isoformat(timespec="seconds"),
        end_time.isoformat(timespec="seconds"),
        duration_seconds,
    )
    return result


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
