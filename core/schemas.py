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
    strongest_parts: list[str] = Field(default_factory=list)
    weakest_assumptions: list[str] = Field(default_factory=list)
    missing_analyses: list[str] = Field(default_factory=list)
    red_team_objections: list[str] = Field(default_factory=list)
    recommendation_confidence: str
    confidence_rationale: str
    improved_recommendation: str


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
