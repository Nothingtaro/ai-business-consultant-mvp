from __future__ import annotations

from core.config import AppConfig
from core.schemas import AgentResult, BusinessProblemInput, FinancialAssumptionOutput, FinancialScenario
from utils.json_parser import model_to_markdown, parse_model_output
from utils.llm_client import call_llm
from utils.prompt_loader import load_prompt_template, render_prompt


def run(business_input: BusinessProblemInput, prior_results: list[AgentResult], config: AppConfig) -> AgentResult:
    system_prompt = load_prompt_template(config.prompts_dir, "system")
    template = load_prompt_template(config.prompts_dir, "financial_assumptions")
    prompt = render_prompt(template, business_input, prior_results, FinancialAssumptionOutput)
    raw_output = call_llm(system_prompt, prompt, config=config)
    parsed = parse_model_output(raw_output, FinancialAssumptionOutput)
    parsed = _add_scenario_calculations(parsed)
    return AgentResult(
        key="financial_assumptions",
        title="Financial Assumption Table",
        content=model_to_markdown(parsed),
        data=parsed.model_dump(),
    )


def _add_scenario_calculations(output: FinancialAssumptionOutput) -> FinancialAssumptionOutput:
    calculated_scenarios = [_calculate_scenario(scenario) for scenario in output.scenarios]
    return output.model_copy(update={"scenarios": calculated_scenarios})


def _calculate_scenario(scenario: FinancialScenario) -> FinancialScenario:
    price = scenario.price
    volume = scenario.volume
    variable_cost_per_unit = scenario.variable_cost_per_unit
    fixed_cost = scenario.fixed_cost

    revenue = _coalesce(_multiply(price, volume), scenario.revenue)
    variable_cost = _coalesce(_multiply(variable_cost_per_unit, volume), scenario.variable_cost)
    gross_profit = _coalesce(_subtract(revenue, variable_cost), scenario.gross_profit)
    gross_margin = _coalesce(_divide(gross_profit, revenue), scenario.gross_margin)
    contribution_margin_per_unit = _coalesce(
        _subtract(price, variable_cost_per_unit),
        scenario.contribution_margin_per_unit,
    )
    break_even_units = _coalesce(_divide_positive(fixed_cost, contribution_margin_per_unit), scenario.break_even_units)
    operating_profit = _coalesce(_subtract(gross_profit, fixed_cost), scenario.operating_profit)

    return scenario.model_copy(
        update={
            "revenue": _round_currency(revenue),
            "variable_cost": _round_currency(variable_cost),
            "gross_profit": _round_currency(gross_profit),
            "gross_margin": _round_ratio(gross_margin),
            "contribution_margin_per_unit": _round_currency(contribution_margin_per_unit),
            "break_even_units": _round_units(break_even_units),
            "operating_profit": _round_currency(operating_profit),
        }
    )


def _coalesce(primary: float | None, fallback: float | None) -> float | None:
    return primary if primary is not None else fallback


def _multiply(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left * right


def _subtract(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _divide_positive(numerator: float | None, denominator: float | None) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return _divide(numerator, denominator)


def _round_currency(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _round_ratio(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _round_units(value: float | None) -> float | None:
    return round(value, 0) if value is not None else None
