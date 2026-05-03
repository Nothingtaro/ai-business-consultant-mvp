from __future__ import annotations

import re
from datetime import datetime

from core.schemas import (
    AnalysisPlanItem,
    BusinessInput,
    DeckSlide,
    FinalConsultingReport,
    FinancialAssumptionItem,
    HypothesisItem,
    IssueTreeBranch,
    RiskMitigation,
)


def build_markdown_report(report: FinalConsultingReport) -> str:
    sections = [
        "# AI Business Consulting Report",
        _executive_summary(report),
        _decision_question(report),
        _business_context(report.business_input),
        _issue_tree(report),
        _key_hypotheses(report),
        _analysis_plan(report),
        _financial_assumptions(report),
        _recommendation(report),
        _risks(report),
        _next_steps(report),
        _deck_outline(report),
        _critic_review(report),
    ]
    return "\n\n".join(section for section in sections if section).strip() + "\n"


def build_full_report(report: FinalConsultingReport) -> str:
    return build_markdown_report(report)


def safe_filename(name: str = "consulting_report.md") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.rsplit(".", 1)[0]).strip("_").lower()
    extension = name.rsplit(".", 1)[-1] if "." in name else "md"
    return f"{stem}_{timestamp}.{extension}"


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
        bullets.append(f"Confidence: {critic.recommendation_confidence} - {critic.confidence_rationale}")

    return "## Executive Summary\n\n" + _bullets(bullets)


def _decision_question(report: FinalConsultingReport) -> str:
    if not report.problem_framing:
        return ""
    framing = report.problem_framing
    return (
        "## Decision Question\n\n"
        f"{framing.decision_question}\n\n"
        "### Success Criteria\n\n"
        f"{_bullets(framing.success_criteria)}\n\n"
        "### Key Unknowns\n\n"
        f"{_bullets(framing.key_unknowns)}"
    )


def _business_context(business_input: BusinessInput) -> str:
    rows = [
        ("Business Problem", business_input.problem),
        ("Budget", business_input.budget),
        ("Geography", business_input.geography),
        ("Target Customers", business_input.target_customers),
        ("Constraints", business_input.constraints),
        ("Expected Output", business_input.expected_output),
    ]
    return "## Business Context\n\n" + _table(["Field", "Input"], rows)


def _issue_tree(report: FinalConsultingReport) -> str:
    if not report.issue_tree:
        return ""
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
        return ""
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
        return ""
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


def _financial_assumptions(report: FinalConsultingReport) -> str:
    if not report.financial_assumptions:
        return ""
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
    return (
        "## Financial Assumptions\n\n"
        f"{_table(['Assumption', 'Base Case', 'Low Case', 'High Case', 'Rationale', 'Validation Source'], rows)}\n\n"
        "### Financial Logic\n\n"
        f"{_bullets(report.financial_assumptions.simple_financial_logic)}\n\n"
        "### Sensitivities\n\n"
        f"{_bullets(report.financial_assumptions.sensitivities)}"
    )


def _recommendation(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return ""
    memo = report.executive_memo
    return (
        "## Recommendation\n\n"
        f"{memo.recommendation}\n\n"
        "### Rationale\n\n"
        f"{_bullets(memo.rationale)}\n\n"
        f"**Financial implications:** {memo.financial_implications}"
    )


def _risks(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return ""
    rows = [
        (risk.risk, risk.why_it_matters, risk.mitigation)
        for risk in report.executive_memo.risks_and_mitigations
    ]
    return "## Risks\n\n" + _table(["Risk", "Why It Matters", "Mitigation"], rows)


def _next_steps(report: FinalConsultingReport) -> str:
    if not report.executive_memo:
        return ""
    return "## Next Steps\n\n" + _bullets(report.executive_memo.next_30_days)


def _deck_outline(report: FinalConsultingReport) -> str:
    if not report.deck_outline:
        return ""
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
        return ""
    critic = report.critic
    return (
        "## Critic Review\n\n"
        "### Strongest Parts\n\n"
        f"{_bullets(critic.strongest_parts)}\n\n"
        "### Weakest Assumptions\n\n"
        f"{_bullets(critic.weakest_assumptions)}\n\n"
        "### Missing Analyses\n\n"
        f"{_bullets(critic.missing_analyses)}\n\n"
        "### Red-Team Objections\n\n"
        f"{_bullets(critic.red_team_objections)}\n\n"
        f"**Recommendation confidence:** {critic.recommendation_confidence}\n\n"
        f"**Confidence rationale:** {critic.confidence_rationale}\n\n"
        f"**Improved recommendation:** {critic.improved_recommendation}"
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
