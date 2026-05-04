from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from core.config import AppConfig
from core.schemas import BusinessProblemInput
from core.workflow import WORKFLOW_STEPS, run_consulting_workflow
from utils.app_logging import get_app_logger
from utils.json_parser import JsonParsingError
from utils.startup_validation import StartupValidationResult, validate_startup
from utils.ui_components import (
    apply_design_system,
    render_action_plan,
    render_assumption_table,
    render_confidence_badge,
    render_concise_bullets,
    render_critic_review,
    render_decision_callout,
    render_empty_state,
    render_export_center,
    render_hero,
    render_issue_tree_cards,
    render_metric_card,
    render_option_card,
    render_risk_table,
    render_section_header,
    render_summary_card,
)


TAB_LABELS = {
    "problem_framing": "Problem Framing",
    "issue_tree": "Issue Tree",
    "hypotheses": "Hypotheses",
    "analysis_plan": "Analysis Plan",
    "financial_assumptions": "Financial Assumptions",
    "executive_memo": "Executive Memo",
    "deck_outline": "Deck Outline",
    "critic": "Critic Review",
}

SAMPLE_CASES_PATH = Path("examples/sample_cases.json")
EVALUATIONS_PATH = Path("eval_outputs/evaluations.json")
FORM_FIELD_KEYS = {
    "business_problem",
    "geography",
    "budget",
    "target_customers",
    "constraints",
    "expected_output",
}


st.set_page_config(
    page_title="AI Business Consulting Agent",
    layout="wide",
)


def initialize_state() -> None:
    if "outputs" not in st.session_state:
        st.session_state.outputs = None
    if "report" not in st.session_state:
        st.session_state.report = None
    if "business_input" not in st.session_state:
        st.session_state.business_input = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "selected_sample_case" not in st.session_state:
        st.session_state.selected_sample_case = "Start from a blank case"


def load_sample_cases(path: Path = SAMPLE_CASES_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        return []
    return [case for case in cases if isinstance(case, dict) and case.get("name")]


def apply_sample_case(sample_case: dict[str, Any]) -> None:
    st.session_state.business_problem = sample_case.get("business_problem") or sample_case.get("problem", "")
    st.session_state.geography = sample_case.get("geography", "")
    st.session_state.budget = sample_case.get("budget", "")
    st.session_state.target_customers = sample_case.get("target_customers", "")
    st.session_state.constraints = sample_case.get("constraints", "")
    st.session_state.expected_output = sample_case.get("expected_output", "")


def clear_input_form() -> None:
    for field_key in FORM_FIELD_KEYS:
        st.session_state[field_key] = ""


def reset_workspace() -> None:
    st.session_state.outputs = None
    st.session_state.report = None
    st.session_state.business_input = None
    st.session_state.error = None
    st.session_state.selected_sample_case = "Start from a blank case"
    clear_input_form()


def load_evaluations(path: Path = EVALUATIONS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    try:
        with path.open(encoding="utf-8") as file:
            evaluations = json.load(file)
    except json.JSONDecodeError:
        return []

    if not isinstance(evaluations, list):
        return []
    return [evaluation for evaluation in evaluations if isinstance(evaluation, dict)]


def save_evaluation(evaluation: dict[str, Any], path: Path = EVALUATIONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    evaluations = load_evaluations(path)
    evaluations.append(evaluation)

    with path.open("w", encoding="utf-8") as file:
        json.dump(evaluations, file, indent=2, ensure_ascii=False)


def build_evaluation_record(
    business_input: BusinessProblemInput,
    scores: dict[str, int],
    notes: str,
) -> dict[str, Any]:
    quality_scores = [
        scores["clarity"],
        scores["mece_structure"],
        scores["practicality"],
        scores["data_backed_reasoning"],
        scores["executive_readiness"],
    ]
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "business_problem": business_input.problem,
        "budget": business_input.budget,
        "geography": business_input.geography,
        "scores": scores,
        "average_quality_score": round(sum(quality_scores) / len(quality_scores), 2),
        "notes": notes.strip(),
    }


def configure_streamlit_secrets_environment() -> None:
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL", "PROMPTS_DIR"):
        if os.getenv(key):
            continue
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
        if value:
            os.environ[key] = str(value)


def render_sidebar(config: AppConfig) -> None:
    with st.sidebar:
        st.header("Mission Control")
        st.caption("Premium AI workspace for structured strategy analysis and executive-ready deliverables.")

        render_sidebar_sample_case_selector()
        render_sidebar_business_summary()

        st.divider()
        render_section_header("Analysis Mode")
        st.caption("Mode: Structured consulting workflow")
        st.text_input("Model", value=config.model, key="model_name")
        st.caption("Set `OPENAI_MODEL` in `.env` or deployment secrets to change the default.")

        render_section_header("Workflow Progress")
        st.markdown(
            "1. Problem framing\n"
            "2. Issue tree\n"
            "3. Hypotheses\n"
            "4. Analysis plan\n"
            "5. Financial assumptions\n"
            "6. Executive memo\n"
            "7. Deck outline\n"
            "8. Critic review"
        )

        render_sidebar_export_center()

        st.divider()
        st.button("Reset workspace", use_container_width=True, on_click=reset_workspace)


def render_sidebar_sample_case_selector() -> None:
    sample_cases = load_sample_cases()
    if not sample_cases:
        return

    render_section_header("Sample Case Selector")
    options = ["Start from a blank case", *[case["name"] for case in sample_cases]]
    selected = st.selectbox(
        "Sample case",
        options,
        key="selected_sample_case",
        help="Choose a sample to auto-fill the project brief.",
    )
    selected_case = next((case for case in sample_cases if case["name"] == selected), None)
    if st.button("Use sample case", disabled=selected_case is None, use_container_width=True):
        apply_sample_case(selected_case)
        st.rerun()


def render_sidebar_business_summary() -> None:
    render_section_header("Business Input Summary")
    problem = st.session_state.get("business_problem") or "No project brief yet."
    geography = st.session_state.get("geography") or "Not specified"
    budget = st.session_state.get("budget") or "Not specified"
    st.caption(problem[:180])
    st.markdown(f"**Geography:** {geography}")
    st.markdown(f"**Budget:** {budget}")


def render_sidebar_export_center() -> None:
    report = st.session_state.report
    if not report:
        return

    st.divider()
    render_section_header("Export Center")
    render_export_center(report)


def render_startup_status(validation: StartupValidationResult, config: AppConfig) -> None:
    with st.sidebar:
        st.divider()
        render_section_header("Health")
        if validation.is_ready:
            st.success("Startup checks passed.")
        else:
            st.warning("Startup checks need attention.")

        if config.has_api_key:
            st.caption("OpenAI API key is configured.")
        else:
            st.caption("OpenAI API key is not configured.")

        with st.expander("Startup checks"):
            for name, passed in validation.checks.items():
                status = "OK" if passed else "Needs attention"
                st.write(f"{name}: {status}")
            for warning in validation.warnings:
                st.warning(warning)


def render_input_form() -> BusinessProblemInput | None:
    with st.form("business_problem_form"):
        render_section_header("Project Brief", "Define the decision context the consulting workflow should solve.")
        problem = st.text_area(
            "Business problem",
            placeholder="Example: Should we launch a premium subscription tier for SMB customers?",
            height=120,
            key="business_problem",
        )

        col1, col2 = st.columns(2)
        with col1:
            geography = st.text_input("Geography", placeholder="Example: United States", key="geography")
            budget = st.text_input("Budget", placeholder="Example: $500k launch budget", key="budget")
            target_customers = st.text_area(
                "Target customers",
                placeholder="Example: B2B SaaS companies with 20-250 employees",
                height=100,
                key="target_customers",
            )
        with col2:
            constraints = st.text_area(
                "Constraints",
                placeholder="Example: Must launch in 90 days; no new engineering hires",
                height=100,
                key="constraints",
            )
            expected_output = st.text_area(
                "Expected output",
                placeholder="Example: A go/no-go recommendation with financial assumptions",
                height=100,
                key="expected_output",
            )

        submitted = st.form_submit_button("Run analysis", type="primary", use_container_width=True)

    st.button("Clear project brief", use_container_width=True, on_click=clear_input_form)

    if not submitted:
        return None

    if not problem.strip():
        st.warning("Please enter a business problem before running the analysis.")
        return None

    return BusinessProblemInput(
        problem=problem.strip(),
        budget=budget.strip() or "Not specified",
        geography=geography.strip() or "Not specified",
        target_customers=target_customers.strip() or "Not specified",
        constraints=constraints.strip() or "Not specified",
        expected_output=expected_output.strip() or "Not specified",
    )


def render_outputs() -> None:
    outputs = st.session_state.outputs
    report = st.session_state.report
    if not outputs or not report:
        return

    st.divider()
    render_section_header("Consultant Canvas", "Review the generated strategy work product by decision area.")
    render_intelligence_panel(report)
    render_main_export_center(report)

    tabs = st.tabs(
        [
            "Overview",
            "Issue Tree",
            "Hypotheses",
            "Strategic Options",
            "Financials",
            "Risks",
            "Action Plan",
            "Deck Outline",
            "Critic Review",
        ]
    )

    with tabs[0]:
        render_overview_tab(report)
    with tabs[1]:
        render_issue_tree_tab(report)
    with tabs[2]:
        render_hypotheses_tab(report)
    with tabs[3]:
        render_strategic_options_tab(report)
    with tabs[4]:
        render_financials_tab(report)
    with tabs[5]:
        render_risks_tab(report)
    with tabs[6]:
        render_action_plan_tab(report)
    with tabs[7]:
        render_deck_outline_tab(report)
    with tabs[8]:
        render_critic_review_tab(report)


def render_main_export_center(report) -> None:
    render_section_header("Export Center", "Download the completed consulting work product as Markdown or PowerPoint.")
    render_export_center(report)
    st.caption("PowerPoint export generates a consulting-style `.pptx` deck from the final report.")


def render_intelligence_panel(report) -> None:
    critic_score = report.critic.overall_score if report.critic else None
    confidence = _confidence_label(critic_score)
    assumptions_count = len(report.assumption_register)
    risks_count = len(report.executive_memo.risks_and_mitigations) if report.executive_memo else 0
    data_gaps_count = len(report.data_gaps)
    revision_status = _revision_status(critic_score, data_gaps_count)

    metric_cols = st.columns(6)
    with metric_cols[0]:
        render_metric_card("Critic Score", f"{critic_score}/5" if critic_score else "N/A")
    with metric_cols[1]:
        render_metric_card("Confidence", confidence)
        render_confidence_badge(confidence)
    with metric_cols[2]:
        render_metric_card("Assumptions", str(assumptions_count))
    with metric_cols[3]:
        render_metric_card("Risks", str(risks_count))
    with metric_cols[4]:
        render_metric_card("Data Gaps", str(data_gaps_count))
    with metric_cols[5]:
        render_metric_card("Revision Status", revision_status)


def render_overview_tab(report) -> None:
    render_section_header("Overview", "Executive summary, decision question, and business context.")
    if report.problem_framing:
        render_decision_callout(report.problem_framing.decision_question)
    summary_bullets = []
    if report.executive_memo:
        summary_bullets.append(f"Recommendation: {report.executive_memo.recommendation}")
        summary_bullets.extend(report.executive_memo.rationale)
    if report.critic:
        summary_bullets.append(f"Critic review: {report.critic.overall_score}/5 - {report.critic.final_verdict}")
    render_summary_card("Executive Summary", summary_bullets)
    if report.problem_framing:
        with st.expander("Success criteria and key unknowns"):
            st.markdown("**Success Criteria**")
            _render_bullets(report.problem_framing.success_criteria)
            st.markdown("**Key Unknowns**")
            _render_bullets(report.problem_framing.key_unknowns)
    st.markdown("### Key Business Objective")
    st.write(report.key_business_objective or "Not provided.")
    with st.expander("Situation / context"):
        _render_bullets(report.situation_context)


def render_issue_tree_tab(report) -> None:
    render_section_header("Issue Tree", "MECE structure and highest-leverage branches.")
    if not report.issue_tree:
        st.info("Issue tree not generated yet.")
        return
    render_issue_tree_cards(report.issue_tree)
    with st.expander("Branch logic"):
        st.write(report.issue_tree.branch_logic)
    st.markdown("### Highest-Leverage Branches")
    render_concise_bullets(report.issue_tree.highest_leverage_branches)


def render_hypotheses_tab(report) -> None:
    render_section_header("Hypotheses", "Testable beliefs, evidence needs, and decision impact.")
    if not report.hypotheses:
        st.info("Hypotheses not generated yet.")
        return
    rows = [
        {
            "Hypothesis": item.hypothesis,
            "Why It Matters": item.why_it_matters,
            "Evidence Needed": item.evidence_needed,
            "Decision Impact": item.potential_decision_impact,
        }
        for item in report.hypotheses.hypotheses
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.markdown(f"**Initial lean:** {report.hypotheses.initial_lean}")


def render_strategic_options_tab(report) -> None:
    render_section_header("Strategic Options", "Alternative paths and tradeoffs for management decision-making.")
    rows = [
        {
            "Option": item.option,
            "Description": item.description,
            "Upside": item.upside,
            "Downside": item.downside,
            "Decision Implication": item.decision_implication,
        }
        for item in report.strategic_options
    ]
    if not rows:
        render_empty_state("No strategic options", "Strategic options have not been generated yet.")
    option_cols = st.columns(3) if report.strategic_options else []
    for index, option in enumerate(report.strategic_options[:3]):
        with option_cols[index % 3]:
            render_option_card(option)
    with st.expander("Strategic options comparison table"):
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
    st.markdown("### Market / Customer / Competitor Considerations")
    render_concise_bullets(report.market_customer_competitor_considerations, expander_label="More considerations")


def render_financials_tab(report) -> None:
    render_section_header("Financials", "Financial assumptions, scenario analysis, and assumption register.")
    if not report.financial_assumptions:
        st.info("Financial assumptions not generated yet.")
        return
    st.markdown("### Financial Assumptions")
    render_assumption_table(report.financial_assumptions.assumptions)
    scenarios = [
        {
            "Scenario": item.scenario,
            "Revenue": item.revenue,
            "Gross Margin": item.gross_margin,
            "Break-Even Units": item.break_even_units,
            "Operating Profit": item.operating_profit,
        }
        for item in report.financial_assumptions.scenarios
    ]
    st.markdown("### Scenario Analysis")
    st.dataframe(scenarios, use_container_width=True, hide_index=True)
    with st.expander("Assumption Register"):
        render_assumption_table(report.assumption_register)


def render_risks_tab(report) -> None:
    render_section_header("Risks", "Key risks, business impact, and mitigation plan.")
    if not report.executive_memo:
        st.info("Risks not generated yet.")
        return
    render_risk_table(report.executive_memo.risks_and_mitigations)
    st.markdown("### Data Gaps")
    render_concise_bullets(report.data_gaps, expander_label="More data gaps")


def render_action_plan_tab(report) -> None:
    render_section_header("Action Plan", "Next 30 / 60 / 90 day execution path.")
    render_action_plan(report.action_plan)


def render_deck_outline_tab(report) -> None:
    render_section_header("Deck Outline", "Suggested 10-slide management presentation storyline.")
    if not report.deck_outline:
        st.info("Deck outline not generated yet.")
        return
    rows = [
        {
            "#": item.slide_number,
            "Slide": item.title,
            "Core Message": item.core_message,
            "Suggested Visual": item.suggested_visual,
            "Key Bullets": "; ".join(item.key_bullets),
        }
        for item in report.deck_outline.slides
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_critic_review_tab(report) -> None:
    render_section_header("Critic Review", "Quality notes from the senior-manager critic plus user evaluation.")
    render_critic_review(report.critic)
    st.divider()
    render_evaluation_tab(report.business_input)


def _confidence_label(score: int | None) -> str:
    if score is None:
        return "Pending"
    if score >= 4:
        return "High"
    if score == 3:
        return "Medium"
    return "Low"


def _revision_status(score: int | None, data_gaps_count: int) -> str:
    if score is None:
        return "Pending"
    if score >= 4 and data_gaps_count <= 3:
        return "Ready"
    return "Revise"


def _render_bullets(items: list[str]) -> None:
    if not items:
        st.write("Not provided.")
        return
    for item in items:
        st.markdown(f"- {item}")


def render_evaluation_tab(business_input: BusinessProblemInput) -> None:
    render_section_header("Quality Score", "Score the generated consulting output and maintain a lightweight review history.")
    st.caption("Score the generated consulting output from 1 to 5. For hallucination risk, 1 means low risk and 5 means high risk.")

    with st.form("evaluation_form"):
        col1, col2 = st.columns(2)
        with col1:
            clarity = st.slider("Clarity", 1, 5, 3)
            mece_structure = st.slider("MECE structure", 1, 5, 3)
            practicality = st.slider("Practicality", 1, 5, 3)
        with col2:
            data_backed_reasoning = st.slider("Data-backed reasoning", 1, 5, 3)
            executive_readiness = st.slider("Executive readiness", 1, 5, 3)
            hallucination_risk = st.slider("Hallucination risk", 1, 5, 3)

        notes = st.text_area(
            "Notes",
            placeholder="Add reviewer notes, concerns, or follow-up actions.",
            height=120,
        )
        submitted = st.form_submit_button("Save evaluation", type="primary")

    if submitted:
        scores = {
            "clarity": clarity,
            "mece_structure": mece_structure,
            "practicality": practicality,
            "data_backed_reasoning": data_backed_reasoning,
            "executive_readiness": executive_readiness,
            "hallucination_risk": hallucination_risk,
        }
        save_evaluation(build_evaluation_record(business_input, scores, notes))
        st.success(f"Evaluation saved to `{EVALUATIONS_PATH}`.")

    st.divider()
    render_section_header("Historical Evaluations")
    evaluations = load_evaluations()
    if not evaluations:
        st.info("No evaluations saved yet.")
        return

    st.dataframe(_evaluation_table_rows(evaluations), use_container_width=True, hide_index=True)


def _evaluation_table_rows(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for evaluation in reversed(evaluations[-50:]):
        scores = evaluation.get("scores", {})
        rows.append(
            {
                "Timestamp": evaluation.get("timestamp", ""),
                "Business Problem": evaluation.get("business_problem", ""),
                "Clarity": scores.get("clarity", ""),
                "MECE": scores.get("mece_structure", ""),
                "Practicality": scores.get("practicality", ""),
                "Data-Backed": scores.get("data_backed_reasoning", ""),
                "Executive Ready": scores.get("executive_readiness", ""),
                "Hallucination Risk": scores.get("hallucination_risk", ""),
                "Quality Avg": evaluation.get("average_quality_score", evaluation.get("average_score", "")),
                "Notes": evaluation.get("notes", ""),
            }
        )
    return rows


def main() -> None:
    initialize_state()
    configure_streamlit_secrets_environment()
    apply_design_system()
    logger = get_app_logger()
    config = AppConfig.from_env()
    validation = validate_startup(
        prompts_dir=config.prompts_dir,
        sample_cases_path=SAMPLE_CASES_PATH,
        writable_dirs=(Path("logs"), EVALUATIONS_PATH.parent),
    )
    render_sidebar(config)
    render_startup_status(validation, config)

    render_hero(
        "AI Business Consulting Agent",
        "Turn a business question into a structured recommendation, financial logic, pitch deck outline, and critic-reviewed executive report.",
    )

    if not config.has_api_key:
        st.error(config.missing_api_key_message)

    business_input = render_input_form()

    if business_input and config.has_api_key:
        st.session_state.error = None
        st.session_state.business_input = business_input
        model = st.session_state.get("model_name") or config.model
        workflow_config = config.with_model(model)

        st.divider()
        st.subheader("Running Analysis")
        progress = st.progress(0)
        status = st.empty()

        try:
            total_steps = len(WORKFLOW_STEPS)

            def update_progress(index, step, output):
                status.write(f"Completed {index} of {total_steps}: {TAB_LABELS.get(output.key, output.title)}")
                progress.progress(index / total_steps)

            with st.spinner("Running the consulting workflow..."):
                report = run_consulting_workflow(
                    input_data=business_input,
                    config=workflow_config,
                    progress_callback=update_progress,
                )

            st.session_state.report = report
            st.session_state.outputs = report.intermediate_results
            status.success("Analysis complete.")
        except JsonParsingError as exc:
            raw_output_path = getattr(exc, "raw_output_path", None)
            st.session_state.error = "A model response could not be converted into the expected structured JSON."
            st.error("The analysis stopped because one model response was not valid structured JSON.")
            st.info(
                "The raw response was saved locally for debugging. "
                "Try running the analysis again, or review the saved output before changing prompts."
            )
            if raw_output_path:
                st.caption(f"Saved raw output: `{raw_output_path}`")
            logger.warning(
                "streamlit_error status=json_parse_failed raw_output_path=%s error_type=%s",
                raw_output_path,
                type(exc).__name__,
            )
        except ValueError as exc:
            st.session_state.error = str(exc)
            st.error(str(exc))
            logger.warning("streamlit_error status=value_error error_type=%s", type(exc).__name__)
        except RuntimeError as exc:
            st.session_state.error = "The model request failed after retries."
            st.error("The model request failed after retries. Please check your network connection and try again.")
            logger.warning("streamlit_error status=runtime_error error_type=%s message=%s", type(exc).__name__, exc)
        except Exception as exc:
            st.session_state.error = "Analysis failed unexpectedly."
            st.error("Analysis failed unexpectedly. Please check the local logs for details and try again.")
            logger.exception("streamlit_error status=unexpected error_type=%s", type(exc).__name__)

    render_outputs()


if __name__ == "__main__":
    main()
