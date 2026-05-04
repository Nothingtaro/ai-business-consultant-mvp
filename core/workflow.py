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
    ActionPlanOutput,
    AgentResult,
    AnalysisPlanOutput,
    AssumptionRegisterItem,
    BusinessProblemInput,
    CriticOutput,
    DeckOutlineOutput,
    ExecutiveMemoOutput,
    FinalConsultingReport,
    FinancialAssumptionOutput,
    HypothesisOutput,
    IssueTreeOutput,
    ProblemFramingOutput,
    StrategicOption,
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
    problem_framing = _as_model(result_map, "problem_framing", ProblemFramingOutput)
    issue_tree = _as_model(result_map, "issue_tree", IssueTreeOutput)
    hypotheses = _as_model(result_map, "hypotheses", HypothesisOutput)
    analysis_plan = _as_model(result_map, "analysis_plan", AnalysisPlanOutput)
    financial_assumptions = _as_model(result_map, "financial_assumptions", FinancialAssumptionOutput)
    executive_memo = _as_model(result_map, "executive_memo", ExecutiveMemoOutput)
    deck_outline = _as_model(result_map, "deck_outline", DeckOutlineOutput)
    critic = _as_model(result_map, "critic", CriticOutput)

    return FinalConsultingReport(
        business_input=business_input,
        situation_context=_build_situation_context(business_input, problem_framing),
        key_business_objective=_build_key_business_objective(business_input, problem_framing),
        market_customer_competitor_considerations=_build_market_considerations(
            business_input,
            issue_tree,
            executive_memo,
        ),
        strategic_options=_build_strategic_options(executive_memo),
        assumption_register=_build_assumption_register(financial_assumptions, hypotheses),
        data_gaps=_build_data_gaps(problem_framing, analysis_plan, critic),
        action_plan=_build_action_plan(executive_memo, analysis_plan),
        problem_framing=problem_framing,
        issue_tree=issue_tree,
        hypotheses=hypotheses,
        analysis_plan=analysis_plan,
        financial_assumptions=financial_assumptions,
        executive_memo=executive_memo,
        deck_outline=deck_outline,
        critic=critic,
        intermediate_results=results,
    )


def _build_situation_context(
    business_input: BusinessProblemInput,
    problem_framing: ProblemFramingOutput | None,
) -> list[str]:
    context = [
        f"Business problem: {business_input.problem}",
        f"Geography: {business_input.geography}",
        f"Target customers: {business_input.target_customers}",
        f"Budget: {business_input.budget}",
        f"Constraints: {business_input.constraints}",
    ]
    if problem_framing:
        context.extend(problem_framing.context_summary)
    return _unique(context)


def _build_key_business_objective(
    business_input: BusinessProblemInput,
    problem_framing: ProblemFramingOutput | None,
) -> str:
    if business_input.expected_output and business_input.expected_output != "Not specified":
        return business_input.expected_output
    if problem_framing and problem_framing.success_criteria:
        return problem_framing.success_criteria[0]
    return "Clarify the decision and identify the highest-value path forward."


def _build_market_considerations(
    business_input: BusinessProblemInput,
    issue_tree: IssueTreeOutput | None,
    executive_memo: ExecutiveMemoOutput | None,
) -> list[str]:
    considerations = []
    if executive_memo and executive_memo.market_customer_competitor_considerations:
        considerations.extend(executive_memo.market_customer_competitor_considerations)
    considerations.extend(
        [
            f"Market / geography: {business_input.geography}",
            f"Customer segment: {business_input.target_customers}",
        ]
    )
    if issue_tree:
        market_branches = [
            branch.name
            for branch in issue_tree.branches
            if any(keyword in branch.name.lower() for keyword in ("market", "customer", "competitor", "demand"))
        ]
        considerations.extend(f"High-priority market/customer branch: {branch}" for branch in market_branches)
    return _unique(considerations)


def _build_strategic_options(executive_memo: ExecutiveMemoOutput | None) -> list[StrategicOption]:
    if executive_memo and executive_memo.strategic_options:
        return executive_memo.strategic_options
    if not executive_memo:
        return []
    return [
        StrategicOption(
            option="Proceed with recommended path",
            description=executive_memo.recommendation,
            upside="Captures the opportunity identified in the analysis.",
            downside="Depends on validating the core assumptions before scaling.",
            decision_implication="Use the recommendation as the base case for management decision-making.",
        ),
        StrategicOption(
            option="Run a constrained pilot first",
            description="Validate demand, economics, and operational feasibility before committing full resources.",
            upside="Reduces downside risk and improves evidence quality.",
            downside="Delays full-scale impact and may understate long-term potential.",
            decision_implication="Best fit if confidence is moderate or data gaps remain material.",
        ),
        StrategicOption(
            option="Defer major investment",
            description="Pause significant spend until critical data gaps are closed.",
            upside="Avoids committing capital against weak evidence.",
            downside="May miss timing advantages or competitor movement.",
            decision_implication="Best fit if the critic review or financial assumptions show low confidence.",
        ),
    ]


def _build_assumption_register(
    financial_assumptions: FinancialAssumptionOutput | None,
    hypotheses: HypothesisOutput | None,
) -> list[AssumptionRegisterItem]:
    register: list[AssumptionRegisterItem] = []
    if financial_assumptions:
        register.extend(
            AssumptionRegisterItem(
                assumption=item.assumption,
                source="Financial assumptions",
                importance=item.rationale,
                validation_needed=item.validation_source,
            )
            for item in financial_assumptions.assumptions
        )
        register.extend(
            AssumptionRegisterItem(
                assumption=f"{item.category}: {item.driver}",
                source="Financial driver assumptions",
                importance=item.rationale,
                validation_needed=item.validation_source,
            )
            for item in financial_assumptions.driver_assumptions
        )
    if hypotheses:
        register.extend(
            AssumptionRegisterItem(
                assumption=item.hypothesis,
                source="Key hypotheses",
                importance=item.why_it_matters,
                validation_needed=item.evidence_needed,
            )
            for item in hypotheses.hypotheses
        )
    return register


def _build_data_gaps(
    problem_framing: ProblemFramingOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
    critic: CriticOutput | None,
) -> list[str]:
    gaps: list[str] = []
    if problem_framing:
        gaps.extend(problem_framing.key_unknowns)
    if analysis_plan:
        gaps.extend(item.data_needed for item in analysis_plan.plan)
    if critic:
        gaps.extend(critic.critical_gaps)
    return _unique(gaps)


def _build_action_plan(
    executive_memo: ExecutiveMemoOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
) -> ActionPlanOutput:
    next_30_days = executive_memo.next_30_days if executive_memo else []
    next_60_days = executive_memo.next_60_days if executive_memo else []
    next_90_days = executive_memo.next_90_days if executive_memo else []

    if analysis_plan and not next_60_days:
        next_60_days = [
            f"Complete {item.workstream}: {item.analysis}"
            for item in analysis_plan.plan[:3]
        ]
    if analysis_plan and not next_90_days:
        next_90_days = [
            f"Use evidence from {item.workstream} to refine the recommendation."
            for item in analysis_plan.plan[:3]
        ]
    return ActionPlanOutput(
        next_30_days=next_30_days,
        next_60_days=next_60_days,
        next_90_days=next_90_days,
    )


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique_items = []
    for item in items:
        clean_item = str(item).strip()
        if not clean_item or clean_item in seen:
            continue
        seen.add(clean_item)
        unique_items.append(clean_item)
    return unique_items


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
