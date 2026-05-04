# AI Business Consulting Agent

<img width="1999" height="1091" alt="image" src="https://github.com/user-attachments/assets/16e0ed8e-0f2b-4c5f-b778-0c1a64c86f99" />

A Python + Streamlit application that turns an ambiguous business problem into a structured strategy consulting work product using the OpenAI API.

The app guides a user from raw business context to a decision question, MECE issue tree, hypotheses, analysis plan, financial assumptions, executive memo, pitch deck outline, and critic review.

## Short Description

An AI-powered strategy consulting assistant for structuring business decisions and generating executive-ready markdown reports.

## Problem Statement

Business teams often start with broad questions such as "Should we enter this market?" or "Should we launch this product?" These questions need structure before they can become useful decisions.

This project demonstrates how an AI agent workflow can apply strategy consulting patterns to help users clarify the decision, organize analysis, surface assumptions, and produce executive-ready outputs.

## Key Features

- Streamlit UI for structured business inputs
- Modular agent architecture with one responsibility per consulting step
- OpenAI Responses API integration
- Prompt templates stored as markdown files in `prompts/`
- Pydantic schemas for structured JSON outputs
- Robust JSON parsing with helpful error messages
- Sequential workflow that passes context between steps
- Markdown export for the final consulting report
- Lightweight evaluation tab with local JSON history
- Local workflow logging with saved raw outputs for JSON parsing failures
- `.env` based configuration with no hardcoded API keys

## Demo Workflow

1. Enter a business problem, budget, geography, target customers, constraints, and expected output.
2. Run the consulting workflow.
3. Review outputs in separate tabs:
   - Problem Framing
   - Issue Tree
   - Hypotheses
   - Analysis Plan
   - Financial Assumptions
   - Executive Memo
   - Deck Outline
   - Critic Review
4. Use the Evaluation tab to score output quality and save reviewer notes locally.
5. Download the final markdown report.

## Architecture Overview

The application uses a simple sequential agent workflow:

- `app.py` handles the Streamlit interface.
- `core/workflow.py` orchestrates the consulting steps.
- `agents/` contains one module per consulting task.
- `prompts/` contains all LLM prompt templates.
- `core/schemas.py` defines structured Pydantic output models.
- `utils/llm_client.py` centralizes OpenAI API calls and retry handling.
- `utils/json_parser.py` validates LLM JSON responses.
- `utils/markdown_exporter.py` converts the final report into markdown.

Each step receives the original business input plus prior step outputs, so later steps can build on earlier analysis.

## Folder Structure

```text
ai_business_consultant/
  app.py
  requirements.txt
  .env.example
  .gitignore
  LICENSE
  README.md

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
    llm_client.py
    prompt_loader.py
    json_parser.py
    markdown_exporter.py

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

4. Create your own `.env` file from `.env.example`.

Windows:

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

5. Add your own OpenAI API key to `.env`.

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.2
```

Do not commit your `.env` file. It is intentionally ignored by `.gitignore`.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Your OpenAI API key. Create this locally in `.env`. |
| `OPENAI_MODEL` | No | Model used for generation. Defaults to `gpt-5.2`. |
| `PROMPTS_DIR` | No | Prompt directory path. Defaults to `prompts`. |

## Run The Streamlit App

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal, usually:

```text
http://localhost:8501
```

## How To Use Sample Cases

Sample business cases are available in:

```text
examples/sample_cases.json
```

Use the sample case selector in the Streamlit app to auto-fill the input form, or open the JSON file directly for tests and demos.

## Example Output Sections

The final markdown export includes:

- Executive Summary
- Decision Question
- Business Context
- Issue Tree
- Key Hypotheses
- Analysis Plan
- Financial Assumptions
- Recommendation
- Risks
- Next Steps
- 10-Slide Pitch Deck Outline
- Critic Review

## Known Limitations

- Outputs are AI-generated and should be reviewed before business use.
- Financial assumptions are directional and not a substitute for a validated financial model.
- The app does not currently browse the web or verify market data.
- There is no persistent project history or database.
- Logs and evaluation history are local-only and not intended for multi-user deployments.
- There is no offline/mock mode for running the full workflow without an API key.
- Automated tests are not yet included.

## Future Roadmap

- Add unit tests for schemas, JSON parsing, prompt rendering, and markdown export.
- Add a mock LLM mode for demos and CI checks.
- Add saved project history and report management.
- Add richer financial model calculations.
- Add optional web research or document upload support.
- Add PPTX export for the deck outline.
- Improve UI rendering of structured JSON into tables and formatted sections.

## How To Verify The App Works

1. Run a basic syntax and import check.

```bash
python -m compileall app.py agents core utils
```

2. Start the Streamlit app.

```bash
streamlit run app.py
```

3. Open the local URL shown in the terminal and confirm the input form loads.

4. Add your own API key in `.env`, run a sample case from `examples/sample_cases.json`, and confirm the app generates output tabs plus a markdown download.

## Disclaimer

This project is an MVP for strategy-analysis assistance. It is not legal, financial, or professional consulting advice.
