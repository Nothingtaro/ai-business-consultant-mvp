from __future__ import annotations

import re
from datetime import datetime

from core.schemas import (
    AnalysisPlanItem,
    DeckSlide,
    FinalConsultingReport,
    FinancialAssumptionItem,
    HypothesisItem,
    IssueTreeBranch,
    RiskMitigation,
)


def build_markdown_report(report: FinalConsultingReport) -> str:
    """Build the complete client-ready markdown consulting report."""
    sections = [
        "# AI Business Consulting Report",
        _executive_summary(report),
        _decision_question(report),
        _situation_context(report),
        _key_business_objective(report),
        _issue_tree(report),
        _key_hypotheses(report),
        _analysis_plan(report),
        _market_customer_competitor_considerations(report),
        _strategic_options(report),
        _recommendation(report),
        _financial_assumptions(report),
        _scenario_analysis(report),
        _key_risks(report),
        _mitigation_plan(report),
        _assumption_register(report),
        _data_gaps(report),
        _action_plan(report),
        _deck_outline(report),
        _critic_review(report),
    ]
    return "\n\n".join(section for section in sections if section).strip() + "\n"


def build_full_report(report: FinalConsultingReport) -> str:
    return build_markdown_report(report)


def safe_filename(name: str = "consulting_report.md") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    stem, extension = _split_filename(name)
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_").lower() or "consulting_report"
    extension = re.sub(r"[^a-zA-Z0-9]+", "", extension).lower() or "md"
    return f"{stem}_{timestamp}.{extension}"


def _split_filename(name: str) -> tuple[str, str]:
    if "." not in name:
        return name, "md"
    stem, extension = name.rsplit(".", 1)
    return stem, extension or "md"


def _executive_summary(report: FinalConsultingReport) -> str:
    memo = report.executive_memo
    framing = report.problem_framing
    critic = report.critic

    bullets = []
    if framing:
        bullets.append(f"Decision focus: {framing.decision_question}")
    if memo:
        bullets.append(f"Recommendation: {memo.recommendation}")
    if critic:
        bullets.append(f"Critic score: {critic.overall_score}/5 - {critic.final_verdict}")

    return "## Executive Summary\n\n" + _bullets(bullets)


def _decision_question(report: FinalConsultingReport) -> str:
    if not report.problem_framing:
        return "## Decision Question\n\nNot provided."
    framing = report.problem_framing
    return (
        "## Decision Question\n\n"
        f"{framing.decision_question}\n\n"
        "### Success Criteria\n\n"
        f"{_bullets(framing.success_criteria)}\n\n"
        "### Key Unknowns\n\n"
        f"{_bullets(framing.key_unknowns)}"
    )


def _situation_context(report: FinalConsultingReport) -> str:
    rows = [
        ("Business Problem", report.business_input.problem),
        ("Budget", report.business_input.budget),
        ("Geography", report.business_input.geography),
        ("Target Customers", report.business_input.target_customers),
        ("Constraints", report.business_input.constraints),
        ("Expected Output", report.business_input.expected_output),
    ]
    return (
        "## Situation / Context\n\n"
        f"{_table(['Field', 'Input'], rows)}\n\n"
        "### Context Summary\n\n"
        f"{_bullets(report.situation_context)}"
    )


def _key_business_objective(report: FinalConsultingReport) -> str:
    return "## Key Business Objective\n\n" + (report.key_business_objective or "Not provided.")


def _issue_tree(report: FinalConsultingReport) -> str:
    if not report.issue_tree:
        return "## Issue Tree\n\nNot provided."
    tree = report.issue_tree
    branch_rows = [
        (branch.name, _join(branch.questions), _join(branch.sub_branches))
        for branch in tree.branches
    ]
    return (
        "## Issue Tree\n\n"
        f"{_table(['Branch', 'Key Questions', 'Sub-Branches'], branch_rows)}\n\n"
        f"**Branch logic:** {tree.branch_logic}\n\n"
        "### Highest-Leverage Branches\n\n"
        f"{_bullets(tree.highest_leverage_branches)}"
    )


def _key_hypotheses(report: FinalConsultingReport) -> str:
    if not report.hypotheses:
        return "## Key Hypotheses\n\nNot provided."
    rows = [
        (
            item.hypothesis,
            item.why_it_matters,
            item.evidence_needed,
            item.potential_decision_impact,
        )
        for item in report.hypotheses.hypotheses
    ]
    return (
        "## Key Hypotheses\n\n"
        f"{_table(['Hypothesis', 'Why It Matters', 'Evidence Needed', 'Decision Impact'], rows)}\n\n"
        f"**Initial lean:** {report.hypotheses.initial_lean}"
    )


def _analysis_plan(report: FinalConsultingReport) -> str:
    if not report.analysis_plan:
        return "## Analysis Plan\n\nNot provided."
    rows = [
        (
            item.workstream,
            item.question,
            item.analysis,
            item.data_needed,
            item.owner,
            item.time_estimate,
        )
        for item in report.analysis_plan.plan
    ]
    return (
        "## Analysis Plan\n\n"
        f"{_table(['Workstream', 'Question', 'Analysis', 'Data Needed', 'Owner', 'Timing'], rows)}\n\n"
        "### Research Methods\n\n"
        f"{_bullets(report.analysis_plan.research_methods)}\n\n"
        f"**MVP evidence standard:** {report.analysis_plan.mvp_evidence_standard}"
    )


def _market_customer_competitor_considerations(report: FinalConsultingReport) -> str:
    return (
        "## Market / Customer / Competitor Considerations\n\n"
        f"{_bullets(report.market_customer_competitor_considerations)}"
    )


def _strategic_options(report: FinalConsultingReport) -> str:
    rows = [
        (
            item.option,
            item.description,
            item.upside,
            item.downside,
            item.decision_implication,
        )
        for item in report.strategic_options
    ]
    return "## Strategic Options\n\n" + _table(
        ["Option", "Description", "Upside", "Downside", "Decision Implication"],
        rows,
    )


def _financial_assumptions(report: FinalConsultingReport) -> str:
    if not report.financial_assumptions:
        return "## Financial Assumptions\n\nNot provided."
    driver_rows = [
        (
            item.category,
            item.driver,
            item.worst_case_value,
            item.base_case_value,
            item.best_case_value,
            item.rationale,
            item.validation_source,
        )
        for item in report.financial_assumptions.driver_assumptions
    ]
    rows = [
        (
            item.assumption,
            item.base_case_value,
            item.low_case,
            item.high_case,
            item.rationale,
            item.validation_source,
        )
        for item in report.financial_assumptions.assumptions
    ]
    break_even = report.financial_assumptions.break_even_logic
    break_even_text = "Not provided."
    if break_even:
        break_even_text = (
            f"**Formula:** {break_even.formula}\n\n"
            f"**Interpretation:** {break_even.interpretation}\n\n"
            f"**Key constraint:** {break_even.key_constraint}"
        )
    return (
        "## Financial Assumptions\n\n"
        "### Driver Assumptions\n\n"
        f"{_table(['Category', 'Driver', 'Worst Case', 'Base Case', 'Best Case', 'Rationale', 'Validation Source'], driver_rows)}\n\n"
        "### Assumption Table\n\n"
        f"{_table(['Assumption', 'Base Case', 'Low Case', 'High Case', 'Rationale', 'Validation Source'], rows)}\n\n"
        "### Break-Even Logic\n\n"
        f"{break_even_text}\n\n"
        "### Financial Logic\n\n"
        f"{_bullets(report.financial_assumptions.simple_financial_logic)}\n\n"
        "### Sensitivities\n\n"
        f"{_bullets(report.financial_assumptions.sensitivities)}"
    )


def _scenario_analysis(report: FinalConsultingReport) -> str:
    if not report.financial_assumptions:
        return "## Scenario Analysis\n\nNot provided."
    scenario_rows = [
        (
            item.scenario,
            _format_number(item.price),
            _format_number(item.volume),
            _format_number(item.variable_cost_per_unit),
            _format_number(item.fixed_cost),
            _format_number(item.revenue),
            _format_number(item.variable_cost),
            _format_number(item.gross_profit),
            _format_number(item.gross_margin, is_ratio=True),
            _format_number(item.break_even_units),
            _format_number(item.operating_profit),
            item.notes,
        )
        for item in report.financial_assumptions.scenarios
    ]
    return "## Scenario Analysis\n\n" + _table(
        [
            "Scenario",
            "Price",
            "Volume",
            "Variable Cost / Unit",
            "Fixed Cost",
            "Revenue",
            "Variable Cost",
            "Gross Profit",
            "Gross Margin",
            "Break-Even Units",
            "Operating Profit",
            "Notes",
        ],
        scenario_rows,
    )


def _recommendation(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return "## Recommendation\n\nNot provided."
    memo = report.executive_memo
    return (
        "## Recommendation\n\n"
        f"{memo.recommendation}\n\n"
        "### Rationale\n\n"
        f"{_bullets(memo.rationale)}\n\n"
        f"**Financial implications:** {memo.financial_implications}"
    )


def _key_risks(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return "## Key Risks\n\nNot provided."
    rows = [
        (risk.risk, risk.why_it_matters)
        for risk in report.executive_memo.risks_and_mitigations
    ]
    return "## Key Risks\n\n" + _table(["Risk", "Why It Matters"], rows)


def _mitigation_plan(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return "## Mitigation Plan\n\nNot provided."
    rows = [
        (risk.risk, risk.mitigation)
        for risk in report.executive_memo.risks_and_mitigations
    ]
    return "## Mitigation Plan\n\n" + _table(["Risk", "Mitigation"], rows)


def _assumption_register(report: FinalConsultingReport) -> str:
    rows = [
        (
            item.assumption,
            item.source,
            item.importance,
            item.validation_needed,
        )
        for item in report.assumption_register
    ]
    return "## Assumption Register\n\n" + _table(
        ["Assumption", "Source", "Importance", "Validation Needed"],
        rows,
    )


def _data_gaps(report: FinalConsultingReport) -> str:
    return "## Data Gaps\n\n" + _bullets(report.data_gaps)


def _action_plan(report: FinalConsultingReport) -> str:
    return (
        "## Next 30 / 60 / 90 Day Action Plan\n\n"
        "### Next 30 Days\n\n"
        f"{_bullets(report.action_plan.next_30_days)}\n\n"
        "### Next 60 Days\n\n"
        f"{_bullets(report.action_plan.next_60_days)}\n\n"
        "### Next 90 Days\n\n"
        f"{_bullets(report.action_plan.next_90_days)}"
    )


def _deck_outline(report: FinalConsultingReport) -> str:
    if not report.deck_outline:
        return "## 10-Slide Pitch Deck Outline\n\nNot provided."
    rows = [
        (
            str(slide.slide_number),
            slide.title,
            slide.core_message,
            slide.suggested_visual,
            _join(slide.key_bullets),
        )
        for slide in report.deck_outline.slides
    ]
    return "## 10-Slide Pitch Deck Outline\n\n" + _table(
        ["Slide", "Title", "Core Message", "Suggested Visual", "Key Bullets"],
        rows,
    )


def _critic_review(report: FinalConsultingReport) -> str:
    if not report.critic:
        return "## Critic Review\n\nNot provided."
    critic = report.critic
    return (
        "## Critic Review\n\n"
        f"**Overall score:** {critic.overall_score}/5\n\n"
        "### Strengths\n\n"
        f"{_bullets(critic.strengths)}\n\n"
        "### Weaknesses\n\n"
        f"{_bullets(critic.weaknesses)}\n\n"
        "### Critical Gaps\n\n"
        f"{_bullets(critic.critical_gaps)}\n\n"
        "### Recommended Improvements\n\n"
        f"{_bullets(critic.recommended_improvements)}\n\n"
        f"**Final verdict:** {critic.final_verdict}"
    )


def _bullets(items: list[str]) -> str:
    if not items:
        return "Not provided."
    return "\n".join(f"- {_clean(item)}" for item in items)


def _table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        return "Not provided."
    header_row = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_clean(value) for value in row) + " |" for row in rows]
    return "\n".join([header_row, divider, *body])


def _join(items: list[str]) -> str:
    return "; ".join(_clean(item) for item in items) if items else "Not provided."


def _clean(value: str) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


def _format_number(value: float | None, is_ratio: bool = False) -> str:
    if value is None:
        return "Not provided."
    if is_ratio:
        return f"{value * 100:.1f}%"
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"
