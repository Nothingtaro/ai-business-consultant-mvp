from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BusinessInput(BaseModel):
    problem: str
    budget: str
    geography: str
    target_customers: str
    constraints: str
    expected_output: str

    def to_markdown(self) -> str:
        return (
            "## Business Input\n\n"
            f"**Problem:** {self.problem}\n\n"
            f"**Budget:** {self.budget}\n\n"
            f"**Geography:** {self.geography}\n\n"
            f"**Target customers:** {self.target_customers}\n\n"
            f"**Constraints:** {self.constraints}\n\n"
            f"**Expected output:** {self.expected_output}\n"
        )


BusinessProblemInput = BusinessInput


class IssueTreeBranch(BaseModel):
    name: str
    questions: list[str] = Field(default_factory=list)
    sub_branches: list[str] = Field(default_factory=list)


class SCQOutput(BaseModel):
    situation: str = ""
    complication: str = ""
    question: str = ""


class HypothesisItem(BaseModel):
    hypothesis: str
    why_it_matters: str
    evidence_needed: str
    potential_decision_impact: str


class HypothesisTreeBranch(BaseModel):
    branch: str
    hypotheses: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    decision_link: str = ""


class AnalyticsPlanItem(BaseModel):
    hypothesis: str
    analytical_question: str
    business_metric_needed: str
    data_fields_needed: list[str] = Field(default_factory=list)
    recommended_analysis_method: str
    expected_output: str
    decision_relevance: str
    priority: Literal["high", "medium", "low"] = "medium"
    limitations_or_assumptions: str = "Assumption-led until data is uploaded."

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> str:
        normalized = str(value or "medium").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            return "medium"
        return normalized


class AnalyticsPlannerOutput(BaseModel):
    plan: list[AnalyticsPlanItem] = Field(default_factory=list)
    summary: str = "Analytics plan is assumption-led until data is uploaded."


class AnalysisPlanItem(BaseModel):
    workstream: str
    question: str
    analysis: str
    data_needed: str
    owner: str
    time_estimate: str


class DataRequestItem(BaseModel):
    data_name: str
    purpose: str
    owner: str = "To be assigned"
    priority: str = "Medium"
    required_fields: list[str] = Field(default_factory=list)
    assumption_if_missing: str = "Label as assumption until data is available."


class EvidenceItem(BaseModel):
    claim: str
    evidence: str = "Assumption - no uploaded data provided."
    source: str = "Assumption based on provided business context."
    strength: str = "Assumption"
    data_backed: bool = False
    implication: str = ""


class DataProfile(BaseModel):
    file_name: str
    row_count: int
    column_count: int
    column_names: list[str] = Field(default_factory=list)
    inferred_dtypes: dict[str, str] = Field(default_factory=dict)
    missing_values: dict[str, int] = Field(default_factory=dict)
    missing_percentages: dict[str, float] = Field(default_factory=dict)
    duplicate_row_count: int = 0
    numeric_summary: dict[str, dict[str, float | int | None]] = Field(default_factory=dict)
    categorical_summary: dict[str, dict[str, Any]] = Field(default_factory=dict)
    date_columns_detected: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)
    possible_analysis_suggestions: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        numeric_columns = ", ".join(self.numeric_summary.keys()) or "None detected."
        categorical_columns = ", ".join(self.categorical_summary.keys()) or "None detected."
        missing_summary = "; ".join(
            f"{column}: {self.missing_percentages.get(column, 0)}%"
            for column in self.column_names
            if self.missing_values.get(column, 0)
        ) or "No missing values detected."
        return (
            "## Uploaded Data Profile\n\n"
            f"**File:** {self.file_name}\n\n"
            f"**Shape:** {self.row_count:,} rows x {self.column_count:,} columns\n\n"
            f"**Columns:** {', '.join(self.column_names) or 'Not provided.'}\n\n"
            f"**Numeric columns summarized:** {numeric_columns}\n\n"
            f"**Categorical columns summarized:** {categorical_columns}\n\n"
            f"**Missing-value summary:** {missing_summary}\n\n"
            f"**Duplicate rows:** {self.duplicate_row_count:,}\n\n"
            f"**Detected date columns:** {', '.join(self.date_columns_detected) or 'None detected.'}\n\n"
            f"**Data quality notes:** {'; '.join(self.data_quality_notes) or 'No major quality notes.'}\n\n"
            f"**Possible analyses:** {'; '.join(self.possible_analysis_suggestions) or 'Not provided.'}"
        )


class AnalysisResult(BaseModel):
    analysis_type: str
    title: str
    summary: str
    input_columns_used: list[str] = Field(default_factory=list)
    result_table: list[dict[str, Any]] = Field(default_factory=list)
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)


HypothesisSupportValue = Literal["supported", "partially_supported", "not_supported", "inconclusive"]
ConfidenceLevel = Literal["high", "medium", "low"]


class HypothesisSupportItem(BaseModel):
    hypothesis: str
    status: HypothesisSupportValue = "inconclusive"
    rationale: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> str:
        normalized = str(value or "inconclusive").strip().lower().replace(" ", "_").replace("-", "_")
        if normalized not in {"supported", "partially_supported", "not_supported", "inconclusive"}:
            return "inconclusive"
        return normalized


class InsightSynthesisOutput(BaseModel):
    key_insights: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    business_implications: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = "medium"
    limitations: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    hypothesis_support_status: list[HypothesisSupportItem] = Field(default_factory=list)

    @field_validator("confidence_level", mode="before")
    @classmethod
    def normalize_confidence_level(cls, value: object) -> str:
        normalized = str(value or "medium").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            return "medium"
        return normalized


class FinancialAssumptionItem(BaseModel):
    assumption: str
    base_case_value: str
    low_case: str
    high_case: str
    rationale: str
    validation_source: str


class FinancialDriverAssumption(BaseModel):
    driver: str
    category: str
    base_case_value: str
    worst_case_value: str
    best_case_value: str
    rationale: str
    validation_source: str


class KPIDriverItem(BaseModel):
    kpi: str
    driver: str
    formula_or_logic: str
    data_needed: str
    assumption_if_no_data: str = "Assumption - validate when data is uploaded."


class FinancialScenario(BaseModel):
    scenario: str
    price: float | None = None
    volume: float | None = None
    variable_cost_per_unit: float | None = None
    fixed_cost: float | None = None
    revenue: float | None = None
    variable_cost: float | None = None
    gross_profit: float | None = None
    gross_margin: float | None = None
    contribution_margin_per_unit: float | None = None
    break_even_units: float | None = None
    operating_profit: float | None = None
    notes: str = ""


class BreakEvenLogic(BaseModel):
    formula: str = "fixed_cost / (price - variable_cost_per_unit)"
    interpretation: str
    key_constraint: str


class RiskMitigation(BaseModel):
    risk: str
    why_it_matters: str
    mitigation: str


class StrategicOption(BaseModel):
    option: str
    description: str
    upside: str
    downside: str
    decision_implication: str
    expected_impact: str = ""
    investment_required: str = ""
    confidence_level: str = "Medium"


class AssumptionRegisterItem(BaseModel):
    assumption: str
    source: str
    importance: str
    validation_needed: str
    status: str = "Assumption - no uploaded data provided."


class ActionPlanOutput(BaseModel):
    next_30_days: list[str] = Field(default_factory=list)
    next_60_days: list[str] = Field(default_factory=list)
    next_90_days: list[str] = Field(default_factory=list)


class DeckSlide(BaseModel):
    slide_number: int
    title: str
    core_message: str
    suggested_visual: str
    key_bullets: list[str] = Field(default_factory=list)
    pyramid_role: str = ""


class ProblemFramingOutput(BaseModel):
    decision_question: str
    scq: SCQOutput = Field(default_factory=SCQOutput)
    context_summary: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    key_unknowns: list[str] = Field(default_factory=list)


class IssueTreeOutput(BaseModel):
    branches: list[IssueTreeBranch] = Field(default_factory=list)
    branch_logic: str
    highest_leverage_branches: list[str] = Field(default_factory=list)


class HypothesisOutput(BaseModel):
    hypotheses: list[HypothesisItem] = Field(default_factory=list)
    hypothesis_tree: list[HypothesisTreeBranch] = Field(default_factory=list)
    initial_lean: str


class AnalysisPlanOutput(BaseModel):
    plan: list[AnalysisPlanItem] = Field(default_factory=list)
    data_request_list: list[DataRequestItem] = Field(default_factory=list)
    evidence_register: list[EvidenceItem] = Field(default_factory=list)
    research_methods: list[str] = Field(default_factory=list)
    mvp_evidence_standard: str


class FinancialAssumptionOutput(BaseModel):
    assumptions: list[FinancialAssumptionItem] = Field(default_factory=list)
    kpi_driver_tree: list[KPIDriverItem] = Field(default_factory=list)
    driver_assumptions: list[FinancialDriverAssumption] = Field(default_factory=list)
    scenarios: list[FinancialScenario] = Field(default_factory=list)
    break_even_logic: BreakEvenLogic | None = None
    simple_financial_logic: list[str] = Field(default_factory=list)
    sensitivities: list[str] = Field(default_factory=list)


class ExecutiveMemoOutput(BaseModel):
    recommendation: str
    rationale: list[str] = Field(default_factory=list)
    expected_impact: list[str] = Field(default_factory=list)
    financial_implications: str
    market_customer_competitor_considerations: list[str] = Field(default_factory=list)
    strategic_options: list[StrategicOption] = Field(default_factory=list)
    risks_and_mitigations: list[RiskMitigation] = Field(default_factory=list)
    next_30_days: list[str] = Field(default_factory=list)
    next_60_days: list[str] = Field(default_factory=list)
    next_90_days: list[str] = Field(default_factory=list)
    decision_roadmap: list[str] = Field(default_factory=list)
    stakeholder_lens: dict[str, list[str]] = Field(default_factory=dict)


class DeckOutlineOutput(BaseModel):
    slides: list[DeckSlide] = Field(default_factory=list)
    pyramid_principle_storyline: list[str] = Field(default_factory=list)


class CriticOutput(BaseModel):
    overall_score: int = Field(ge=1, le=5)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)
    recommended_improvements: list[str] = Field(default_factory=list)
    red_team_challenges: list[str] = Field(default_factory=list)
    final_verdict: str


class AgentResult(BaseModel):
    key: str
    title: str
    content: str
    data: dict[str, Any] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        return f"# {self.title}\n\n{self.content.strip()}\n"


class FinalConsultingReport(BaseModel):
    business_input: BusinessInput
    data_profile: DataProfile | None = None
    data_analysis_results: list[AnalysisResult] = Field(default_factory=list)
    situation_context: list[str] = Field(default_factory=list)
    key_business_objective: str = ""
    market_customer_competitor_considerations: list[str] = Field(default_factory=list)
    strategic_options: list[StrategicOption] = Field(default_factory=list)
    expected_impact: list[str] = Field(default_factory=list)
    assumption_register: list[AssumptionRegisterItem] = Field(default_factory=list)
    evidence_register: list[EvidenceItem] = Field(default_factory=list)
    data_request_list: list[DataRequestItem] = Field(default_factory=list)
    kpi_driver_tree: list[KPIDriverItem] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    action_plan: ActionPlanOutput = Field(default_factory=ActionPlanOutput)
    decision_roadmap: list[str] = Field(default_factory=list)
    stakeholder_lens: dict[str, list[str]] = Field(default_factory=dict)
    consulting_work_automated: list[str] = Field(default_factory=list)
    human_judgment_needed: list[str] = Field(default_factory=list)
    problem_framing: ProblemFramingOutput | None = None
    issue_tree: IssueTreeOutput | None = None
    hypotheses: HypothesisOutput | None = None
    analytics_plan: AnalyticsPlannerOutput | None = None
    analysis_plan: AnalysisPlanOutput | None = None
    insight_synthesis: InsightSynthesisOutput | None = None
    financial_assumptions: FinancialAssumptionOutput | None = None
    executive_memo: ExecutiveMemoOutput | None = None
    deck_outline: DeckOutlineOutput | None = None
    critic: CriticOutput | None = None
    intermediate_results: list[AgentResult] = Field(default_factory=list)
