from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from core.config import AppConfig
from core.schemas import AnalysisResult, BusinessProblemInput, DataProfile
from core.workflow import WORKFLOW_STEPS, run_consulting_workflow
from tools.analysis_tools import (
    get_categorical_columns,
    get_numeric_columns,
    run_eda,
    run_segmentation_analysis,
)
from tools.data_profiler import profile_uploaded_dataset
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
    "analytics_plan": "Analytics Plan",
    "analysis_plan": "Analysis Plan",
    "insight_synthesis": "Insight Synthesis",
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
    page_title="AI Consulting Operating System",
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
    if "uploaded_dataframe" not in st.session_state:
        st.session_state.uploaded_dataframe = None
    if "data_profile" not in st.session_state:
        st.session_state.data_profile = None
    if "uploaded_file_signature" not in st.session_state:
        st.session_state.uploaded_file_signature = None
    if "dataset_uploader_key" not in st.session_state:
        st.session_state.dataset_uploader_key = 0
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = []


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
    st.session_state.uploaded_dataframe = None
    st.session_state.data_profile = None
    st.session_state.uploaded_file_signature = None
    st.session_state.dataset_uploader_key += 1
    st.session_state.analysis_results = []
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
        st.header("Consulting OS")
        st.caption(
            "AI workspace for accelerating first-pass strategy and analytics work before human review."
        )

        render_sidebar_sample_case_selector()
        render_sidebar_dataset_upload()
        render_sidebar_business_summary()

        st.divider()
        render_section_header("Analysis Mode")
        st.caption("Mode: Top-tier strategy workflow with analytics-oriented deliverables")
        st.text_input("Model", value=config.model, key="model_name")
        st.caption("Set `OPENAI_MODEL` in `.env` or deployment secrets to change the default.")

        render_section_header("Workflow Progress")
        st.markdown(
            "1. Problem framing\n"
            "2. Issue tree\n"
            "3. Hypotheses\n"
            "4. Analytics planner\n"
            "5. Consulting analysis plan\n"
            "6. Insight synthesis\n"
            "7. Financial and data assumptions\n"
            "8. Executive memo\n"
            "9. Executive deck outline\n"
            "10. Partner-style critique"
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


def render_sidebar_dataset_upload() -> None:
    render_section_header("Dataset Upload")
    existing_profile = st.session_state.get("data_profile")
    if existing_profile:
        st.caption(f"Active profile: {existing_profile.file_name}")
        if st.button("Clear dataset", use_container_width=True):
            st.session_state.uploaded_dataframe = None
            st.session_state.data_profile = None
            st.session_state.uploaded_file_signature = None
            st.session_state.analysis_results = []
            st.session_state.dataset_uploader_key += 1
            st.rerun()

    uploaded_file = st.file_uploader(
        "CSV or XLSX",
        type=["csv", "xlsx"],
        key=f"dataset_upload_{st.session_state.dataset_uploader_key}",
        help="Optional. The app stores the dataframe in session memory and sends only profile metadata to the LLM.",
    )
    if uploaded_file is None:
        return

    signature = (uploaded_file.name, uploaded_file.size)
    if signature == st.session_state.uploaded_file_signature:
        return

    try:
        dataframe, profile = profile_uploaded_dataset(uploaded_file, uploaded_file.name)
    except Exception as exc:
        st.session_state.uploaded_dataframe = None
        st.session_state.data_profile = None
        st.session_state.uploaded_file_signature = None
        st.session_state.analysis_results = []
        st.error(f"Could not profile dataset: {exc}")
        return

    st.session_state.uploaded_dataframe = dataframe
    st.session_state.data_profile = profile
    st.session_state.analysis_results = []
    st.session_state.uploaded_file_signature = signature
    st.success(f"Profiled {profile.row_count:,} rows x {profile.column_count:,} columns.")


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
        render_section_header(
            "Project Brief",
            "Define the strategic question, operating context, and expected first-pass work product.",
        )
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

        submitted = st.form_submit_button("Run consulting workflow", type="primary", use_container_width=True)

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
    render_section_header(
        "Strategy Workbench",
        "Review the generated first-pass strategy and analytics work product by decision area.",
    )
    render_intelligence_panel(report)
    render_main_export_center(report)

    tabs = st.tabs(
        [
            "Overview",
            "Data Profile",
            "Trees",
            "Data & Evidence",
            "Insights",
            "Options",
            "Financials",
            "Risks",
            "Execution",
            "Stakeholders",
            "Deck Storyline",
            "Partner Review",
        ]
    )

    with tabs[0]:
        render_overview_tab(report)
    with tabs[1]:
        render_data_profile_tab(report)
    with tabs[2]:
        render_trees_tab(report)
    with tabs[3]:
        render_data_evidence_tab(report)
    with tabs[4]:
        render_insight_synthesis_tab(report)
    with tabs[5]:
        render_strategic_options_tab(report)
    with tabs[6]:
        render_financials_tab(report)
    with tabs[7]:
        render_risks_tab(report)
    with tabs[8]:
        render_execution_tab(report)
    with tabs[9]:
        render_stakeholder_lens_tab(report)
    with tabs[10]:
        render_deck_outline_tab(report)
    with tabs[11]:
        render_critic_review_tab(report)


def render_main_export_center(report) -> None:
    render_section_header(
        "Export Center",
        "Download the first-pass consulting work product as Markdown or PowerPoint for human review.",
    )
    render_export_center(report)
    st.caption("PowerPoint export generates an executive-style `.pptx` deck from the final report.")


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
    render_section_header("Overview", "Executive summary, decision question, and business context for review.")
    if report.problem_framing:
        render_decision_callout(report.problem_framing.decision_question)
        render_scq(report)
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
    render_section_header("Expected Impact", "Assumption-led until validated with uploaded data or source evidence.")
    render_concise_bullets(report.expected_impact)


def render_scq(report) -> None:
    scq = report.problem_framing.scq
    rows = [
        {"Element": "Situation", "Content": scq.situation or "Not provided."},
        {"Element": "Complication", "Content": scq.complication or "Not provided."},
        {"Element": "Question", "Content": scq.question or report.problem_framing.decision_question},
    ]
    st.markdown("### SCQ")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_data_profile_tab(report) -> None:
    profile = report.data_profile or st.session_state.get("data_profile")
    render_section_header("Data Profile", "Uploaded dataset metadata and summarized statistics.")
    if not profile:
        render_empty_state("No dataset uploaded", "The consulting workflow can run in text-only mode without a dataset.")
        return
    render_data_profile(profile)
    render_analytics_workbench()


def render_data_profile(profile: DataProfile) -> None:
    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_metric_card("File", profile.file_name)
    with metric_cols[1]:
        render_metric_card("Rows", f"{profile.row_count:,}")
    with metric_cols[2]:
        render_metric_card("Columns", f"{profile.column_count:,}")
    with metric_cols[3]:
        render_metric_card("Duplicates", f"{profile.duplicate_row_count:,}")

    render_section_header("Columns")
    st.dataframe(
        [
            {
                "Column": column,
                "Type": profile.inferred_dtypes.get(column, ""),
                "Missing": profile.missing_values.get(column, 0),
                "Missing %": profile.missing_percentages.get(column, 0),
            }
            for column in profile.column_names
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Numeric summary"):
        st.dataframe(_dict_table(profile.numeric_summary), use_container_width=True, hide_index=True)
    with st.expander("Categorical summary"):
        st.dataframe(_dict_table(profile.categorical_summary), use_container_width=True, hide_index=True)
    with st.expander("Sample rows"):
        st.dataframe(profile.sample_rows, use_container_width=True, hide_index=True)

    render_section_header("Data Quality Notes")
    render_concise_bullets(profile.data_quality_notes)
    render_section_header("Possible Analysis Suggestions")
    render_concise_bullets(profile.possible_analysis_suggestions)


def render_analytics_workbench() -> None:
    dataframe = st.session_state.get("uploaded_dataframe")
    if dataframe is None or dataframe.empty:
        return

    render_section_header(
        "Analytics Workbench",
        "Run focused, predefined pandas analysis templates on the uploaded dataset.",
    )
    numeric_columns = get_numeric_columns(dataframe)
    categorical_columns = get_categorical_columns(dataframe)
    all_columns = [str(column) for column in dataframe.columns]

    analysis_options = [
        "Data Exploration",
        "Segmentation Analysis",
    ]
    selected = st.selectbox("Analysis type", analysis_options, key="analysis_workbench_type")
    st.caption(_analysis_availability_note(selected, numeric_columns, categorical_columns))

    result = None
    if selected == "Data Exploration":
        if st.button("Run data exploration", type="primary"):
            result = run_eda(dataframe)
    elif selected == "Segmentation Analysis":
        segment_col = st.selectbox("Segment column", categorical_columns or all_columns, key="segmentation_segment_col")
        metric_col = st.selectbox("Metric column", numeric_columns or all_columns, key="segmentation_metric_col")
        weight_options = ["None", *numeric_columns]
        weight_col = st.selectbox("Optional weight column", weight_options, key="segmentation_weight_col")
        min_segment_size = st.number_input(
            "Minimum segment size",
            min_value=1,
            max_value=max(1, len(dataframe)),
            value=min(5, max(1, len(dataframe))),
            step=1,
            key="segmentation_min_segment_size",
        )
        if st.button("Run segmentation", type="primary"):
            result = run_segmentation_analysis(
                dataframe,
                segment_col,
                metric_col,
                None if weight_col == "None" else weight_col,
                int(min_segment_size),
            )

    if result:
        _save_analysis_result(result)
        st.success("Analysis result saved in session state.")
        render_analysis_result(result)

    saved_results = st.session_state.get("analysis_results", [])
    if saved_results:
        with st.expander(f"Saved analysis results ({len(saved_results)})", expanded=False):
            for index, saved in enumerate(saved_results, start=1):
                st.markdown(f"### {index}. {saved.title}")
                render_analysis_result(saved)


def render_analysis_result(result: AnalysisResult) -> None:
    if result.analysis_type == "data_exploration":
        render_data_exploration_result(result)
        return
    if result.analysis_type == "segmentation":
        render_segmentation_result(result)
        return

    render_section_header(result.title)
    st.write(result.summary)
    if result.key_metrics:
        st.markdown("### Key Metrics")
        st.dataframe([result.key_metrics], use_container_width=True, hide_index=True)
    if result.result_table:
        st.markdown("### Result Table")
        st.dataframe(result.result_table, use_container_width=True, hide_index=True)
    if result.warnings:
        st.markdown("### Warnings")
        render_concise_bullets(result.warnings)
    if result.limitations:
        st.markdown("### Limitations")
        render_concise_bullets(result.limitations)
    if result.suggested_next_steps:
        st.markdown("### Suggested Next Steps")
        render_concise_bullets(result.suggested_next_steps)


def render_data_exploration_result(result: AnalysisResult) -> None:
    render_section_header(result.title)
    metrics = result.key_metrics or {}
    overview = metrics.get("dataset_overview", {})
    quality = metrics.get("data_quality_assessment", {})
    readiness = metrics.get("business_analysis_readiness", {})
    numeric_profile = metrics.get("numeric_profile", [])
    categorical_profile = metrics.get("categorical_profile", [])
    date_profile = metrics.get("date_profile", [])

    st.write(metrics.get("executive_summary") or result.summary)

    metric_cols = st.columns(5)
    with metric_cols[0]:
        render_metric_card("Rows", f"{overview.get('row_count', 0):,}")
    with metric_cols[1]:
        render_metric_card("Columns", f"{overview.get('column_count', 0):,}")
    with metric_cols[2]:
        render_metric_card("Duplicates", f"{overview.get('duplicate_rows', 0):,}")
    with metric_cols[3]:
        render_metric_card("Memory MB", str(overview.get("memory_usage_mb", "N/A")))
    with metric_cols[4]:
        render_metric_card("Quality Score", f"{quality.get('data_quality_score', 'N/A')}/5")

    tabs = st.tabs(["Overview", "Column Profile", "Numeric", "Categorical", "Dates", "Readiness"])
    with tabs[0]:
        st.markdown("### Dataset Overview")
        st.dataframe([overview], use_container_width=True, hide_index=True)
        st.markdown("### Data Quality Assessment")
        quality_rows = [
            {"Area": "Missing Values", "Finding": _format_list_for_display(quality.get("missing_value_summary", []))},
            {"Area": "Duplicates", "Finding": quality.get("duplicate_summary", "Not provided.")},
            {"Area": "Constant Columns", "Finding": _format_list_for_display(quality.get("constant_columns", []))},
            {"Area": "Near-Constant Columns", "Finding": _format_list_for_display(quality.get("near_constant_columns", []))},
            {"Area": "High-Cardinality Categories", "Finding": _format_list_for_display(quality.get("high_cardinality_categorical_columns", []))},
            {"Area": "Potential ID Columns", "Finding": _format_list_for_display(quality.get("potential_id_columns", []))},
            {"Area": "Potential Leakage Columns", "Finding": _format_list_for_display(quality.get("potential_leakage_columns", []))},
            {"Area": "Suspicious Values", "Finding": _format_list_for_display(quality.get("suspicious_values", []))},
        ]
        st.dataframe(quality_rows, use_container_width=True, hide_index=True)
        if result.warnings:
            st.markdown("### Warnings")
            render_concise_bullets(result.warnings)
    with tabs[1]:
        st.markdown("### Column Profile")
        st.dataframe(result.result_table, use_container_width=True, hide_index=True)
    with tabs[2]:
        st.markdown("### Numeric Profile")
        if numeric_profile:
            st.dataframe(numeric_profile, use_container_width=True, hide_index=True)
        else:
            render_empty_state("No numeric profile", "No numeric columns were detected.")
    with tabs[3]:
        st.markdown("### Categorical Profile")
        if categorical_profile:
            flattened = []
            for row in categorical_profile:
                flattened.append(
                    {
                        "column": row.get("column"),
                        "cardinality": row.get("cardinality"),
                        "top_values": _format_top_values(row.get("top_values", [])),
                        "rare_category_count": row.get("rare_category_count"),
                        "long_tail_warning": row.get("long_tail_warning") or "",
                    }
                )
            st.dataframe(flattened, use_container_width=True, hide_index=True)
        else:
            render_empty_state("No categorical profile", "No categorical columns were detected.")
    with tabs[4]:
        st.markdown("### Date Profile")
        if date_profile:
            st.dataframe(date_profile, use_container_width=True, hide_index=True)
        else:
            render_empty_state("No date profile", "No date-like columns were detected.")
    with tabs[5]:
        st.markdown("### Business Analysis Readiness")
        readiness_rows = [
            {"Readiness Area": "Likely Segmentation Columns", "Columns": _format_list_for_display(readiness.get("likely_segmentation_columns", []))},
            {"Readiness Area": "Likely Target Metrics", "Columns": _format_list_for_display(readiness.get("likely_target_metric_columns", []))},
            {"Readiness Area": "Likely Revenue / Value Columns", "Columns": _format_list_for_display(readiness.get("likely_revenue_value_columns", []))},
            {"Readiness Area": "Likely Conversion / Binary Columns", "Columns": _format_list_for_display(readiness.get("likely_conversion_binary_columns", []))},
            {"Readiness Area": "Likely Date Columns", "Columns": _format_list_for_display(readiness.get("likely_date_columns", []))},
        ]
        st.dataframe(readiness_rows, use_container_width=True, hide_index=True)
        st.markdown("### Suggested Next Analyses")
        render_concise_bullets(readiness.get("suggested_next_analyses", result.suggested_next_steps))

    with st.expander("Limitations"):
        render_concise_bullets(result.limitations)


def render_segmentation_result(result: AnalysisResult) -> None:
    render_section_header(result.title)
    st.write(result.summary)
    metrics = result.key_metrics or {}

    metric_cols = st.columns(5)
    with metric_cols[0]:
        render_metric_card("Segments", str(metrics.get("segment_count", "N/A")))
    with metric_cols[1]:
        render_metric_card("Usable Rows", f"{metrics.get('usable_row_count', 0):,}")
    with metric_cols[2]:
        render_metric_card("Metric Total", str(metrics.get("metric_total", "N/A")))
    with metric_cols[3]:
        render_metric_card("Top 3 Share", f"{metrics.get('top_3_metric_share_pct', 'N/A')}%")
    with metric_cols[4]:
        render_metric_card("Min Size", str(metrics.get("minimum_segment_size", "N/A")))

    tabs = st.tabs(["Summary", "Top / Bottom", "Interpretation", "Scoring"])
    with tabs[0]:
        st.markdown("### Segment Summary Table")
        st.dataframe(result.result_table, use_container_width=True, hide_index=True)
        if result.warnings:
            st.markdown("### Warnings")
            render_concise_bullets(result.warnings)
    with tabs[1]:
        st.markdown("### Top 5 By Performance")
        _render_optional_dataframe(metrics.get("top_segments_by_performance", []), "No reliable top-performance segments.")
        st.markdown("### Top 5 By Total Contribution")
        _render_optional_dataframe(metrics.get("top_segments_by_total_contribution", []), "No contribution segments available.")
        st.markdown("### Bottom 5 By Performance")
        _render_optional_dataframe(metrics.get("bottom_segments_by_performance", []), "No reliable bottom-performance segments.")
        st.markdown("### Insufficient Sample")
        _render_optional_dataframe(metrics.get("segments_with_insufficient_sample", []), "No segments below the minimum size threshold.")
    with tabs[2]:
        interpretation = metrics.get("business_interpretation", {})
        st.markdown("### Attractive Segments")
        render_concise_bullets(interpretation.get("attractive_segments", []))
        st.markdown("### Underperforming Segments")
        render_concise_bullets(interpretation.get("underperforming_segments", []))
        st.markdown("### Requires Validation")
        render_concise_bullets(interpretation.get("segments_requiring_validation", []))
        st.markdown("### Business Actions To Consider")
        render_concise_bullets(interpretation.get("business_actions_to_consider", []))
        st.markdown("### Data Limitations")
        render_concise_bullets(interpretation.get("data_limitations", result.limitations))
    with tabs[3]:
        st.markdown("### Attractiveness Scoring Logic")
        st.write(metrics.get("scoring_logic", "Not provided."))
        st.markdown("### Recommended Actions")
        render_concise_bullets(metrics.get("recommended_actions", result.suggested_next_steps))
        with st.expander("General limitations"):
            render_concise_bullets(result.limitations)


def _save_analysis_result(result: AnalysisResult) -> None:
    st.session_state.analysis_results.append(result)


def render_trees_tab(report) -> None:
    render_section_header("Issue Tree", "MECE-style structure and highest-leverage branches.")
    if not report.issue_tree:
        st.info("Issue tree not generated yet.")
    else:
        render_issue_tree_cards(report.issue_tree)
        with st.expander("Branch logic"):
            st.write(report.issue_tree.branch_logic)
        st.markdown("### Highest-Leverage Branches")
        render_concise_bullets(report.issue_tree.highest_leverage_branches)

    render_section_header("Hypotheses", "Testable beliefs, evidence needs, and decision impact.")
    if not report.hypotheses:
        st.info("Hypotheses not generated yet.")
        return
    tree_rows = [
        {
            "Branch": item.branch,
            "Hypotheses": "; ".join(item.hypotheses),
            "Evidence Needed": "; ".join(item.evidence_needed),
            "Decision Link": item.decision_link,
        }
        for item in report.hypotheses.hypothesis_tree
    ]
    if tree_rows:
        st.markdown("### Hypothesis Tree")
        st.dataframe(tree_rows, use_container_width=True, hide_index=True)
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

    render_section_header("KPI / Driver Tree", "Management KPIs, core drivers, formulas, and data needed.")
    render_kpi_driver_tree(report)


def render_kpi_driver_tree(report) -> None:
    rows = [
        {
            "KPI": item.kpi,
            "Driver": item.driver,
            "Formula / Logic": item.formula_or_logic,
            "Data Needed": item.data_needed,
            "Assumption If No Data": item.assumption_if_no_data,
        }
        for item in report.kpi_driver_tree
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No KPI driver tree", "KPI and driver logic has not been generated yet.")


def render_data_evidence_tab(report) -> None:
    render_analytics_plan(report)

    render_section_header("Data Request List", "Data needed to separate validated findings from assumptions.")
    data_rows = [
        {
            "Data": item.data_name,
            "Purpose": item.purpose,
            "Owner": item.owner,
            "Priority": item.priority,
            "Required Fields": "; ".join(item.required_fields),
            "Assumption If Missing": item.assumption_if_missing,
        }
        for item in report.data_request_list
    ]
    if data_rows:
        st.dataframe(data_rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No data requests", "Data requests have not been generated yet.")

    render_section_header("Evidence Register", "Findings are labeled as data-backed or assumption-led.")
    evidence_rows = [
        {
            "Claim": item.claim,
            "Evidence": item.evidence,
            "Source": item.source,
            "Data-Backed": "Yes" if item.data_backed else "No - assumption-led",
            "Strength": item.strength,
            "Implication": item.implication,
        }
        for item in report.evidence_register
    ]
    if evidence_rows:
        st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No evidence register", "Evidence items have not been generated yet.")

    render_section_header("Assumption Register", "Open assumptions that require validation before high-stakes decisions.")
    render_assumption_table(report.assumption_register)


def render_analytics_plan(report) -> None:
    render_section_header(
        "Analytics Plan",
        "Hypotheses translated into analytical questions, metrics, data fields, and methods.",
    )
    if not report.analytics_plan or not report.analytics_plan.plan:
        render_empty_state("No analytics plan", "Analytics planner output has not been generated yet.")
        return
    st.caption(report.analytics_plan.summary)
    rows = [
        {
            "Hypothesis": item.hypothesis,
            "Analytical Question": item.analytical_question,
            "Metric Needed": item.business_metric_needed,
            "Data Fields": "; ".join(item.data_fields_needed),
            "Method": item.recommended_analysis_method,
            "Expected Output": item.expected_output,
            "Decision Relevance": item.decision_relevance,
            "Priority": item.priority.title(),
            "Limitations / Assumptions": item.limitations_or_assumptions,
        }
        for item in report.analytics_plan.plan
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_insight_synthesis_tab(report) -> None:
    render_section_header(
        "Insight Synthesis",
        "Consulting-grade insights synthesized from the business context, data profile, and saved predefined analyses.",
    )
    synthesis = report.insight_synthesis
    if not synthesis:
        render_empty_state("No insight synthesis", "Insight synthesis has not been generated yet.")
        return

    metric_cols = st.columns(2)
    with metric_cols[0]:
        render_metric_card("Confidence", synthesis.confidence_level.title())
        render_confidence_badge(synthesis.confidence_level.title())
    with metric_cols[1]:
        render_metric_card("Hypotheses Assessed", str(len(synthesis.hypothesis_support_status)))

    render_summary_card("Key Insights", synthesis.key_insights)

    st.markdown("### Observations")
    render_concise_bullets(synthesis.observations)

    st.markdown("### Supporting Evidence")
    render_concise_bullets(synthesis.supporting_evidence)

    st.markdown("### Business Implications")
    render_concise_bullets(synthesis.business_implications)

    st.markdown("### Recommended Actions")
    render_concise_bullets(synthesis.recommended_actions)

    st.markdown("### Hypothesis Support Status")
    status_rows = [
        {
            "Hypothesis": item.hypothesis,
            "Status": item.status.replace("_", " ").title(),
            "Rationale": item.rationale,
        }
        for item in synthesis.hypothesis_support_status
    ]
    if status_rows:
        st.dataframe(status_rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No hypothesis support assessment", "The synthesis did not include hypothesis support statuses.")

    with st.expander("Limitations"):
        render_concise_bullets(synthesis.limitations)


def render_strategic_options_tab(report) -> None:
    render_section_header("Strategic Options", "Alternative paths, tradeoffs, and management implications.")
    rows = [
        {
            "Option": item.option,
            "Description": item.description,
            "Upside": item.upside,
            "Downside": item.downside,
            "Expected Impact": item.expected_impact,
            "Investment": item.investment_required,
            "Confidence": item.confidence_level,
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
    render_section_header("Financials", "Directional financial logic, scenarios, and assumptions for validation.")
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
    st.markdown("### Sensitivities")
    render_concise_bullets(report.financial_assumptions.sensitivities)


def render_risks_tab(report) -> None:
    render_section_header("Risks", "Key risks, business impact, and mitigation plan.")
    if not report.executive_memo:
        st.info("Risks not generated yet.")
        return
    render_risk_table(report.executive_memo.risks_and_mitigations)
    st.markdown("### Data Gaps")
    render_concise_bullets(report.data_gaps, expander_label="More data gaps")


def render_execution_tab(report) -> None:
    render_section_header("Action Plan", "Next 30 / 60 / 90 day execution path.")
    render_action_plan(report.action_plan)
    render_section_header("Decision Roadmap", "Stage gates and validation milestones.")
    render_concise_bullets(report.decision_roadmap)


def render_stakeholder_lens_tab(report) -> None:
    render_section_header("Stakeholder Lens", "How key leaders are likely to evaluate the recommendation.")
    rows = [
        {"Stakeholder": stakeholder, "Likely Lens": "; ".join(items)}
        for stakeholder, items in report.stakeholder_lens.items()
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    render_section_header("Consulting Work Automated", "Repeatable consulting work accelerated by this workflow.")
    render_concise_bullets(report.consulting_work_automated)
    render_section_header("Human Judgment Still Needed", "Areas requiring consultant, operator, or executive review.")
    render_concise_bullets(report.human_judgment_needed)


def render_deck_outline_tab(report) -> None:
    render_section_header("Slide Storyline", "Suggested executive presentation storyline using Pyramid Principle.")
    if not report.deck_outline:
        st.info("Deck outline not generated yet.")
        return
    render_summary_card("Pyramid Principle Storyline", report.deck_outline.pyramid_principle_storyline)
    rows = [
        {
            "#": item.slide_number,
            "Slide": item.title,
            "Pyramid Role": item.pyramid_role,
            "Core Message": item.core_message,
            "Suggested Visual": item.suggested_visual,
            "Key Bullets": "; ".join(item.key_bullets),
        }
        for item in report.deck_outline.slides
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_critic_review_tab(report) -> None:
    render_section_header("Critic Review", "Partner-style quality notes plus user evaluation.")
    render_critic_review(report.critic)
    if report.critic and report.critic.red_team_challenges:
        render_section_header("Red Team Challenges", "Objections likely to come from a skeptical senior stakeholder.")
        render_concise_bullets(report.critic.red_team_challenges)
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
    render_section_header("Quality Score", "Score the generated first-pass output and maintain a lightweight review history.")
    st.caption("Score the AI-assisted output from 1 to 5. For hallucination risk, 1 means low risk and 5 means high risk.")

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
        "AI Consulting Operating System",
        "Accelerate first-pass strategy and analytics work with structured problem solving, recommendation drafting, executive deck generation, and partner-style critique.",
    )

    if not config.has_api_key:
        st.error(config.missing_api_key_message)

    render_uploaded_data_profile_preview()
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
                    data_profile=st.session_state.get("data_profile"),
                    analysis_results=st.session_state.get("analysis_results", []),
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


def render_uploaded_data_profile_preview() -> None:
    profile = st.session_state.get("data_profile")
    if not profile or st.session_state.get("report"):
        return
    with st.expander(f"Uploaded data profile: {profile.file_name}", expanded=False):
        render_data_profile(profile)
        render_analytics_workbench()


def _dict_table(values: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for name, details in values.items():
        row = {"Column": name}
        row.update(details)
        rows.append(row)
    return rows


def _analysis_availability_note(
    selected: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> str:
    if selected == "Data Exploration":
        return "Available for any uploaded dataframe. Produces column diagnostics, quality warnings, and next-step analysis guidance."
    if selected == "Segmentation Analysis":
        return f"Requires one segment/group column and one numeric metric column. Found {len(categorical_columns)} categorical and {len(numeric_columns)} numeric columns."
    return "Select an analysis mode."


def _format_list_for_display(values: object) -> str:
    if not values:
        return "None detected."
    if isinstance(values, list):
        return "; ".join(str(value) for value in values) if values else "None detected."
    return str(values)


def _format_top_values(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "Not provided."
    return "; ".join(
        f"{item.get('value')} ({item.get('frequency')}, {item.get('share_pct')}%)"
        for item in values
        if isinstance(item, dict)
    ) or "Not provided."


def _render_optional_dataframe(rows: object, empty_message: str) -> None:
    if isinstance(rows, list) and rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No data", empty_message)


if __name__ == "__main__":
    main()
