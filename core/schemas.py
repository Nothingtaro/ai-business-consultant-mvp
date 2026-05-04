from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class HypothesisItem(BaseModel):
    hypothesis: str
    why_it_matters: str
    evidence_needed: str
    potential_decision_impact: str


class AnalysisPlanItem(BaseModel):
    workstream: str
    question: str
    analysis: str
    data_needed: str
    owner: str
    time_estimate: str


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


class DeckSlide(BaseModel):
    slide_number: int
    title: str
    core_message: str
    suggested_visual: str
    key_bullets: list[str] = Field(default_factory=list)


class ProblemFramingOutput(BaseModel):
    decision_question: str
    context_summary: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    key_unknowns: list[str] = Field(default_factory=list)


class IssueTreeOutput(BaseModel):
    branches: list[IssueTreeBranch] = Field(default_factory=list)
    branch_logic: str
    highest_leverage_branches: list[str] = Field(default_factory=list)


class HypothesisOutput(BaseModel):
    hypotheses: list[HypothesisItem] = Field(default_factory=list)
    initial_lean: str


class AnalysisPlanOutput(BaseModel):
    plan: list[AnalysisPlanItem] = Field(default_factory=list)
    research_methods: list[str] = Field(default_factory=list)
    mvp_evidence_standard: str


class FinancialAssumptionOutput(BaseModel):
    assumptions: list[FinancialAssumptionItem] = Field(default_factory=list)
    driver_assumptions: list[FinancialDriverAssumption] = Field(default_factory=list)
    scenarios: list[FinancialScenario] = Field(default_factory=list)
    break_even_logic: BreakEvenLogic | None = None
    simple_financial_logic: list[str] = Field(default_factory=list)
    sensitivities: list[str] = Field(default_factory=list)


class ExecutiveMemoOutput(BaseModel):
    recommendation: str
    rationale: list[str] = Field(default_factory=list)
    financial_implications: str
    risks_and_mitigations: list[RiskMitigation] = Field(default_factory=list)
    next_30_days: list[str] = Field(default_factory=list)


class DeckOutlineOutput(BaseModel):
    slides: list[DeckSlide] = Field(default_factory=list)


class CriticOutput(BaseModel):
    overall_score: int = Field(ge=1, le=5)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)
    recommended_improvements: list[str] = Field(default_factory=list)
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
    problem_framing: ProblemFramingOutput | None = None
    issue_tree: IssueTreeOutput | None = None
    hypotheses: HypothesisOutput | None = None
    analysis_plan: AnalysisPlanOutput | None = None
    financial_assumptions: FinancialAssumptionOutput | None = None
    executive_memo: ExecutiveMemoOutput | None = None
    deck_outline: DeckOutlineOutput | None = None
    critic: CriticOutput | None = None
    intermediate_results: list[AgentResult] = Field(default_factory=list)
