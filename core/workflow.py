from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from agents import (
    analysis_planner,
    analytics_planner,
    critic,
    deck_outline_writer,
    financial_analyst,
    hypothesis_generator,
    insight_synthesizer,
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
    AnalysisResult,
    AnalysisPlanOutput,
    AnalyticsPlannerOutput,
    AssumptionRegisterItem,
    BusinessProblemInput,
    CriticOutput,
    DataRequestItem,
    DataProfile,
    DeckOutlineOutput,
    EvidenceItem,
    ExecutiveMemoOutput,
    FinalConsultingReport,
    FinancialAssumptionOutput,
    HypothesisOutput,
    InsightSynthesisOutput,
    IssueTreeOutput,
    KPIDriverItem,
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
    WorkflowStep("analytics_plan", "Analytics Plan", analytics_planner.run),
    WorkflowStep("analysis_plan", "Analysis Plan", analysis_planner.run),
    WorkflowStep("insight_synthesis", "Insight Synthesis", insight_synthesizer.run),
    WorkflowStep("financial_assumptions", "Financial Assumption Table", financial_analyst.run),
    WorkflowStep("executive_memo", "Executive Memo", memo_writer.run),
    WorkflowStep("deck_outline", "10-Slide Pitch Deck Outline", deck_outline_writer.run),
    WorkflowStep("critic", "Critic Review", critic.run),
]


def run_consulting_workflow(
    input_data: BusinessProblemInput,
    config: AppConfig | None = None,
    data_profile: DataProfile | None = None,
    analysis_results: list[AnalysisResult] | None = None,
    progress_callback: Callable[[int, WorkflowStep, AgentResult], None] | None = None,
) -> FinalConsultingReport:
    """Run the full consulting workflow and return a structured final report.

    Each agent receives all prior AgentResult objects. This gives later steps useful context
    such as the framed decision question, issue tree, hypotheses, and recommendation draft.
    The returned report also keeps those intermediate results for Streamlit display/export.
    """
    app_config = config or AppConfig.from_env()
    intermediate_results: list[AgentResult] = []
    if data_profile:
        intermediate_results.append(_data_profile_result(data_profile))
    for analysis_result in analysis_results or []:
        intermediate_results.append(_analysis_result_context(analysis_result))

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
    data_profile = _as_model(result_map, "data_profile", DataProfile)
    data_analysis_results = [
        AnalysisResult.model_validate(result.data)
        for result in results
        if result.key == "data_analysis_result"
    ]
    problem_framing = _as_model(result_map, "problem_framing", ProblemFramingOutput)
    issue_tree = _as_model(result_map, "issue_tree", IssueTreeOutput)
    hypotheses = _as_model(result_map, "hypotheses", HypothesisOutput)
    analytics_plan = _as_model(result_map, "analytics_plan", AnalyticsPlannerOutput)
    analysis_plan = _as_model(result_map, "analysis_plan", AnalysisPlanOutput)
    insight_synthesis = _as_model(result_map, "insight_synthesis", InsightSynthesisOutput)
    financial_assumptions = _as_model(result_map, "financial_assumptions", FinancialAssumptionOutput)
    executive_memo = _as_model(result_map, "executive_memo", ExecutiveMemoOutput)
    deck_outline = _as_model(result_map, "deck_outline", DeckOutlineOutput)
    critic = _as_model(result_map, "critic", CriticOutput)

    return FinalConsultingReport(
        business_input=business_input,
        data_profile=data_profile,
        data_analysis_results=data_analysis_results,
        situation_context=_build_situation_context(business_input, problem_framing),
        key_business_objective=_build_key_business_objective(business_input, problem_framing),
        market_customer_competitor_considerations=_build_market_considerations(
            business_input,
            issue_tree,
            executive_memo,
        ),
        strategic_options=_build_strategic_options(executive_memo),
        expected_impact=_build_expected_impact(executive_memo, financial_assumptions),
        assumption_register=_build_assumption_register(financial_assumptions, hypotheses),
        evidence_register=_build_evidence_register(analytics_plan, analysis_plan, hypotheses, financial_assumptions),
        data_request_list=_build_data_request_list(analytics_plan, analysis_plan),
        kpi_driver_tree=_build_kpi_driver_tree(financial_assumptions),
        data_gaps=_build_data_gaps(problem_framing, analytics_plan, analysis_plan, critic),
        action_plan=_build_action_plan(executive_memo, analysis_plan),
        decision_roadmap=_build_decision_roadmap(executive_memo, analysis_plan),
        stakeholder_lens=_build_stakeholder_lens(executive_memo),
        consulting_work_automated=_build_consulting_work_automated(),
        human_judgment_needed=_build_human_judgment_needed(),
        problem_framing=problem_framing,
        issue_tree=issue_tree,
        hypotheses=hypotheses,
        analytics_plan=analytics_plan,
        analysis_plan=analysis_plan,
        insight_synthesis=insight_synthesis,
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


def _data_profile_result(data_profile: DataProfile) -> AgentResult:
    return AgentResult(
        key="data_profile",
        title="Uploaded Data Profile",
        content=data_profile.to_markdown(),
        data=data_profile.model_dump(),
    )


def _analysis_result_context(result: AnalysisResult) -> AgentResult:
    content = (
        f"## Saved Data Analysis Result\n\n"
        f"**Analysis:** {result.title}\n\n"
        f"**Summary:** {result.summary}\n\n"
        f"**Columns used:** {', '.join(result.input_columns_used) or 'Manual inputs / not applicable'}\n\n"
        f"**Key metrics:** {result.key_metrics}\n\n"
        f"**Warnings:** {'; '.join(result.warnings) or 'None'}\n\n"
        f"**Limitations:** {'; '.join(result.limitations) or 'None'}"
    )
    return AgentResult(
        key="data_analysis_result",
        title=f"Data Analysis Result - {result.title}",
        content=content,
        data=result.model_dump(),
    )


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


def _build_expected_impact(
    executive_memo: ExecutiveMemoOutput | None,
    financial_assumptions: FinancialAssumptionOutput | None,
) -> list[str]:
    impact: list[str] = []
    if executive_memo:
        impact.extend(executive_memo.expected_impact)
        if executive_memo.financial_implications:
            impact.append(f"Financial implication: {executive_memo.financial_implications}")
    if financial_assumptions:
        impact.extend(financial_assumptions.simple_financial_logic[:3])
    return _unique(impact) or ["Expected impact is assumption-led until operating, customer, and financial data are uploaded."]


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
                status="Assumption - no uploaded data provided.",
            )
            for item in financial_assumptions.assumptions
        )
        register.extend(
            AssumptionRegisterItem(
                assumption=f"{item.category}: {item.driver}",
                source="Financial driver assumptions",
                importance=item.rationale,
                validation_needed=item.validation_source,
                status="Assumption - no uploaded data provided.",
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
                status="Assumption - no uploaded data provided.",
            )
            for item in hypotheses.hypotheses
        )
    return register


def _build_evidence_register(
    analytics_plan: AnalyticsPlannerOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
    hypotheses: HypothesisOutput | None,
    financial_assumptions: FinancialAssumptionOutput | None,
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    if analysis_plan and analysis_plan.evidence_register:
        evidence.extend(analysis_plan.evidence_register)
    if analytics_plan:
        evidence.extend(
            EvidenceItem(
                claim=item.hypothesis,
                evidence=f"Planned analysis: {item.recommended_analysis_method}",
                source="Analytics planner - no uploaded data provided.",
                strength="Analysis planned",
                data_backed=False,
                implication=item.decision_relevance,
            )
            for item in analytics_plan.plan
        )
    if hypotheses:
        evidence.extend(
            EvidenceItem(
                claim=item.hypothesis,
                evidence="Assumption - no uploaded data provided.",
                source="Generated from business context and prior workflow outputs.",
                strength="Assumption",
                data_backed=False,
                implication=item.potential_decision_impact,
            )
            for item in hypotheses.hypotheses
        )
    if financial_assumptions:
        evidence.extend(
            EvidenceItem(
                claim=item.assumption,
                evidence=item.base_case_value,
                source=f"Assumption requiring validation: {item.validation_source}",
                strength="Assumption",
                data_backed=False,
                implication=item.rationale,
            )
            for item in financial_assumptions.assumptions
        )
    return evidence


def _build_data_request_list(
    analytics_plan: AnalyticsPlannerOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
) -> list[DataRequestItem]:
    requests: list[DataRequestItem] = []
    if analytics_plan:
        requests.extend(
            DataRequestItem(
                data_name=item.business_metric_needed,
                purpose=f"Answer analytics question: {item.analytical_question}",
                owner="Data Team",
                priority=item.priority.title(),
                required_fields=item.data_fields_needed,
                assumption_if_missing=item.limitations_or_assumptions,
            )
            for item in analytics_plan.plan
        )
    if not analysis_plan:
        return requests
    if analysis_plan.data_request_list:
        requests.extend(analysis_plan.data_request_list)
        return _dedupe_data_requests(requests)
    requests.extend(
        [
            DataRequestItem(
                data_name=item.data_needed,
                purpose=f"Test workstream '{item.workstream}' and answer: {item.question}",
                owner=item.owner,
                priority="High",
                required_fields=[item.data_needed],
                assumption_if_missing="Keep related findings labeled as assumptions until this data is available.",
            )
            for item in analysis_plan.plan
        ]
    )
    return _dedupe_data_requests(requests)


def _dedupe_data_requests(items: list[DataRequestItem]) -> list[DataRequestItem]:
    seen = set()
    unique_items = []
    for item in items:
        key = (item.data_name.strip().lower(), item.purpose.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def _build_kpi_driver_tree(financial_assumptions: FinancialAssumptionOutput | None) -> list[KPIDriverItem]:
    if not financial_assumptions:
        return []
    if financial_assumptions.kpi_driver_tree:
        return financial_assumptions.kpi_driver_tree
    return [
        KPIDriverItem(
            kpi=item.category,
            driver=item.driver,
            formula_or_logic=item.rationale,
            data_needed=item.validation_source,
        )
        for item in financial_assumptions.driver_assumptions
    ]


def _build_data_gaps(
    problem_framing: ProblemFramingOutput | None,
    analytics_plan: AnalyticsPlannerOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
    critic: CriticOutput | None,
) -> list[str]:
    gaps: list[str] = []
    if problem_framing:
        gaps.extend(problem_framing.key_unknowns)
    if analytics_plan:
        gaps.extend(field for item in analytics_plan.plan for field in item.data_fields_needed)
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


def _build_decision_roadmap(
    executive_memo: ExecutiveMemoOutput | None,
    analysis_plan: AnalysisPlanOutput | None,
) -> list[str]:
    if executive_memo and executive_memo.decision_roadmap:
        return executive_memo.decision_roadmap
    roadmap = [
        "Align on the decision question, success criteria, and non-negotiable constraints.",
        "Validate the highest-risk assumptions with the requested data and targeted analysis.",
        "Compare strategic options using expected impact, investment, risk, and confidence.",
        "Make a stage-gate decision: proceed, pilot, defer, or stop.",
    ]
    if analysis_plan and analysis_plan.mvp_evidence_standard:
        roadmap.append(f"Minimum evidence standard: {analysis_plan.mvp_evidence_standard}")
    return roadmap


def _build_stakeholder_lens(executive_memo: ExecutiveMemoOutput | None) -> dict[str, list[str]]:
    default_lens = {
        "CEO": ["Strategic fit, growth upside, competitive timing, and decision clarity."],
        "CFO": ["Investment required, downside exposure, payback logic, and assumption sensitivity."],
        "COO": ["Operational feasibility, execution capacity, process change, and near-term risks."],
        "Data Team": ["Data availability, metric definitions, instrumentation gaps, and validation plan."],
    }
    if not executive_memo or not executive_memo.stakeholder_lens:
        return default_lens
    merged = default_lens | executive_memo.stakeholder_lens
    return {key: value if value else default_lens.get(key, []) for key, value in merged.items()}


def _build_consulting_work_automated() -> list[str]:
    return [
        "Problem framing and decision-question sharpening",
        "Issue tree and hypothesis tree generation",
        "Analytics plan and data request drafting",
        "Assumption-led KPI, driver, scenario, and sensitivity structure",
        "Strategic option comparison and recommendation drafting",
        "Executive memo, slide storyline, and partner-style critique",
    ]


def _build_human_judgment_needed() -> list[str]:
    return [
        "Validate market, customer, operational, and financial facts with real data.",
        "Challenge assumptions, confidence levels, and risks before committing resources.",
        "Apply executive judgment on timing, organizational appetite, politics, and tradeoffs.",
        "Approve the final recommendation and accountability for execution.",
    ]


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
        | DataProfile
        | IssueTreeOutput
        | HypothesisOutput
        | AnalyticsPlannerOutput
        | AnalysisPlanOutput
        | InsightSynthesisOutput
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
