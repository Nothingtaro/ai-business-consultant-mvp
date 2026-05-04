from __future__ import annotations

import html

import streamlit as st

from utils.markdown_exporter import build_markdown_report, safe_filename
from utils.pptx_exporter import PPTX_MIME_TYPE, build_pptx_report


def apply_design_system() -> None:
    st.markdown(
        """
        <style>
        :root {
          --war-room-bg: #f6f8fb;
          --war-room-surface: #ffffff;
          --war-room-text: #1f3144;
          --war-room-muted: #5a6069;
          --war-room-border: #d8dee8;
          --war-room-accent: #3465a4;
          --war-room-soft-blue: #e8eff7;
          --war-room-success: #1f7a4d;
          --war-room-warning: #b7791f;
          --war-room-danger: #b42318;
        }

        .block-container {
          max-width: 1280px;
          padding-top: 2rem;
          padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
          border-right: 1px solid var(--war-room-border);
        }

        h1, h2, h3 {
          letter-spacing: 0;
          color: var(--war-room-text);
        }

        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
          border-radius: 8px;
        }

        .stButton > button,
        .stDownloadButton > button {
          border-radius: 6px;
          border: 1px solid var(--war-room-border);
          font-weight: 600;
        }

        .stButton > button[kind="primary"] {
          border-color: var(--war-room-accent);
          background: var(--war-room-accent);
        }

        .war-room-hero {
          border: 1px solid var(--war-room-border);
          background: var(--war-room-surface);
          border-radius: 8px;
          padding: 22px 24px;
          margin-bottom: 18px;
        }

        .war-room-eyebrow {
          color: var(--war-room-accent);
          font-size: 0.76rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          margin-bottom: 6px;
        }

        .war-room-title {
          color: var(--war-room-text);
          font-size: 2rem;
          line-height: 1.15;
          font-weight: 750;
          margin-bottom: 6px;
        }

        .war-room-subtitle {
          color: var(--war-room-muted);
          font-size: 0.98rem;
          line-height: 1.5;
          max-width: 780px;
        }

        .war-room-section {
          margin-top: 20px;
          margin-bottom: 10px;
        }

        .war-room-section-title {
          color: var(--war-room-text);
          font-size: 1.18rem;
          font-weight: 700;
          margin-bottom: 2px;
        }

        .war-room-section-caption {
          color: var(--war-room-muted);
          font-size: 0.9rem;
          line-height: 1.45;
        }

        .war-room-card {
          border: 1px solid var(--war-room-border);
          background: var(--war-room-surface);
          border-radius: 8px;
          padding: 16px 18px;
          min-height: 96px;
          margin-bottom: 12px;
        }

        .war-room-card-title {
          color: var(--war-room-muted);
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        .war-room-card-value {
          color: var(--war-room-text);
          font-size: 1.12rem;
          font-weight: 700;
          line-height: 1.3;
        }

        .war-room-card-caption {
          color: var(--war-room-muted);
          font-size: 0.82rem;
          margin-top: 6px;
          line-height: 1.35;
        }

        .war-room-summary-card {
          border: 1px solid rgba(52, 101, 164, 0.28);
          background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
          border-radius: 8px;
          padding: 20px 22px;
          margin: 12px 0 16px 0;
        }

        .war-room-summary-title {
          color: var(--war-room-text);
          font-size: 1.05rem;
          font-weight: 750;
          margin-bottom: 8px;
        }

        .war-room-decision-callout {
          border-left: 4px solid var(--war-room-accent);
          background: var(--war-room-soft-blue);
          border-radius: 8px;
          padding: 16px 18px;
          margin: 12px 0 18px 0;
        }

        .war-room-decision-label {
          color: var(--war-room-accent);
          font-size: 0.76rem;
          font-weight: 800;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-bottom: 6px;
        }

        .war-room-decision-text {
          color: var(--war-room-text);
          font-size: 1.08rem;
          font-weight: 700;
          line-height: 1.42;
        }

        .war-room-branch-title {
          color: var(--war-room-text);
          font-size: 1rem;
          font-weight: 750;
          margin-bottom: 8px;
        }

        .war-room-badge {
          display: inline-flex;
          align-items: center;
          border: 1px solid var(--war-room-border);
          border-radius: 999px;
          padding: 3px 10px;
          color: var(--war-room-text);
          background: var(--war-room-soft-blue);
          font-size: 0.76rem;
          font-weight: 700;
          margin-right: 6px;
          margin-bottom: 6px;
        }

        .war-room-badge.success {
          color: var(--war-room-success);
          background: rgba(31, 122, 77, 0.1);
          border-color: rgba(31, 122, 77, 0.24);
        }

        .war-room-badge.warning {
          color: var(--war-room-warning);
          background: rgba(183, 121, 31, 0.1);
          border-color: rgba(183, 121, 31, 0.24);
        }

        @media (max-width: 760px) {
          .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
          }

          .war-room-title {
            font-size: 1.55rem;
          }

          .war-room-hero {
            padding: 18px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, eyebrow: str = "AI Consulting War Room") -> None:
    st.markdown(
        f"""
        <div class="war-room-hero">
          <div class="war-room-eyebrow">{_escape(eyebrow)}</div>
          <div class="war-room-title">{_escape(title)}</div>
          <div class="war-room-subtitle">{_escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str | None = None) -> None:
    caption_html = f'<div class="war-room-section-caption">{_escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="war-room-section">
          <div class="war-room-section-title">{_escape(title)}</div>
          {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, subtitle: str | None = None) -> None:
    caption_html = f'<div class="war-room-card-caption">{_escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="war-room-card">
          <div class="war-room-card-title">{_escape(title)}</div>
          <div class="war-room-card-value">{_escape(value)}</div>
          {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(label: str, status: str) -> None:
    status_class = f" {status}" if status else ""
    st.markdown(
        f'<span class="war-room-badge{status_class}">{_escape(label)}</span>',
        unsafe_allow_html=True,
    )


def render_badge(label: str, status: str = "") -> None:
    render_status_badge(label, status)


def render_confidence_badge(confidence_level: str) -> None:
    normalized = confidence_level.strip().lower()
    if normalized in {"high", "ready"}:
        status = "success"
    elif normalized in {"medium", "pending"}:
        status = "warning"
    else:
        status = "danger"
    render_status_badge(confidence_level, status)


def render_option_card(option) -> None:
    st.markdown(
        f"""
        <div class="war-room-card">
          <div class="war-room-card-title">{_escape(getattr(option, "option", "Strategic Option"))}</div>
          <div class="war-room-card-value">{_escape(getattr(option, "description", ""))}</div>
          <div class="war-room-card-caption"><strong>Upside:</strong> {_escape(getattr(option, "upside", ""))}</div>
          <div class="war-room-card-caption"><strong>Downside:</strong> {_escape(getattr(option, "downside", ""))}</div>
          <div class="war-room-card-caption"><strong>Decision implication:</strong> {_escape(getattr(option, "decision_implication", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_table(risks) -> None:
    rows = [
        {
            "Risk": risk.risk,
            "Why It Matters": risk.why_it_matters,
            "Mitigation": risk.mitigation,
        }
        for risk in risks
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No risks available", "Risk and mitigation details have not been generated yet.")


def render_assumption_table(assumptions) -> None:
    rows = []
    for item in assumptions:
        if hasattr(item, "low_case"):
            rows.append(
                {
                    "Assumption": item.assumption,
                    "Low": item.low_case,
                    "Base": item.base_case_value,
                    "High": item.high_case,
                    "Validation Source": item.validation_source,
                }
            )
        else:
            rows.append(
                {
                    "Assumption": item.assumption,
                    "Source": item.source,
                    "Importance": item.importance,
                    "Validation Needed": item.validation_needed,
                    "Status": getattr(item, "status", "Assumption - no uploaded data provided."),
                }
            )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No assumptions available", "Assumption details have not been generated yet.")


def render_action_plan(action_plan) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        render_section_header("Next 30 Days")
        _render_bullets(action_plan.next_30_days)
    with col2:
        render_section_header("Next 60 Days")
        _render_bullets(action_plan.next_60_days)
    with col3:
        render_section_header("Next 90 Days")
        _render_bullets(action_plan.next_90_days)


def render_empty_state(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="war-room-card">
          <div class="war-room-card-title">{_escape(title)}</div>
          <div class="war-room-card-caption">{_escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_export_center(report) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Markdown report",
            data=build_markdown_report(report),
            file_name=safe_filename("consulting_report.md"),
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "PowerPoint report",
            data=build_pptx_report(report),
            file_name=safe_filename("consulting_report.pptx"),
            mime=PPTX_MIME_TYPE,
            use_container_width=True,
        )


def render_summary_card(title: str, bullets: list[str], max_visible: int = 5) -> None:
    visible = bullets[:max_visible] or ["Not provided."]
    list_items = "".join(f"<li>{_escape(item)}</li>" for item in visible)
    st.markdown(
        f"""
        <div class="war-room-summary-card">
          <div class="war-room-summary-title">{_escape(title)}</div>
          <ul>{list_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    hidden = bullets[max_visible:]
    if hidden:
        with st.expander(f"Show {len(hidden)} more summary points"):
            _render_bullets(hidden)


def render_decision_callout(decision_question: str) -> None:
    st.markdown(
        f"""
        <div class="war-room-decision-callout">
          <div class="war-room-decision-label">Decision Question</div>
          <div class="war-room-decision-text">{_escape(decision_question or "Not provided.")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_issue_tree_cards(issue_tree) -> None:
    if not issue_tree or not issue_tree.branches:
        render_empty_state("No issue tree available", "Issue tree details have not been generated yet.")
        return

    for branch in issue_tree.branches:
        with st.container():
            st.markdown(
                f"""
                <div class="war-room-card">
                  <div class="war-room-branch-title">{_escape(branch.name)}</div>
                  <div class="war-room-card-caption"><strong>Key questions:</strong> {_escape(_join(branch.questions[:3]))}</div>
                  <div class="war-room-card-caption"><strong>Sub-branches:</strong> {_escape(_join(branch.sub_branches[:4]))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            hidden_questions = branch.questions[3:]
            hidden_subbranches = branch.sub_branches[4:]
            if hidden_questions or hidden_subbranches:
                with st.expander(f"More detail: {branch.name}"):
                    if hidden_questions:
                        st.markdown("**Additional questions**")
                        _render_bullets(hidden_questions)
                    if hidden_subbranches:
                        st.markdown("**Additional sub-branches**")
                        _render_bullets(hidden_subbranches)


def render_concise_bullets(items: list[str], max_visible: int = 5, expander_label: str = "Show more") -> None:
    _render_bullets(items[:max_visible])
    hidden = items[max_visible:]
    if hidden:
        with st.expander(f"{expander_label} ({len(hidden)})"):
            _render_bullets(hidden)


def render_critic_review(critic) -> None:
    if not critic:
        render_empty_state("No critic review", "Critic review details have not been generated yet.")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        render_metric_card("Overall Score", f"{critic.overall_score}/5")
        render_confidence_badge("High" if critic.overall_score >= 4 else "Medium" if critic.overall_score == 3 else "Low")
    with col2:
        render_section_header("Final Verdict")
        st.write(critic.final_verdict)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        render_section_header("Strengths")
        render_concise_bullets(critic.strengths, max_visible=4, expander_label="More strengths")
    with col_b:
        render_section_header("Weaknesses")
        render_concise_bullets(critic.weaknesses, max_visible=4, expander_label="More weaknesses")
    with col_c:
        render_section_header("Critical Gaps")
        render_concise_bullets(critic.critical_gaps, max_visible=4, expander_label="More gaps")

    with st.expander("Recommended improvements"):
        render_concise_bullets(critic.recommended_improvements, max_visible=8)


def _render_bullets(items: list[str]) -> None:
    if not items:
        st.write("Not provided.")
        return
    for item in items:
        st.markdown(f"- {item}")


def _escape(value: str | None) -> str:
    return html.escape(str(value or ""))


def _join(items: list[str]) -> str:
    return "; ".join(items) if items else "Not provided."
