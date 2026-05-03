from __future__ import annotations

import streamlit as st

from core.config import AppConfig
from core.schemas import BusinessProblemInput
from core.workflow import WORKFLOW_STEPS, run_consulting_workflow
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


def render_input_form() -> BusinessProblemInput | None:
    with st.form("business_problem_form"):
        st.subheader("Business Input")
        problem = st.text_area(
            "Business problem",
            placeholder="Example: Should we launch a premium subscription tier for SMB customers?",
            height=120,
        )

        col1, col2 = st.columns(2)
        with col1:
            geography = st.text_input("Geography", placeholder="Example: United States")
            budget = st.text_input("Budget", placeholder="Example: $500k launch budget")
            target_customers = st.text_area(
                "Target customers",
                placeholder="Example: B2B SaaS companies with 20-250 employees",
                height=100,
            )
        with col2:
            constraints = st.text_area(
                "Constraints",
                placeholder="Example: Must launch in 90 days; no new engineering hires",
                height=100,
            )
            expected_output = st.text_area(
                "Expected output",
                placeholder="Example: A go/no-go recommendation with financial assumptions",
                height=100,
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

    tabs = st.tabs([TAB_LABELS.get(output.key, output.title) for output in outputs])
    for tab, output in zip(tabs, outputs):
        with tab:
            st.markdown(output.content)
            st.download_button(
                f"Download {TAB_LABELS.get(output.key, output.title)}",
                data=output.to_markdown(),
                file_name=safe_filename(f"{output.title}.md"),
                mime="text/markdown",
                key=f"download_{output.key}",
            )


def main() -> None:
    initialize_state()
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
            st.session_state.error = str(exc)
            st.error("The model response could not be parsed as the expected JSON schema.")
            st.code(exc.raw_output or "<empty output>", language="json")
        except Exception as exc:
            st.session_state.error = str(exc)
            st.error(f"Analysis failed: {exc}")

    render_outputs()


if __name__ == "__main__":
    main()
