from __future__ import annotations

from io import BytesIO
from typing import BinaryIO
import warnings

import pandas as pd

from core.schemas import DataProfile


MAX_SAMPLE_ROWS = 5
MAX_CATEGORICAL_VALUES = 5


def load_uploaded_dataset(file: BinaryIO, file_name: str) -> pd.DataFrame:
    extension = file_name.rsplit(".", 1)[-1].lower()
    if extension == "csv":
        return pd.read_csv(file)
    if extension in {"xlsx", "xls"}:
        content = file.read()
        return pd.read_excel(BytesIO(content))
    raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")


def build_data_profile(dataframe: pd.DataFrame, file_name: str) -> DataProfile:
    missing_values = dataframe.isna().sum().astype(int).to_dict()
    missing_percentages = (dataframe.isna().mean() * 100).round(2).to_dict()
    date_columns = detect_date_columns(dataframe)

    return DataProfile(
        file_name=file_name,
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        column_names=[str(column) for column in dataframe.columns],
        inferred_dtypes={str(column): str(dtype) for column, dtype in dataframe.dtypes.items()},
        missing_values={str(key): int(value) for key, value in missing_values.items()},
        missing_percentages={str(key): float(value) for key, value in missing_percentages.items()},
        duplicate_row_count=int(dataframe.duplicated().sum()),
        numeric_summary=_numeric_summary(dataframe),
        categorical_summary=_categorical_summary(dataframe),
        date_columns_detected=date_columns,
        sample_rows=_sample_rows(dataframe),
        data_quality_notes=_data_quality_notes(dataframe, missing_percentages),
        possible_analysis_suggestions=_analysis_suggestions(dataframe, date_columns),
    )


def profile_uploaded_dataset(file: BinaryIO, file_name: str) -> tuple[pd.DataFrame, DataProfile]:
    dataframe = load_uploaded_dataset(file, file_name)
    profile = build_data_profile(dataframe, file_name)
    return dataframe, profile


def _numeric_summary(dataframe: pd.DataFrame) -> dict[str, dict[str, float | int | None]]:
    numeric = dataframe.select_dtypes(include="number")
    summary: dict[str, dict[str, float | int | None]] = {}
    for column in numeric.columns:
        series = numeric[column]
        summary[str(column)] = {
            "count": _clean_number(series.count()),
            "mean": _clean_number(series.mean()),
            "std": _clean_number(series.std()),
            "min": _clean_number(series.min()),
            "p25": _clean_number(series.quantile(0.25)),
            "median": _clean_number(series.median()),
            "p75": _clean_number(series.quantile(0.75)),
            "max": _clean_number(series.max()),
        }
    return summary


def _categorical_summary(dataframe: pd.DataFrame) -> dict[str, dict[str, object]]:
    categorical = dataframe.select_dtypes(include=["object", "category", "bool"])
    summary: dict[str, dict[str, object]] = {}
    for column in categorical.columns:
        series = dataframe[column]
        top_values = series.value_counts(dropna=True).head(MAX_CATEGORICAL_VALUES)
        summary[str(column)] = {
            "unique_count": int(series.nunique(dropna=True)),
            "top_values": {str(index): int(value) for index, value in top_values.items()},
        }
    return summary


def detect_date_columns(dataframe: pd.DataFrame) -> list[str]:
    detected = []
    for column in dataframe.columns:
        series = dataframe[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            detected.append(str(column))
            continue
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        non_null = series.dropna()
        if non_null.empty:
            continue
        sample = non_null.astype(str).head(100)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().mean() >= 0.8:
            detected.append(str(column))
    return detected


def _sample_rows(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    sample = dataframe.head(MAX_SAMPLE_ROWS).where(pd.notna(dataframe.head(MAX_SAMPLE_ROWS)), None)
    return [
        {str(key): _clean_value(value) for key, value in row.items()}
        for row in sample.to_dict(orient="records")
    ]


def _data_quality_notes(dataframe: pd.DataFrame, missing_percentages: dict[object, float]) -> list[str]:
    notes = []
    if dataframe.empty:
        notes.append("Dataset is empty.")
    duplicate_count = int(dataframe.duplicated().sum())
    if duplicate_count:
        notes.append(f"{duplicate_count:,} duplicate rows detected.")
    high_missing = [str(column) for column, pct in missing_percentages.items() if pct >= 25]
    if high_missing:
        notes.append(f"Columns with at least 25% missing values: {', '.join(high_missing)}.")
    unnamed = [str(column) for column in dataframe.columns if str(column).lower().startswith("unnamed")]
    if unnamed:
        notes.append(f"Possible index/export artifact columns detected: {', '.join(unnamed)}.")
    if not notes:
        notes.append("No obvious structural quality issues detected from metadata profiling.")
    return notes


def _analysis_suggestions(dataframe: pd.DataFrame, date_columns: list[str]) -> list[str]:
    suggestions = []
    numeric_columns = [str(column) for column in dataframe.select_dtypes(include="number").columns]
    categorical_columns = [str(column) for column in dataframe.select_dtypes(include=["object", "category", "bool"]).columns]

    if numeric_columns and categorical_columns:
        suggestions.append("Compare numeric KPIs across customer, product, geography, or segment dimensions.")
    if date_columns and numeric_columns:
        suggestions.append("Run time-series trend analysis using detected date fields and numeric KPIs.")
    if categorical_columns:
        suggestions.append("Profile categorical distributions and identify high-volume or high-value segments.")
    if len(numeric_columns) >= 2:
        suggestions.append("Check correlations or driver relationships across numeric fields.")
    if not suggestions:
        suggestions.append("Review columns manually to define business metrics and analysis cuts.")
    return suggestions


def _clean_number(value: object) -> float | int | None:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, int | float):
        return round(float(value), 4)
    return None


def _clean_value(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value
