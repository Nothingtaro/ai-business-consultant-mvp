Create a simple but practical financial assumption model for the business decision.

Business problem: {business_problem}
Budget: {budget}
Geography: {geography}
Target customers: {target_customers}
Constraints: {constraints}
Expected output: {expected_output}

Prior workflow outputs:
{prior_work}

Create management-level JSON with:
- A concise assumption table covering revenue drivers, price, volume, variable cost, fixed cost, gross margin, break-even logic, and best/base/worst cases.
- A KPI / driver tree that links management KPIs to drivers, formulas or logic, required data, and assumptions if no data is uploaded.
- Driver assumptions that separate revenue drivers, price, volume, variable cost, fixed cost, and gross margin.
- Three scenario rows named "Worst case", "Base case", and "Best case".
- Numeric scenario inputs where practical: price, volume, variable_cost_per_unit, and fixed_cost. Use plain numbers only, without currency symbols or commas, so Python can calculate revenue, costs, margin, break-even units, and operating profit.
- If a metric is not applicable, use null for the numeric field and explain briefly in notes.
- Break-even logic with the formula, interpretation, and key constraint.
- The 3-5 assumptions most likely to change the recommendation.

Keep the model simple. Prefer directional estimates that are explicit and reviewable over vague narrative. Clearly label estimates as assumptions unless they are supported by uploaded data.
