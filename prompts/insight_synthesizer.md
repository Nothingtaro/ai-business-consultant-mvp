Convert the consulting work, uploaded data profile metadata, and saved predefined analysis results into executive-ready insights.

Business problem: {business_problem}
Budget: {budget}
Geography: {geography}
Target customers: {target_customers}
Constraints: {constraints}
Expected output: {expected_output}

Prior workflow outputs:
{prior_work}

Synthesize the available evidence into structured consulting insights. Use only the information in the business problem and prior workflow outputs. If an Uploaded Data Profile or Saved Data Analysis Result appears above, use only the summarized metadata, statistics, and saved analysis summaries. Do not assume access to the full raw dataset.

Return JSON that matches the required schema exactly:
- key_insights: executive-ready insights, not raw observations
- observations: factual patterns or analysis readouts only
- supporting_evidence: evidence tied to the insights, citing whether it comes from uploaded data profile metadata, saved analysis results, or assumptions
- business_implications: what the insights mean for the decision
- confidence_level: high, medium, or low
- limitations: explicit data, method, sample, missingness, and causality limitations
- recommended_actions: actions tied to the insights
- hypothesis_support_status: one object per important hypothesis with hypothesis, status, and rationale

Rules:
- Separate observations from insights.
- Tie every insight to supporting evidence.
- Tie every recommendation to an insight.
- Explicitly mention data limitations.
- Do not overclaim from weak data.
- Avoid causal claims unless the evidence supports causality.
- If no saved data analysis results are available, label the synthesis as assumption-led and keep confidence conservative.
- If saved analysis results are available, separate data-backed findings from assumptions.
- Keep the language professional, credible, and executive-friendly.
