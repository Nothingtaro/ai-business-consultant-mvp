from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from core.config import AppConfig
from core.schemas import BusinessProblemInput
from core.workflow import WORKFLOW_STEPS, run_consulting_workflow
from utils.app_logging import get_app_logger
from utils.json_parser import JsonParsingError
from utils.markdown_exporter import build_markdown_report, safe_filename


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


def render_sidebar(config: AppConfig) -> None:
    with st.sidebar:
        st.header("Workflow")
        st.caption("The agent runs a structured strategy-consulting analysis from problem definition to critique.")
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
        st.divider()
        st.header("Settings")
        st.text_input("Model", value=config.model, key="model_name")
        st.caption("Set `OPENAI_MODEL` in `.env` to change the default.")


def render_sample_case_selector() -> None:
    sample_cases = load_sample_cases()
    if not sample_cases:
        return

    options = ["Start from a blank case", *[case["name"] for case in sample_cases]]
    selected = st.selectbox(
        "Sample case",
        options,
        key="selected_sample_case",
        help="Choose a sample to auto-fill the business input form.",
    )

    selected_case = next((case for case in sample_cases if case["name"] == selected), None)
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Use sample case", disabled=selected_case is None, use_container_width=True):
            apply_sample_case(selected_case)
            st.rerun()
    with col2:
        if st.button("Clear form", use_container_width=True):
            clear_input_form()
            st.rerun()


def render_input_form() -> BusinessProblemInput | None:
    render_sample_case_selector()

    with st.form("business_problem_form"):
        st.subheader("Business Input")
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
    st.subheader("Consulting Outputs")

    st.download_button(
        "Download Full Markdown Report",
        data=build_markdown_report(report),
        file_name=safe_filename("consulting_report.md"),
        mime="text/markdown",
        use_container_width=True,
    )

    tabs = st.tabs([*[TAB_LABELS.get(output.key, output.title) for output in outputs], "Evaluation"])
    output_tabs = tabs[:-1]
    evaluation_tab = tabs[-1]

    for tab, output in zip(output_tabs, outputs):
        with tab:
            st.markdown(output.content)
            st.download_button(
                f"Download {TAB_LABELS.get(output.key, output.title)}",
                data=output.to_markdown(),
                file_name=safe_filename(f"{output.title}.md"),
                mime="text/markdown",
                key=f"download_{output.key}",
            )

    with evaluation_tab:
        render_evaluation_tab(report.business_input)


def render_evaluation_tab(business_input: BusinessProblemInput) -> None:
    st.subheader("Evaluation")
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
    st.subheader("Historical Evaluations")
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
    logger = get_app_logger()
    config = AppConfig.from_env()
    render_sidebar(config)

    st.title("AI Business Consulting Agent")
    st.caption("Turn a business question into a structured recommendation, memo, deck outline, and critique.")

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
