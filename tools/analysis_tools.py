from __future__ import annotations

from typing import Any
import warnings

import pandas as pd

from core.schemas import AnalysisResult


SEMANTIC_ROLES = {"id", "date", "category", "numeric metric", "binary flag", "text", "unknown"}


def run_eda(df: pd.DataFrame) -> AnalysisResult:
    """Run a consulting-grade, pandas-only exploration of an uploaded dataframe."""
    if not isinstance(df, pd.DataFrame):
        return _error_result("data_exploration", "Data Exploration", "Uploaded dataset is invalid or unavailable.")
    if df.empty or len(df.columns) == 0:
        return _error_result("data_exploration", "Data Exploration", "Uploaded dataset is empty.")

    row_count = int(len(df))
    column_count = int(len(df.columns))
    duplicate_count = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    total_cells = row_count * column_count
    memory_usage_mb = round(float(df.memory_usage(deep=True).sum()) / (1024 * 1024), 3)
    date_columns = _detect_date_columns(df)
    date_profile = [_date_profile(df, column) for column in date_columns]
    date_range = _overall_date_range(date_profile)

    column_profile = [_column_profile(df, column) for column in df.columns]
    numeric_profile = [_numeric_profile(df, column) for column in get_numeric_columns(df)]
    categorical_profile = [_categorical_profile(df, column) for column in get_categorical_columns(df)]
    readiness = _business_analysis_readiness(df, column_profile, date_columns)
    quality = _data_quality_assessment(df, column_profile, numeric_profile, categorical_profile, duplicate_count)
    quality_score = _data_quality_score(row_count, duplicate_count, missing_cells, total_cells, quality)
    quality["data_quality_score"] = quality_score
    warnings_list = _quality_warnings(quality, readiness)
    executive_summary = _executive_summary(row_count, column_count, quality_score, readiness, quality)

    return AnalysisResult(
        analysis_type="data_exploration",
        title="Data Exploration",
        summary=executive_summary,
        input_columns_used=[str(column) for column in df.columns],
        result_table=column_profile,
        key_metrics={
            "dataset_overview": {
                "row_count": row_count,
                "column_count": column_count,
                "memory_usage_mb": memory_usage_mb,
                "duplicate_rows": duplicate_count,
                "missing_cell_count": missing_cells,
                "missing_cell_percentage": _round_pct(_safe_ratio(missing_cells, total_cells) or 0),
                "date_range": date_range,
            },
            "data_quality_assessment": quality,
            "numeric_profile": numeric_profile,
            "categorical_profile": categorical_profile,
            "date_profile": date_profile,
            "business_analysis_readiness": readiness,
            "executive_summary": executive_summary,
        },
        warnings=warnings_list,
        limitations=[
            "Data Exploration is descriptive and does not establish causality, forecasts, or final business recommendations.",
            "Semantic roles and suggested analyses are inferred from column names, values, and data types; confirm definitions with a business or data owner.",
            "Only summarized metadata and analysis outputs should be sent forward to LLM-based synthesis, not the full raw dataset.",
        ],
        suggested_next_steps=readiness["suggested_next_analyses"],
    )


def run_segmentation_analysis(
    df: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    weight_col: str | None = None,
    min_segment_size: int = 5,
) -> AnalysisResult:
    """Compare a numeric business metric across one segment dimension."""
    min_segment_size = max(1, int(min_segment_size or 1))
    required_columns = [segment_col, metric_col] + ([weight_col] if weight_col else [])
    error = _validate_columns(df, required_columns)
    if error:
        return error
    if not pd.api.types.is_numeric_dtype(df[metric_col]):
        return _error_result("segmentation", "Segmentation Analysis", f"Metric column '{metric_col}' must be numeric.")
    if weight_col and not pd.api.types.is_numeric_dtype(df[weight_col]):
        return _error_result("segmentation", "Segmentation Analysis", f"Weight column '{weight_col}' must be numeric.")

    working_columns = [segment_col, metric_col] + ([weight_col] if weight_col else [])
    working = df[working_columns].copy()
    working[segment_col] = working[segment_col].astype("object").where(working[segment_col].notna(), "[Missing]")
    metric = pd.to_numeric(working[metric_col], errors="coerce")
    metric_missing_count = int(metric.isna().sum())
    working[metric_col] = metric
    if weight_col:
        working[weight_col] = pd.to_numeric(working[weight_col], errors="coerce")
    valid_working = working.dropna(subset=[metric_col])
    if valid_working.empty:
        return _error_result("segmentation", "Segmentation Analysis", f"Metric column '{metric_col}' has no usable numeric values.")

    grouped = _build_segment_summary(working, segment_col, metric_col, weight_col)
    total_rows = int(grouped["rows"].sum())
    total_metric = float(grouped["metric_total"].sum())
    overall_average = float(valid_working[metric_col].mean())
    top_segment_share = _safe_ratio(float(grouped["metric_total"].max()), total_metric) or 0
    grouped["row_share_pct"] = grouped["rows"].apply(lambda value: _round_pct(_safe_ratio(value, total_rows) or 0))
    grouped["metric_share_pct"] = grouped["metric_total"].apply(lambda value: _round_pct(_safe_ratio(value, total_metric) or 0))
    grouped["average_index_vs_overall"] = grouped["metric_average"].apply(
        lambda value: _clean_number((_safe_ratio(value, overall_average) or 0) * 100)
    )
    grouped["attractiveness_score"] = grouped.apply(
        _segment_attractiveness_score(total_rows, total_metric, overall_average, top_segment_share, min_segment_size),
        axis=1,
    )
    grouped["interpretation_label"] = grouped.apply(
        _segment_interpretation_label(total_rows, total_metric, overall_average, min_segment_size),
        axis=1,
    )
    grouped = grouped.sort_values(["metric_total", "rows"], ascending=False)
    grouped["rank"] = grouped["attractiveness_score"].rank(method="first", ascending=False).astype(int)

    full_segment_count = int(grouped[segment_col].nunique(dropna=True))
    display_grouped = grouped.head(25).copy()
    table = _records(display_grouped)
    top_total = display_grouped.iloc[0] if not display_grouped.empty else None
    reliable_segments = grouped[grouped["rows"] >= min_segment_size]
    top_average = reliable_segments.sort_values("metric_average", ascending=False).head(1)
    top_average_label = str(top_average.iloc[0][segment_col]) if not top_average.empty else "Not enough sample"
    top_three_share = _round_pct(_safe_ratio(grouped["metric_total"].head(3).sum(), total_metric) or 0)
    top_performance = _records(reliable_segments.sort_values("metric_average", ascending=False).head(5))
    top_contribution = _records(grouped.sort_values("metric_total", ascending=False).head(5))
    bottom_performance = _records(reliable_segments.sort_values("metric_average", ascending=True).head(5))
    insufficient_sample = _records(grouped[grouped["rows"] < min_segment_size].sort_values("rows").head(25))
    business_interpretation = _segmentation_business_interpretation(
        grouped,
        segment_col,
        metric_col,
        min_segment_size,
        top_average_label,
        str(top_total[segment_col]) if top_total is not None else "N/A",
    )
    recommended_actions = _segmentation_recommended_actions(business_interpretation, segment_col, metric_col)

    warnings_list = _small_sample_warnings(grouped, "rows", min_segment_size)
    if full_segment_count > 25:
        warnings_list.append(f"{full_segment_count:,} segments found; result table shows the top 25 by total {metric_col}.")
    if full_segment_count > 50:
        warnings_list.append(f"{segment_col} has high cardinality ({full_segment_count:,} segments); group rare segments before using this for management decisions.")
    if metric_missing_count:
        warnings_list.append(f"{metric_missing_count:,} rows had missing or non-numeric values in {metric_col} and were excluded.")
    if total_metric == 0:
        warnings_list.append("Total metric value is zero, so metric-share interpretation is limited.")
    if top_segment_share >= 0.5:
        warnings_list.append("One segment contributes at least 50% of the total metric, indicating concentration risk.")

    summary = (
        f"Segmentation compared {metric_col} across {full_segment_count:,} {segment_col} segment(s). "
        f"The largest contributor is {top_total[segment_col] if top_total is not None else 'N/A'}, "
        f"and the highest-performing segment above the minimum size threshold is {top_average_label}."
    )

    return AnalysisResult(
        analysis_type="segmentation",
        title=f"Segmentation Analysis: {metric_col} by {segment_col}",
        summary=summary,
        input_columns_used=[column for column in [segment_col, metric_col, weight_col] if column],
        result_table=table,
        key_metrics={
            "segment_count": full_segment_count,
            "usable_row_count": total_rows,
            "excluded_metric_rows": metric_missing_count,
            "minimum_segment_size": min_segment_size,
            "weight_column": weight_col or "None",
            "metric_total": _clean_number(total_metric),
            "overall_average": _clean_number(overall_average),
            "top_segment_by_total": str(top_total[segment_col]) if top_total is not None else "N/A",
            "top_3_metric_share_pct": top_three_share,
            "highest_average_segment_min_size": top_average_label,
            "scoring_logic": (
                "1-5 score based on performance index vs overall average, segment row share, sample reliability, "
                "and concentration risk. Scores are directional and intended for prioritization."
            ),
            "top_segments_by_performance": top_performance,
            "top_segments_by_total_contribution": top_contribution,
            "bottom_segments_by_performance": bottom_performance,
            "segments_with_insufficient_sample": insufficient_sample,
            "business_interpretation": business_interpretation,
            "recommended_actions": recommended_actions,
        },
        warnings=warnings_list,
        limitations=[
            "Segmentation is descriptive and may reflect customer mix, channel mix, seasonality, or operational differences.",
            "Attractiveness scores are simple directional heuristics, not a substitute for profitability, capacity, or causal analysis.",
            "Use this as a prioritization lens; validate root causes with deeper cuts or additional evidence before making major decisions.",
        ],
        suggested_next_steps=recommended_actions,
    )


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(column) for column in df.select_dtypes(include="number").columns]


def get_categorical_columns(df: pd.DataFrame) -> list[str]:
    return [str(column) for column in df.select_dtypes(include=["object", "category", "bool"]).columns]


def _column_profile(df: pd.DataFrame, column: object) -> dict[str, Any]:
    series = df[column]
    non_null_count = int(series.notna().sum())
    unique_count = int(series.nunique(dropna=True))
    role = _semantic_role(series, unique_count, non_null_count)
    return {
        "column": str(column),
        "inferred_type": str(series.dtype),
        "semantic_role": role,
        "missing_count": int(series.isna().sum()),
        "missing_percentage": _round_pct(series.isna().mean()),
        "unique_count": unique_count,
        "sample_values": _sample_values(series),
    }


def _semantic_role(series: pd.Series, unique_count: int, non_null_count: int) -> str:
    name = str(series.name).lower()
    if non_null_count == 0:
        return "unknown"
    if _looks_like_date(series) or any(token in name for token in ("date", "time", "timestamp", "created_at", "updated_at")):
        return "date"
    if _looks_like_id(series, unique_count, non_null_count):
        return "id"
    if pd.api.types.is_bool_dtype(series) or unique_count == 2 or name.startswith(("is_", "has_")):
        return "binary flag"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric metric"
    if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
        if unique_count <= max(30, int(non_null_count * 0.2)):
            return "category"
        return "text"
    return "unknown"


def _numeric_profile(df: pd.DataFrame, column: str) -> dict[str, Any]:
    series = pd.to_numeric(df[column], errors="coerce")
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        outlier_count = 0
        outlier_signal = "No strong IQR outlier signal."
    else:
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        outlier_signal = f"{outlier_count:,} potential outlier(s) using 1.5x IQR rule."
    return {
        "column": str(column),
        "mean": _clean_number(series.mean()),
        "median": _clean_number(series.median()),
        "min": _clean_number(series.min()),
        "max": _clean_number(series.max()),
        "standard_deviation": _clean_number(series.std()),
        "p25": _clean_number(q1),
        "p75": _clean_number(q3),
        "missing_percentage": _round_pct(series.isna().mean()),
        "outlier_count": outlier_count,
        "outlier_signal": outlier_signal,
    }


def _categorical_profile(df: pd.DataFrame, column: str) -> dict[str, Any]:
    series = df[column]
    value_counts = series.value_counts(dropna=True)
    non_null_count = int(series.notna().sum())
    top_values = [
        {
            "value": str(_clean_value(value)),
            "frequency": int(count),
            "share_pct": _round_pct(_safe_ratio(count, non_null_count) or 0),
        }
        for value, count in value_counts.head(5).items()
    ]
    rare_count = int((value_counts == 1).sum())
    cardinality = int(series.nunique(dropna=True))
    long_tail_warning = ""
    if cardinality > 20 and rare_count / max(cardinality, 1) >= 0.5:
        long_tail_warning = "Long-tail distribution; many rare categories may need grouping before analysis."
    return {
        "column": str(column),
        "cardinality": cardinality,
        "top_values": top_values,
        "rare_category_count": rare_count,
        "long_tail_warning": long_tail_warning,
    }


def _date_profile(df: pd.DataFrame, column: str) -> dict[str, Any]:
    parsed = _parse_dates(df[column])
    valid = parsed.dropna()
    return {
        "column": str(column),
        "min_date": valid.min().date().isoformat() if not valid.empty else "Not available",
        "max_date": valid.max().date().isoformat() if not valid.empty else "Not available",
        "unique_dates": int(valid.dt.date.nunique()) if not valid.empty else 0,
        "detected_granularity": _date_granularity(valid),
        "missing_percentage": _round_pct(parsed.isna().mean()),
    }


def _data_quality_assessment(
    df: pd.DataFrame,
    column_profile: list[dict[str, Any]],
    numeric_profile: list[dict[str, Any]],
    categorical_profile: list[dict[str, Any]],
    duplicate_count: int,
) -> dict[str, Any]:
    constant_columns = [
        row["column"]
        for row in column_profile
        if row["unique_count"] <= 1 and row["missing_percentage"] < 100
    ]
    near_constant_columns = [
        str(column)
        for column in df.columns
        if _top_value_share(df[column]) >= 0.95 and int(df[column].nunique(dropna=True)) > 1
    ]
    high_cardinality_categorical_columns = [
        row["column"]
        for row in categorical_profile
        if row["cardinality"] > 30
    ]
    potential_id_columns = [row["column"] for row in column_profile if row["semantic_role"] == "id"]
    potential_leakage_columns = [
        row["column"]
        for row in column_profile
        if any(token in row["column"].lower() for token in ("target", "label", "outcome", "churned", "converted", "prediction", "score"))
    ]
    suspicious_values = _suspicious_values(df, numeric_profile)
    missing_columns = [
        f"{row['column']}: {row['missing_percentage']}%"
        for row in column_profile
        if row["missing_percentage"] and row["missing_percentage"] > 0
    ]
    return {
        "missing_value_summary": missing_columns or ["No missing values detected."],
        "duplicate_summary": f"{duplicate_count:,} duplicate row(s) detected." if duplicate_count else "No duplicate rows detected.",
        "constant_columns": constant_columns,
        "near_constant_columns": near_constant_columns,
        "high_cardinality_categorical_columns": high_cardinality_categorical_columns,
        "potential_id_columns": potential_id_columns,
        "potential_leakage_columns": potential_leakage_columns,
        "suspicious_values": suspicious_values or ["No obvious suspicious numeric values detected."],
    }


def _business_analysis_readiness(
    df: pd.DataFrame,
    column_profile: list[dict[str, Any]],
    date_columns: list[str],
) -> dict[str, Any]:
    likely_segmentation_columns = [
        row["column"]
        for row in column_profile
        if row["semantic_role"] in {"category", "binary flag"} and 1 < row["unique_count"] <= 30
    ]
    likely_target_metric_columns = [
        row["column"]
        for row in column_profile
        if row["semantic_role"] == "numeric metric" and not _looks_like_id(df[row["column"]], row["unique_count"], int(df[row["column"]].notna().sum()))
    ]
    likely_revenue_value_columns = [
        column
        for column in likely_target_metric_columns
        if any(token in column.lower() for token in ("revenue", "sales", "amount", "value", "price", "gmv", "profit", "margin", "cost"))
    ]
    likely_conversion_binary_columns = [
        row["column"]
        for row in column_profile
        if row["semantic_role"] == "binary flag"
        or any(token in row["column"].lower() for token in ("converted", "conversion", "won", "active", "churn", "retained"))
    ]
    suggested = ["Run Segmentation Analysis using a reliable segment column and the most decision-relevant numeric metric."]
    if likely_revenue_value_columns and likely_segmentation_columns:
        suggested.append(f"Prioritize value segmentation: {likely_revenue_value_columns[0]} by {likely_segmentation_columns[0]}.")
    if date_columns and likely_target_metric_columns:
        suggested.append("Later, add trend analysis by detected date fields once this MVP expands beyond exploration and segmentation.")
    if likely_conversion_binary_columns and likely_segmentation_columns:
        suggested.append("Compare conversion or retention flags across segments to identify where performance differs.")
    return {
        "likely_segmentation_columns": likely_segmentation_columns,
        "likely_target_metric_columns": likely_target_metric_columns,
        "likely_revenue_value_columns": likely_revenue_value_columns,
        "likely_conversion_binary_columns": likely_conversion_binary_columns,
        "likely_date_columns": date_columns,
        "suggested_next_analyses": suggested,
    }


def _data_quality_score(
    row_count: int,
    duplicate_count: int,
    missing_cells: int,
    total_cells: int,
    quality: dict[str, Any],
) -> int:
    score = 5
    missing_pct = _safe_ratio(missing_cells, total_cells) or 0
    duplicate_pct = _safe_ratio(duplicate_count, row_count) or 0
    if row_count < 20:
        score -= 1
    if missing_pct >= 0.1:
        score -= 1
    if missing_pct >= 0.3:
        score -= 1
    if duplicate_pct >= 0.05:
        score -= 1
    if quality["constant_columns"] or quality["near_constant_columns"]:
        score -= 1
    if quality["potential_leakage_columns"]:
        score -= 1
    return max(1, min(5, score))


def _quality_warnings(quality: dict[str, Any], readiness: dict[str, Any]) -> list[str]:
    warnings_list = []
    if quality["data_quality_score"] <= 2:
        warnings_list.append("Data quality score is low; use outputs for orientation only until issues are resolved.")
    if quality["constant_columns"]:
        warnings_list.append(f"Constant columns detected: {', '.join(quality['constant_columns'])}.")
    if quality["near_constant_columns"]:
        warnings_list.append(f"Near-constant columns detected: {', '.join(quality['near_constant_columns'])}.")
    if quality["high_cardinality_categorical_columns"]:
        warnings_list.append(f"High-cardinality categorical columns may need grouping: {', '.join(quality['high_cardinality_categorical_columns'][:8])}.")
    if quality["potential_leakage_columns"]:
        warnings_list.append(f"Potential leakage/outcome columns detected: {', '.join(quality['potential_leakage_columns'])}.")
    if not readiness["likely_segmentation_columns"]:
        warnings_list.append("No strong segmentation columns detected.")
    if not readiness["likely_target_metric_columns"]:
        warnings_list.append("No strong numeric target metric columns detected.")
    return warnings_list


def _executive_summary(
    row_count: int,
    column_count: int,
    quality_score: int,
    readiness: dict[str, Any],
    quality: dict[str, Any],
) -> str:
    reliable = []
    caution = []
    if readiness["likely_target_metric_columns"]:
        reliable.append(f"{len(readiness['likely_target_metric_columns'])} numeric metric candidate(s)")
    if readiness["likely_segmentation_columns"]:
        reliable.append(f"{len(readiness['likely_segmentation_columns'])} segmentation candidate(s)")
    if readiness["likely_date_columns"]:
        reliable.append(f"{len(readiness['likely_date_columns'])} date field(s)")
    if quality["potential_id_columns"]:
        caution.append("ID-like columns should not be treated as business segments.")
    if quality["potential_leakage_columns"]:
        caution.append("possible leakage/outcome columns require care.")
    if quality["high_cardinality_categorical_columns"]:
        caution.append("some categories are high-cardinality and may need grouping.")
    reliable_text = ", ".join(reliable) if reliable else "limited obvious business-analysis structure"
    caution_text = " ".join(caution) if caution else "No major structural cautions were detected from this pass."
    next_analysis = readiness["suggested_next_analyses"][0] if readiness["suggested_next_analyses"] else "Confirm data definitions before analysis."
    return (
        f"The dataset contains {row_count:,} rows and {column_count:,} columns with a data quality score of {quality_score}/5. "
        f"It appears to contain {reliable_text}. {caution_text} Recommended next step: {next_analysis}"
    )


def _detect_date_columns(df: pd.DataFrame) -> list[str]:
    detected = []
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            detected.append(str(column))
            continue
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        parsed = _parse_dates(series.dropna().head(100))
        if not parsed.empty and parsed.notna().mean() >= 0.8:
            detected.append(str(column))
    return detected


def _looks_like_date(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
        return False
    non_null = series.dropna()
    if non_null.empty:
        return False
    parsed = _parse_dates(non_null.head(50))
    return bool(parsed.notna().mean() >= 0.8)


def _parse_dates(series: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.to_datetime(series, errors="coerce")


def _overall_date_range(date_profile: list[dict[str, Any]]) -> str:
    valid_min = [item["min_date"] for item in date_profile if item["min_date"] != "Not available"]
    valid_max = [item["max_date"] for item in date_profile if item["max_date"] != "Not available"]
    if not valid_min or not valid_max:
        return "No date range detected."
    return f"{min(valid_min)} to {max(valid_max)}"


def _date_granularity(valid_dates: pd.Series) -> str:
    if valid_dates.empty:
        return "unknown"
    normalized = valid_dates.sort_values().dt.normalize().drop_duplicates()
    if len(normalized) <= 1:
        return "single date"
    day_diffs = normalized.diff().dropna().dt.days
    median_days = day_diffs.median()
    if median_days <= 1:
        return "daily or finer"
    if 6 <= median_days <= 8:
        return "weekly"
    if 27 <= median_days <= 32:
        return "monthly"
    if 80 <= median_days <= 100:
        return "quarterly"
    if 350 <= median_days <= 380:
        return "yearly"
    return "irregular"


def _suspicious_values(df: pd.DataFrame, numeric_profile: list[dict[str, Any]]) -> list[str]:
    notes = []
    for profile in numeric_profile:
        column = profile["column"]
        series = pd.to_numeric(df[column], errors="coerce")
        name = column.lower()
        negative_count = int((series < 0).sum())
        if negative_count and any(token in name for token in ("revenue", "sales", "amount", "price", "quantity", "count", "age")):
            notes.append(f"{column}: {negative_count:,} negative value(s) in a field that is usually non-negative.")
        if profile["outlier_count"]:
            notes.append(f"{column}: {profile['outlier_signal']}")
    return notes


def _sample_values(series: pd.Series) -> str:
    values = [_clean_value(value) for value in series.dropna().head(3).tolist()]
    return "; ".join(str(value) for value in values) if values else "No non-null values"


def _top_value_share(series: pd.Series) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0
    return float(non_null.value_counts(normalize=True).iloc[0])


def _looks_like_id(series: pd.Series, unique_count: int, non_null_count: int) -> bool:
    name = str(series.name).lower()
    if name in {"id", "uuid"} or name.endswith("_id") or name.endswith(" id"):
        return True
    return non_null_count > 20 and unique_count == non_null_count


def _valid_dataframe(df: pd.DataFrame) -> bool:
    return isinstance(df, pd.DataFrame) and not df.empty


def _validate_columns(df: pd.DataFrame, columns: list[str]) -> AnalysisResult | None:
    if not _valid_dataframe(df):
        return _error_result("validation", "Analysis Input Validation", "Uploaded dataset is empty or unavailable.")
    missing = [column for column in columns if column not in df.columns]
    if missing:
        return _error_result("validation", "Analysis Input Validation", f"Missing required column(s): {', '.join(missing)}.")
    return None


def _build_segment_summary(
    working: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    weight_col: str | None,
) -> pd.DataFrame:
    source = working.copy()
    source["_metric_missing"] = source[metric_col].isna()
    valid_source = source.dropna(subset=[metric_col]).copy()
    if weight_col:
        valid_source["_weighted_metric"] = valid_source[metric_col] * valid_source[weight_col].fillna(0)
        grouped = valid_source.groupby(segment_col, dropna=False).agg(
            rows=(metric_col, "count"),
            metric_mean=(metric_col, "mean"),
            metric_median=(metric_col, "median"),
            metric_sum=(metric_col, "sum"),
            metric_min=(metric_col, "min"),
            metric_max=(metric_col, "max"),
            weight_total=(weight_col, "sum"),
            weighted_metric_sum=("_weighted_metric", "sum"),
            missing_metric_count=(metric_col, lambda values: int(values.isna().sum())),
        ).reset_index()
        grouped["weighted_metric_average"] = grouped.apply(
            lambda row: _safe_ratio(row["weighted_metric_sum"], row["weight_total"]),
            axis=1,
        )
    else:
        grouped = valid_source.groupby(segment_col, dropna=False).agg(
            rows=(metric_col, "count"),
            metric_mean=(metric_col, "mean"),
            metric_median=(metric_col, "median"),
            metric_sum=(metric_col, "sum"),
            metric_min=(metric_col, "min"),
            metric_max=(metric_col, "max"),
            missing_metric_count=(metric_col, lambda values: int(values.isna().sum())),
        ).reset_index()
    grouped = grouped.rename(
        columns={
            segment_col: "segment_name",
            "metric_mean": "metric_average",
            "metric_sum": "metric_total",
        }
    )
    # Keep the original segment column name available for existing UI/export expectations.
    grouped[segment_col] = grouped["segment_name"]
    grouped["missing_metric_count"] = grouped["segment_name"].map(
        source.groupby(segment_col)["_metric_missing"].sum().astype(int)
    ).fillna(0).astype(int)
    return grouped


def _small_sample_warnings(df: pd.DataFrame, count_col: str, min_segment_size: int) -> list[str]:
    if count_col not in df.columns:
        return []
    low_sample_count = int((df[count_col] < min_segment_size).sum())
    return [f"{low_sample_count} segment(s) have fewer than {min_segment_size} rows; interpret carefully."] if low_sample_count else []


def _segment_attractiveness_score(
    total_rows: int,
    total_metric: float,
    overall_average: float,
    top_segment_share: float,
    min_segment_size: int,
):
    def score(row: pd.Series) -> int:
        if row["rows"] < min_segment_size:
            return 1
        performance_index = _safe_ratio(row["metric_average"], overall_average) or 0
        row_share = _safe_ratio(row["rows"], total_rows) or 0
        metric_share = _safe_ratio(row["metric_total"], total_metric) or 0
        score_value = 1
        if performance_index >= 1.25:
            score_value += 2
        elif performance_index >= 1.05:
            score_value += 1
        if row_share >= 0.1:
            score_value += 1
        if row["rows"] >= min_segment_size * 3:
            score_value += 1
        if metric_share >= 0.5 and top_segment_share >= 0.5:
            score_value -= 1
        return max(1, min(5, score_value))

    return score


def _segment_interpretation_label(
    total_rows: int,
    total_metric: float,
    overall_average: float,
    min_segment_size: int,
):
    def label(row: pd.Series) -> str:
        if row["rows"] < min_segment_size:
            return "insufficient sample"
        row_share = _safe_ratio(row["rows"], total_rows) or 0
        metric_share = _safe_ratio(row["metric_total"], total_metric) or 0
        performance_index = _safe_ratio(row["metric_average"], overall_average) or 0
        if performance_index >= 1.15 and row_share >= 0.1:
            return "high-value"
        if performance_index >= 1.15 and row_share < 0.1:
            return "niche but attractive"
        if performance_index < 0.9 and row_share >= 0.1:
            return "large but underperforming"
        if performance_index < 0.9 and metric_share < 0.05:
            return "low priority"
        return "low priority"

    return label


def _segmentation_business_interpretation(
    grouped: pd.DataFrame,
    segment_col: str,
    metric_col: str,
    min_segment_size: int,
    top_performance_segment: str,
    top_contribution_segment: str,
) -> dict[str, list[str]]:
    attractive = grouped[grouped["interpretation_label"].isin(["high-value", "niche but attractive"])]
    underperforming = grouped[grouped["interpretation_label"] == "large but underperforming"]
    validation = grouped[grouped["interpretation_label"] == "insufficient sample"]
    return {
        "attractive_segments": [
            f"{row[segment_col]}: {row['interpretation_label']} with average index {row['average_index_vs_overall']}."
            for _, row in attractive.head(5).iterrows()
        ] or [f"No segment clearly over-indexed above the minimum size threshold of {min_segment_size} rows."],
        "underperforming_segments": [
            f"{row[segment_col]}: large segment under-indexing on {metric_col}; investigate drivers before reallocating spend."
            for _, row in underperforming.head(5).iterrows()
        ] or ["No large underperforming segment was clearly detected."],
        "segments_requiring_validation": [
            f"{row[segment_col]}: below minimum sample threshold with {int(row['rows'])} row(s)."
            for _, row in validation.head(10).iterrows()
        ] or ["No segments fell below the minimum sample threshold."],
        "business_actions_to_consider": [
            f"Use {top_performance_segment} as the first candidate for deeper customer/product/channel diagnostics.",
            f"Review whether {top_contribution_segment} is attractive because of true performance or simply because it is large.",
            "Validate profitability, acquisition cost, operational fit, and repeatability before prioritizing investment.",
        ],
        "data_limitations": [
            "Segmentation is descriptive and does not explain causality.",
            "Small segments can look attractive due to noise; use the minimum-size threshold to avoid overreacting.",
            "A segment can have high total contribution because it is large, even if average performance is weak.",
        ],
    }


def _segmentation_recommended_actions(
    interpretation: dict[str, list[str]],
    segment_col: str,
    metric_col: str,
) -> list[str]:
    actions = [
        f"Prioritize the highest-scoring {segment_col} segments for deeper validation against profitability and operational feasibility.",
        f"Investigate large underperforming {segment_col} segments to identify whether mix, pricing, conversion, or service model explains lower {metric_col}.",
        "Run a small A/B test or targeted campaign before scaling spend based on segment differences.",
        "Improve data collection for segments flagged as insufficient sample or high-cardinality.",
        "Validate segment profitability before treating high metric performance as strategic attractiveness.",
    ]
    if interpretation["attractive_segments"]:
        actions.append("Use attractive segments as candidates for hypothesis refinement and insight synthesis.")
    return actions


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.where(pd.notna(df), None)
    return [{str(key): _clean_value(value) for key, value in row.items()} for row in clean.to_dict(orient="records")]


def _error_result(analysis_type: str, title: str, message: str) -> AnalysisResult:
    return AnalysisResult(
        analysis_type=analysis_type,
        title=title,
        summary=message,
        warnings=[message],
        limitations=["Analysis was not run because required inputs were unavailable or invalid."],
        suggested_next_steps=["Select valid columns and rerun the analysis."],
    )


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    numerator = _to_float(numerator)
    denominator = _to_float(denominator)
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _to_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_number(value: Any) -> float | int | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    if float(numeric).is_integer():
        return int(numeric)
    return round(float(numeric), 4)


def _round_pct(value: Any) -> float | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return round(numeric * 100, 2)


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value
