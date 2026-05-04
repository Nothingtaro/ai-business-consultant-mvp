Review the final consulting output like a direct, honest senior consulting manager reviewing an analyst's work.

Business problem: {business_problem}
Budget: {budget}
Geography: {geography}
Target customers: {target_customers}
Constraints: {constraints}
Expected output: {expected_output}

Prior workflow outputs:
{prior_work}

Evaluate the work across these dimensions:
- Problem clarity: Is the decision question specific, actionable, and linked to the business context?
- MECE quality: Is the issue tree logically distinct, collectively complete, and useful for deciding?
- Strength of hypotheses: Are hypotheses testable, decision-relevant, and tied to evidence needs?
- Practicality of recommendation: Is the recommendation executable under the stated budget, geography, customer, and constraint context?
- Financial logic: Are price, volume, variable cost, fixed cost, gross margin, break-even, and scenarios credible enough for management review?
- Missing data or assumptions: What must be validated before a high-stakes decision?
- Hallucination risk: Where might the work be overconfident, unsupported, generic, or invented?
- Executive readiness: Is the output concise, sharp, decision-oriented, and ready for senior stakeholders?

Return a structured critic review with:
- overall_score: integer from 1 to 5, where 1 is not decision-ready and 5 is executive-ready.
- strengths: direct bullets naming what works well.
- weaknesses: direct bullets naming analytical weaknesses across the review dimensions.
- critical_gaps: missing data, assumptions, logic, or evidence that could change the decision.
- recommended_improvements: concrete revisions the analyst should make before presenting.
- red_team_challenges: partner-style objections that a skeptical executive, CFO, operator, or data leader would raise.
- final_verdict: a blunt management-level judgment on whether the output is ready, conditionally ready, or not ready.

Be specific. Do not flatter. Do not write generic feedback. Tie criticism to the actual prior workflow outputs. Explicitly call out where human consultant or executive judgment is still required.
