from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.schemas import FinalConsultingReport


MAX_BULLETS = 5
MAX_TABLE_ROWS = 5
MAX_TEXT_CHARS = 150


@dataclass
class SlideTable:
    headers: list[str]
    rows: list[tuple[str, ...]]
    overflow_rows: list[tuple[str, ...]] = field(default_factory=list)


@dataclass
class SlideContent:
    title: str
    subtitle: str
    key_message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeckContent:
    slides: list[SlideContent]
    appendix: list[SlideContent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def adapt_report_for_slides(report: FinalConsultingReport) -> DeckContent:
    appendix: list[SlideContent] = []
    _append_saved_analysis_results(appendix, report)
    slides = [
        _title_content(report),
        _section_divider_content(report),
        _executive_summary_content(report),
        _decision_context_content(report, appendix),
        _issue_tree_content(report, appendix),
        _hypotheses_content(report, appendix),
        _analytics_plan_content(report, appendix),
        _options_content(report, appendix),
        _recommendation_content(report),
        _financials_content(report, appendix),
        _risks_content(report, appendix),
        _action_plan_content(report, appendix),
        _storyboard_content(report, appendix),
        _critic_content(report),
    ]
    warnings = qa_slide_content(slides, appendix)
    return DeckContent(slides=slides, appendix=appendix, warnings=warnings)


def _append_saved_analysis_results(appendix: list[SlideContent], report: FinalConsultingReport) -> None:
    if not report.data_analysis_results:
        return
    bullets = [
        _shorten(f"{result.title}: {result.summary}", 150)
        for result in report.data_analysis_results[:6]
    ]
    appendix.append(
        SlideContent(
            title="Saved Dataset Analysis Results",
            subtitle="Appendix",
            key_message="Predefined pandas analyses run on the uploaded dataset.",
            payload={"bullets": bullets},
        )
    )


def qa_slide_content(slides: list[SlideContent], appendix: list[SlideContent] | None = None) -> list[str]:
    warnings: list[str] = []
    exported_appendix = (appendix or [])[:4]
    all_slides = slides + exported_appendix
    if len(all_slides) > 18:
        warnings.append(f"Slide count is high ({len(all_slides)} slides); consider tighter appendix handling.")

    for slide in all_slides:
        if not slide.title.strip():
            warnings.append("A generated slide is missing a title.")
        if not slide.key_message.strip():
            warnings.append(f"Slide '{slide.title}' is missing a clear key message.")

        for key, value in slide.payload.items():
            if isinstance(value, list):
                if len(value) > MAX_BULLETS and key not in {"cards", "columns", "options"}:
                    warnings.append(f"Slide '{slide.title}' has a long list in '{key}' ({len(value)} items).")
                for item in value:
                    if isinstance(item, str) and len(item) > MAX_TEXT_CHARS + 25:
                        warnings.append(f"Slide '{slide.title}' has a long bullet in '{key}'.")
            if isinstance(value, SlideTable):
                max_columns = 5 if "Storyboard" in slide.title else 4
                if len(value.headers) > max_columns:
                    warnings.append(f"Slide '{slide.title}' table has {len(value.headers)} columns.")
                row_limit = 10 if "Storyboard" in slide.title else MAX_TABLE_ROWS
                if len(value.rows) > row_limit:
                    warnings.append(f"Slide '{slide.title}' table has {len(value.rows)} rows.")
    return warnings


def _title_content(report: FinalConsultingReport) -> SlideContent:
    return SlideContent(
        title="AI Consulting OS Strategy Work Product",
        subtitle="First-Pass Executive Strategy Deck",
        key_message=_shorten(report.business_input.problem, 170),
        payload={
            "problem": _shorten(report.business_input.problem, 220),
            "geography": _shorten(report.business_input.geography, 80),
            "customers": _shorten(report.business_input.target_customers, 90),
            "budget": _shorten(report.business_input.budget, 70),
            "expected_output": _shorten(report.business_input.expected_output, 150),
        },
    )


def _section_divider_content(report: FinalConsultingReport) -> SlideContent:
    decision = report.problem_framing.decision_question if report.problem_framing else report.business_input.problem
    return SlideContent(
        title="Strategy Diagnosis",
        subtitle="From business question to first-pass executive view",
        key_message=_shorten(decision, 180),
        payload={"labels": ["Frame", "Analyze", "Synthesize", "Critique"]},
    )


def _executive_summary_content(report: FinalConsultingReport) -> SlideContent:
    recommendation = _recommendation(report)
    cards = [
        ("Decision Focus", _decision_question(report)),
        ("Recommended Direction", recommendation),
        ("Financial Logic", _financial_logic(report)),
        ("Quality Readiness", _quality_readiness(report)),
    ]
    return SlideContent(
        title="Executive Summary",
        subtitle="First-pass synthesis for management review",
        key_message=recommendation,
        payload={"cards": [(title, _shorten(body, 155)) for title, body in cards]},
    )


def _decision_context_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    context = _limit_list(report.situation_context or (report.problem_framing.context_summary if report.problem_framing else []), 4)
    constraints = _limit_list([report.business_input.constraints], 2)
    success = _limit_list(report.problem_framing.success_criteria if report.problem_framing else [], 4)
    unknowns = _limit_list(report.problem_framing.key_unknowns if report.problem_framing else [], 4)
    _append_overflow(appendix, "Decision Context Appendix", "Additional context and unknowns", context[1] + success[1] + unknowns[1])
    return SlideContent(
        title="Decision Context",
        subtitle="Decision question, context, constraints",
        key_message=_decision_question(report),
        payload={
            "decision": _decision_question(report),
            "context": context[0],
            "constraints": constraints[0],
            "success": success[0],
            "unknowns": unknowns[0],
        },
    )


def _issue_tree_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    if not report.issue_tree:
        return SlideContent("Issue Tree", "MECE structure", "No issue tree was generated.", {"branches": []})

    branches = []
    overflow = []
    for index, branch in enumerate(report.issue_tree.branches):
        item = {
            "name": _shorten(branch.name, 55),
            "question": _shorten(branch.questions[0] if branch.questions else "Not provided.", 105),
            "sub_branches": [_shorten(value, 42) for value in branch.sub_branches[:3]],
        }
        if index < 4:
            branches.append(item)
        else:
            overflow.append(branch.name)
    _append_overflow(appendix, "Issue Tree Appendix", "Additional issue branches", overflow)
    return SlideContent(
        title="Issue Tree",
        subtitle="Core workstreams and branch logic",
        key_message=_shorten(report.issue_tree.branch_logic, 175),
        payload={"branches": branches, "branch_logic": _shorten(report.issue_tree.branch_logic, 170)},
    )


def _hypotheses_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    if not report.hypotheses:
        return SlideContent("Key Hypotheses", "What must be true", "No hypotheses were generated.", {"table": SlideTable([], [])})

    rows = [
        (
            _shorten(item.hypothesis, 90),
            _shorten(item.evidence_needed, 80),
            _shorten(item.potential_decision_impact, 80),
        )
        for item in report.hypotheses.hypotheses
    ]
    table = _limit_table(["Hypothesis", "Evidence", "Decision Impact"], rows, 4)
    _append_table_overflow(appendix, "Hypotheses Appendix", "Additional hypotheses", table)
    return SlideContent(
        title="Key Hypotheses",
        subtitle="Evidence agenda",
        key_message=_shorten(report.hypotheses.initial_lean, 170),
        payload={"table": table, "initial_lean": _shorten(report.hypotheses.initial_lean, 150)},
    )


def _analytics_plan_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    if not report.analytics_plan:
        return SlideContent("Analytics Plan", "Hypothesis testing plan", "No analytics plan was generated.", {"table": SlideTable([], [])})

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    sorted_items = sorted(report.analytics_plan.plan, key=lambda item: priority_rank.get(item.priority, 1))
    rows = [
        (
            _shorten(item.hypothesis, 62),
            _shorten(item.business_metric_needed, 45),
            _shorten(item.recommended_analysis_method, 58),
            _shorten(item.decision_relevance, 70),
        )
        for item in sorted_items
    ]
    table = _limit_table(["Hypothesis", "Metric", "Method", "Decision Link"], rows, 5)
    _append_table_overflow(appendix, "Analytics Plan Appendix", "Additional analytics plan rows", table)
    return SlideContent(
        title="Analytics Plan",
        subtitle="Hypotheses to metrics, data, and methods",
        key_message=_shorten(report.analytics_plan.summary, 170),
        payload={"table": table},
    )


def _options_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    options = []
    overflow = []
    for index, option in enumerate(report.strategic_options):
        item = {
            "option": _shorten(option.option, 50),
            "description": _shorten(option.description, 120),
            "upside": _shorten(option.upside, 75),
            "downside": _shorten(option.downside, 75),
            "implication": _shorten(option.decision_implication, 85),
            "impact": _shorten(option.expected_impact, 75),
            "confidence": _shorten(option.confidence_level, 35),
        }
        if index < 3:
            options.append(item)
        else:
            overflow.append(option.option)
    _append_overflow(appendix, "Strategic Options Appendix", "Additional strategic options", overflow)
    return SlideContent(
        title="Strategic Options",
        subtitle="Comparison matrix",
        key_message=_shorten(options[0]["implication"] if options else "No strategic options were generated.", 160),
        payload={"options": options},
    )


def _recommendation_content(report: FinalConsultingReport) -> SlideContent:
    rationale = _limit_list(report.executive_memo.rationale if report.executive_memo else [], 4)[0]
    next_steps = _limit_list(report.action_plan.next_30_days, 3)[0]
    return SlideContent(
        title="Recommendation",
        subtitle="Decision and management implications",
        key_message=_recommendation(report),
        payload={
            "recommendation": _recommendation(report),
            "rationale": rationale,
            "financial_implication": _shorten(report.executive_memo.financial_implications if report.executive_memo else "", 155),
            "next_steps": next_steps,
        },
    )


def _financials_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    if not report.financial_assumptions:
        return SlideContent("Financials", "Assumptions and scenarios", "No financial assumptions were generated.", {})

    assumption_rows = [
        (_shorten(item.assumption, 82), _shorten(item.low_case, 42), _shorten(item.base_case_value, 42), _shorten(item.high_case, 42))
        for item in report.financial_assumptions.assumptions
    ]
    scenario_rows = [
        (
            _shorten(item.scenario, 45),
            _format_number(item.revenue),
            _format_percent(item.gross_margin),
            _format_number(item.operating_profit),
        )
        for item in report.financial_assumptions.scenarios
    ]
    assumptions = _limit_table(["Assumption", "Low", "Base", "High"], assumption_rows, 4)
    scenarios = _limit_table(["Scenario", "Revenue", "GM", "Op. Profit"], scenario_rows, 3)
    _append_table_overflow(appendix, "Financial Appendix", "Additional financial assumptions", assumptions)
    return SlideContent(
        title="Financials",
        subtitle="Driver assumptions and scenario logic",
        key_message=_financial_logic(report),
        payload={
            "assumptions": assumptions,
            "scenarios": scenarios,
            "break_even": _break_even(report),
        },
    )


def _risks_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    risks = report.executive_memo.risks_and_mitigations if report.executive_memo else []
    rows = [
        (_shorten(item.risk, 70), _shorten(item.why_it_matters, 80), _shorten(item.mitigation, 90), "Owner TBD")
        for item in risks
    ]
    table = _limit_table(["Risk", "Impact", "Mitigation", "Owner"], rows, 5)
    _append_table_overflow(appendix, "Risk Appendix", "Additional risks", table)
    return SlideContent(
        title="Risks & Mitigations",
        subtitle="Decision risks and controls",
        key_message=_shorten(rows[0][0] if rows else "No risks were generated.", 160),
        payload={"table": table},
    )


def _action_plan_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    columns = [
        ("Next 30 Days", _limit_list(report.action_plan.next_30_days, 5)[0]),
        ("Next 60 Days", _limit_list(report.action_plan.next_60_days, 5)[0]),
        ("Next 90 Days", _limit_list(report.action_plan.next_90_days, 5)[0]),
    ]
    overflow = []
    for source in [report.action_plan.next_30_days, report.action_plan.next_60_days, report.action_plan.next_90_days]:
        overflow.extend(_limit_list(source, 5)[1])
    _append_overflow(appendix, "Action Plan Appendix", "Additional action items", overflow)
    return SlideContent(
        title="30/60/90 Day Action Plan",
        subtitle="Execution and decision roadmap",
        key_message=_shorten(report.decision_roadmap[0] if report.decision_roadmap else "Translate the recommendation into near-term operating actions.", 170),
        payload={"columns": columns},
    )


def _storyboard_content(report: FinalConsultingReport, appendix: list[SlideContent]) -> SlideContent:
    rows = []
    if report.deck_outline:
        rows = [
            (
                str(item.slide_number),
                _shorten(item.title, 45),
                _shorten(item.pyramid_role, 40),
                _shorten(item.core_message, 85),
                _shorten(item.suggested_visual, 45),
            )
            for item in report.deck_outline.slides
        ]
    table = _limit_table(["#", "Slide", "Pyramid Role", "Core Message", "Visual"], rows, 10)
    _append_table_overflow(appendix, "Storyboard Appendix", "Additional storyboard slides", table)
    return SlideContent(
        title="Pitch Deck Storyboard",
        subtitle="Pyramid Principle storyline",
        key_message=_shorten(report.deck_outline.pyramid_principle_storyline[0] if report.deck_outline and report.deck_outline.pyramid_principle_storyline else "Use this storyline to convert the analysis into a management presentation.", 170),
        payload={"table": table},
    )


def _critic_content(report: FinalConsultingReport) -> SlideContent:
    if not report.critic:
        return SlideContent("Critic Review", "Quality notes", "No critic review was generated.", {})
    return SlideContent(
        title="Critic Review",
        subtitle="Executive readiness assessment",
        key_message=_shorten(report.critic.final_verdict, 170),
        payload={
            "score": f"{report.critic.overall_score}/5",
            "strengths": _limit_list(report.critic.strengths, 4)[0],
            "weaknesses": _limit_list(report.critic.weaknesses, 4)[0],
            "gaps": _limit_list(report.critic.critical_gaps + report.critic.red_team_challenges, 4)[0],
        },
    )


def _limit_list(items: list[str], limit: int) -> tuple[list[str], list[str]]:
    clean = [_shorten(item, MAX_TEXT_CHARS) for item in items if str(item or "").strip()]
    return clean[:limit], clean[limit:]


def _limit_table(headers: list[str], rows: list[tuple[str, ...]], limit: int) -> SlideTable:
    clean_rows = [tuple(_shorten(value, 120) for value in row) for row in rows]
    return SlideTable(headers=headers, rows=clean_rows[:limit], overflow_rows=clean_rows[limit:])


def _append_overflow(appendix: list[SlideContent], title: str, key_message: str, items: list[str]) -> None:
    if not items:
        return
    appendix.append(SlideContent(title=title, subtitle="Appendix", key_message=key_message, payload={"bullets": items[:8]}))


def _append_table_overflow(appendix: list[SlideContent], title: str, key_message: str, table: SlideTable) -> None:
    if not table.overflow_rows:
        return
    appendix.append(
        SlideContent(
            title=title,
            subtitle="Appendix",
            key_message=key_message,
            payload={"table": SlideTable(headers=table.headers, rows=table.overflow_rows[:8])},
        )
    )


def _decision_question(report: FinalConsultingReport) -> str:
    if report.problem_framing and report.problem_framing.decision_question:
        return _shorten(report.problem_framing.decision_question, 180)
    return _shorten(report.business_input.problem, 180)


def _recommendation(report: FinalConsultingReport) -> str:
    if report.executive_memo and report.executive_memo.recommendation:
        return _shorten(report.executive_memo.recommendation, 180)
    return _shorten(report.business_input.expected_output, 180)


def _financial_logic(report: FinalConsultingReport) -> str:
    if report.executive_memo and report.executive_memo.financial_implications:
        return _shorten(report.executive_memo.financial_implications, 170)
    return _break_even(report)


def _break_even(report: FinalConsultingReport) -> str:
    logic = report.financial_assumptions.break_even_logic if report.financial_assumptions else None
    if logic:
        return _shorten(f"{logic.formula}: {logic.interpretation}", 170)
    return "Financial logic should be validated through base, upside, and downside scenarios."


def _quality_readiness(report: FinalConsultingReport) -> str:
    if report.critic:
        return _shorten(f"{report.critic.overall_score}/5 - {report.critic.final_verdict}", 160)
    return "Critic review not available."


def _shorten(value: object, max_chars: int = MAX_TEXT_CHARS) -> str:
    text = str(value or "Not provided.").replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _format_number(value: float | None) -> str:
    if value is None:
        return "N/A"
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"
