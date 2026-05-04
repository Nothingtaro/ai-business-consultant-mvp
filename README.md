# AI Consulting Operating System

<img width="1999" height="1091" alt="AI Consulting Operating System screenshot" src="https://github.com/user-attachments/assets/16e0ed8e-0f2b-4c5f-b778-0c1a64c86f99" />

An AI-powered consulting operating system designed to reduce the cost and cycle time of first-pass strategy and analytics work.

The app behaves like a top-tier strategy consulting analyst with strong data analytics orientation. It helps teams frame a decision, build a MECE-style issue tree, generate hypotheses, define an analytics plan, create practical financial assumptions, synthesize insights, compare strategic options, draft an executive recommendation, outline a PowerPoint deck, and critique the final output.

## Project Overview

This project demonstrates how agent-style workflows can accelerate repeatable strategy consulting work. Instead of producing a single generic answer, the application decomposes the work into specialized steps and passes context forward through the workflow.

The goal is not to replace human consultants or executive judgment. The system reduces dependency, cost, and turnaround time for first-pass work so business leaders and consultants can spend more time challenging assumptions, validating data, and making decisions.

The final output is designed for management review: structured sections, explicit assumptions, directional financial logic, strategic option comparison, partner-style critique, and downloadable Markdown and PowerPoint deliverables.

## Product Vision

The long-term vision is a consulting operating system that automates and accelerates common advisory workstreams:

- Problem framing
- Issue tree generation
- Hypothesis generation
- Analytics planning
- Data profiling
- Predefined analysis
- Insight synthesis
- Strategic option comparison
- Recommendation drafting
- Executive memo generation
- PowerPoint deck generation
- Partner-style critique

The current MVP focuses on the structured strategy workflow, executive memo, exportable report, deck generation, and quality review foundation.

## Problem Statement

Business teams often start with broad questions such as:

- Should we launch this product?
- Should we enter this market?
- How can we improve revenue from this funnel?
- Which customer segment should we prioritize?

These questions usually need structure, analytical framing, and executive synthesis before they can become decision-ready. This app addresses that gap by turning raw business context into a first-pass consulting work product for human review.

## Key Features

- Streamlit interface for entering business context or selecting sample cases
- Sequential consulting workflow with one agent per analysis step
- OpenAI Responses API integration
- Prompt templates stored as editable markdown files
- Pydantic schemas for structured JSON outputs
- JSON parsing with user-friendly Streamlit errors
- Local logging for workflow step status and failed LLM outputs
- Optional CSV/XLSX upload with in-memory pandas profiling
- Practical financial assumption model with scenario calculations
- Strategic option comparison and recommendation drafting
- Hypothesis-to-analytics planner with metrics, data fields, methods, and priorities
- Data request list, evidence register, KPI / driver tree, and assumption register
- Decision roadmap and stakeholder lens for CEO, CFO, COO, and Data Team review
- Partner-style critic review
- Evaluation tab for user scoring and reviewer notes
- Local JSON history for evaluations
- Markdown export with timestamped filenames
- PowerPoint export with a 16:9 executive-style strategy deck
- Environment-based configuration with no hardcoded API keys

## Architecture Diagram

```text
User
  |
  v
Streamlit UI (app.py)
  |
  |-- sample case selector
  |-- optional dataset uploader
  |-- business input form
  |-- output tabs
  |-- evaluation tab
  |
  v
Workflow Orchestrator (core/workflow.py)
  |
  +--> Problem Framer Agent
  +--> Issue Tree Builder Agent
  +--> Hypothesis Generator Agent
  +--> Analytics Planner Agent
  +--> Analysis Planner Agent
  +--> Financial Analyst Agent
  +--> Memo Writer Agent
  +--> Deck Outline Writer Agent
  +--> Critic Agent
  |
  v
Structured Schemas (core/schemas.py)
  |
  +--> JSON parser and validation
  +--> Markdown report exporter
  +--> Local evaluation history
  +--> Local workflow logs
```

## Folder Structure

```text
ai-business-consultant-mvp/
  app.py
  requirements.txt
  .env.example
  README.md
  LICENSE

  agents/
    problem_framer.py
    issue_tree_builder.py
    hypothesis_generator.py
    analytics_planner.py
    analysis_planner.py
    financial_analyst.py
    memo_writer.py
    deck_outline_writer.py
    critic.py

  core/
    config.py
    schemas.py
    workflow.py

  utils/
    app_logging.py
    json_parser.py
    llm_client.py
    markdown_exporter.py
    prompt_loader.py

  tools/
    data_profiler.py

  prompts/
    system.md
    problem_framing.md
    issue_tree.md
    hypotheses.md
    analytics_planner.md
    analysis_plan.md
    financial_assumptions.md
    executive_memo.md
    deck_outline.md
    critic.md

  examples/
    sample_cases.json
```

Local runtime folders such as `logs/` and `eval_outputs/` are created automatically and ignored by Git.

## Setup Instructions

1. Create a virtual environment.

```bash
python -m venv .venv
```

2. Activate the virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create a local `.env` file.

Windows:

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

5. Add your OpenAI API key.

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.2
```

Environment variables:

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | OpenAI API key used for model calls. |
| `OPENAI_MODEL` | No | Model used for generation. Defaults to `gpt-5.2`. |
| `PROMPTS_DIR` | No | Prompt directory path. Defaults to `prompts`. |

Do not commit `.env`. It is intentionally ignored.

## How To Run The App

Start Streamlit:

```bash
streamlit run app.py
```

Open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

To verify imports and syntax:

```bash
python -m compileall app.py agents core utils
```

## Deployment Notes

### Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app from the repository.
3. Set the app entry point to:

```text
app.py
```

4. Add secrets in the Streamlit Cloud settings:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_MODEL = "gpt-5.2"
```

5. Deploy the app. Streamlit will install dependencies from `requirements.txt`.

Notes:

- `runtime.txt` requests Python 3.11.
- The app reads `OPENAI_API_KEY`, `OPENAI_MODEL`, and `PROMPTS_DIR` from Streamlit secrets when environment variables are not set.
- Local runtime folders such as `logs/` and `eval_outputs/` are ephemeral in hosted environments.
- Do not upload `.env`; use platform secrets instead.

### Render

1. Create a new Web Service connected to the GitHub repository.
2. Use Python 3.11.
3. Set the build command:

```bash
pip install -r requirements.txt
```

4. Set the start command:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

5. Add environment variables in Render:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.2
```

## Startup Validation

The app runs lightweight startup checks and shows the result in the sidebar under `Health`.

Checks include:

- Required prompt files exist.
- Sample cases are valid JSON with required fields.
- Local runtime folders for logs and evaluations are writable.
- OpenAI API key configuration is visible as a non-secret status check.

The health check does not print API keys or sensitive environment variables.

## How To Use Sample Cases

Sample cases are stored in:

```text
examples/sample_cases.json
```

In the Streamlit app:

1. Open the sample case dropdown.
2. Select a case.
3. Click `Use sample case`.
4. Review or edit the auto-filled fields.
5. Click `Run analysis`.

Included examples cover matcha delivery, insurance app funnel growth, AI telesales quality control, car insurance renewal segmentation, and SME analytics services.

## Optional Dataset Upload

Users can upload a CSV or XLSX file from the Streamlit sidebar. The dataframe is stored only in `st.session_state`; there is no database or file persistence.

The app profiles the dataset before analysis and sends only metadata and summarized statistics into the workflow, not the full raw dataset. The profile includes shape, columns, inferred types, missing values, duplicate rows, numeric and categorical summaries, detected date columns, sample rows for UI review, data quality notes, and possible analysis suggestions.

If no dataset is uploaded, the app continues to run in text-only consulting mode.

## Analytics Workbench

After a dataset is uploaded and profiled, users can run safe predefined pandas analyses from the Analytics Workbench:

- **Data Exploration**: dataset overview, column profiling, data quality scoring, numeric/categorical/date profiles, business readiness signals, and an executive summary of what analysis is possible next.
- **Segmentation Analysis**: comparison of one numeric or binary metric across one segment dimension, with optional weighting, minimum segment-size controls, attractiveness scoring, top/bottom segment views, interpretation labels, and recommended actions.

The app does not allow arbitrary Python code generated by the LLM. Analyses run only through fixed template functions in `tools/analysis_tools.py`, with required column validation and graceful warnings for weak or invalid inputs.

Saved analysis results are stored in `st.session_state` for the current session. Later phases can use these structured summaries for insight synthesis and presentation support without exposing the full raw dataset to the LLM.

Other analysis templates are intentionally out of scope for the current MVP. The focus is to make exploration and segmentation strong enough for first-pass consulting insight synthesis before adding more analytical modes.

## How The Consulting Workflow Works

The workflow runs sequentially. Each step receives the original business input and all prior step outputs.

1. **Problem Framing** creates a decision question, SCQ framing, success criteria, and key unknowns.
2. **Issue Tree** structures the problem into MECE branches and high-leverage questions.
3. **Hypotheses** proposes testable hypotheses, a hypothesis tree, evidence needs, and decision impact.
4. **Analytics Planner** translates hypotheses into analytical questions, metrics, data fields, methods, expected outputs, decision relevance, priorities, and limitations.
5. **Analysis Plan** defines broader consulting workstreams, data requests, evidence register, methods, owners, and timing.
6. **Financial Assumptions** creates KPI / driver logic, assumption tables, scenario inputs, gross margin logic, and break-even calculations.
7. **Executive Memo** drafts the recommendation, rationale, strategic options, expected impact, stakeholder lens, decision roadmap, risks, mitigations, and next steps.
8. **Deck Outline** turns the recommendation into a Pyramid Principle executive presentation structure.
9. **Critic Review** evaluates the work across clarity, MECE quality, hypothesis strength, practicality, financial logic, missing assumptions, hallucination risk, executive readiness, and red-team objections.

The final Markdown export is a first-pass strategy and analytics work product. It includes:

- Executive Summary
- Decision Question
- SCQ: Situation / Complication / Question
- Success Criteria
- Issue Tree
- Hypothesis Tree
- Analytics Plan
- KPI / Driver Tree
- Data Request List
- Evidence Register
- Assumption Register
- Strategic Options Matrix
- Recommendation With Rationale
- Expected Impact
- Scenario / Sensitivity Analysis
- Risk Register With Mitigation
- 30 / 60 / 90-Day Execution Plan
- Decision Roadmap
- Stakeholder Lens: CEO / CFO / COO / Data Team
- Partner Review / Red Team Critique
- Slide Storyline Using Pyramid Principle
- Consulting Work Automated
- Human Consultant / Executive Judgment Still Needed

The app also exports a concise PowerPoint version with title, executive summary, decision context, issue tree, hypotheses, analytics plan, strategic options, recommendation, financial assumptions, risks, 30/60/90 actions, deck storyline, and critic review slides.

## Evaluation Approach

The app includes a lightweight Evaluation tab after a report is generated.

Users can score the output from 1 to 5 on:

- Clarity
- MECE structure
- Practicality
- Data-backed reasoning
- Executive readiness
- Hallucination risk

Reviewer notes are saved locally to:

```text
eval_outputs/evaluations.json
```

The app also displays a simple historical evaluation table. This creates a practical feedback loop for comparing first-pass output quality across prompts, models, and sample cases.

## Current Limitations

- Outputs are AI-generated and require human review before business use.
- Financial assumptions are directional and should not replace a validated financial model.
- The app does not browse the web or verify market data.
- Data profiling and predefined analysis are part of the broader vision and are not yet implemented as separate workflow modules.
- Evaluation history and logs are local-only.
- There is no database, authentication, or multi-user project history.
- The full workflow requires a valid OpenAI API key.
- Automated tests are not yet included.

## Future Roadmap

- Add unit tests for schemas, prompt rendering, JSON parsing, financial calculations, and markdown export.
- Add a mock LLM mode for demos and CI.
- Add saved project history with named consulting cases.
- Add richer financial model outputs and sensitivity analysis.
- Add data profiling and predefined analysis modules.
- Add optional web research or document upload support.
- Improve Streamlit rendering of structured outputs into cleaner tables and sections.
- Add deployment configuration for hosted demos.

## Disclaimer

This project is an MVP for AI-assisted strategy and analytics work. It is intended to reduce cost and turnaround time for first-pass consulting deliverables, not to fully replace human consultants, expert validation, or executive judgment. It is not legal, financial, or professional consulting advice.
