# AI Business Consulting Agent

<img width="1999" height="1091" alt="AI Business Consulting Agent screenshot" src="https://github.com/user-attachments/assets/16e0ed8e-0f2b-4c5f-b778-0c1a64c86f99" />

A Streamlit application that turns an ambiguous business question into a structured consulting work product using a multi-step OpenAI-powered workflow.

The app helps users frame a decision, build a MECE issue tree, generate hypotheses, define an analysis plan, create practical financial assumptions, draft an executive recommendation, outline a pitch deck, and critique the final output.

## Project Overview

This project demonstrates how agent-style workflows can support strategy consulting tasks. Instead of producing a single generic answer, the application decomposes the work into specialized steps and passes context forward through the workflow.

The final output is designed for management review: structured sections, explicit assumptions, directional financial logic, critic feedback, and a downloadable markdown report.

## Problem Statement

Business teams often start with broad questions such as:

- Should we launch this product?
- Should we enter this market?
- How can we improve revenue from this funnel?
- Which customer segment should we prioritize?

These questions usually need structure before they can become decision-ready. This app addresses that gap by turning raw business context into a consulting-style decision package.

## Key Features

- Streamlit interface for entering business context or selecting sample cases
- Sequential consulting workflow with one agent per analysis step
- OpenAI Responses API integration
- Prompt templates stored as editable markdown files
- Pydantic schemas for structured JSON outputs
- JSON parsing with user-friendly Streamlit errors
- Local logging for workflow step status and failed LLM outputs
- Practical financial assumption model with scenario calculations
- Senior-manager-style critic review
- Evaluation tab for user scoring and reviewer notes
- Local JSON history for evaluations
- Markdown export with timestamped filenames
- PowerPoint export with a simple 16:9 consulting-style deck
- Environment-based configuration with no hardcoded API keys

## Architecture Diagram

```text
User
  |
  v
Streamlit UI (app.py)
  |
  |-- sample case selector
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

  prompts/
    system.md
    problem_framing.md
    issue_tree.md
    hypotheses.md
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

## How The Consulting Workflow Works

The workflow runs sequentially. Each step receives the original business input and all prior step outputs.

1. **Problem Framing** creates a decision question, context summary, success criteria, and key unknowns.
2. **Issue Tree** structures the problem into MECE branches and high-leverage questions.
3. **Hypotheses** proposes testable hypotheses with evidence needs and decision impact.
4. **Analysis Plan** defines workstreams, data needs, methods, owners, and timing.
5. **Financial Assumptions** creates assumption tables, scenario inputs, gross margin logic, and break-even calculations.
6. **Executive Memo** drafts the recommendation, rationale, risks, mitigations, and next steps.
7. **Deck Outline** turns the recommendation into a 10-slide executive presentation structure.
8. **Critic Review** evaluates the work across clarity, MECE quality, hypothesis strength, practicality, financial logic, missing assumptions, hallucination risk, and executive readiness.

The final markdown export includes:

- Executive Summary
- Decision Question
- Situation / Context
- Key Business Objective
- Issue Tree
- Key Hypotheses
- Analysis Plan
- Market / Customer / Competitor Considerations
- Strategic Options
- Recommendation
- Financial Assumptions
- Scenario Analysis
- Key Risks
- Mitigation Plan
- Assumption Register
- Data Gaps
- Next 30 / 60 / 90 Day Action Plan
- 10-Slide Pitch Deck Outline
- Critic Review

The app also exports a concise PowerPoint version with title, executive summary, decision context, issue tree, hypotheses, strategic options, recommendation, financial assumptions, risks, 30/60/90 actions, pitch deck outline, and critic review slides.

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

The app also displays a simple historical evaluation table. This creates a practical feedback loop for comparing output quality across prompts, models, and sample cases.

## Current Limitations

- Outputs are AI-generated and require human review before business use.
- Financial assumptions are directional and should not replace a validated financial model.
- The app does not browse the web or verify market data.
- Evaluation history and logs are local-only.
- There is no database, authentication, or multi-user project history.
- The full workflow requires a valid OpenAI API key.
- Automated tests are not yet included.

## Future Roadmap

- Add unit tests for schemas, prompt rendering, JSON parsing, financial calculations, and markdown export.
- Add a mock LLM mode for demos and CI.
- Add saved project history with named consulting cases.
- Add richer financial model outputs and sensitivity analysis.
- Add optional web research or document upload support.
- Add PPTX export for the deck outline.
- Improve Streamlit rendering of structured outputs into cleaner tables and sections.
- Add deployment configuration for hosted demos.

## Disclaimer

This project is an MVP for strategy-analysis assistance. It is not legal, financial, or professional consulting advice.
