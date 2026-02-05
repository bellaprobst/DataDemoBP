#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze GL Excel dump and produce summary outputs.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the Excel file to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory to write analysis outputs.",
    )
    return parser.parse_args()


def detect_date_ranges(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    date_ranges: Dict[str, Dict[str, str]] = {}
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            parsed = series
        else:
            parsed = pd.to_datetime(series, errors="coerce", utc=False, infer_datetime_format=True)
        non_null = parsed.dropna()
        if non_null.empty:
            continue
        date_ranges[str(column)] = {
            "min": str(non_null.min()),
            "max": str(non_null.max()),
        }
    return date_ranges


def build_summary(df: pd.DataFrame) -> Dict[str, Any]:
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    missing_counts = df.isna().sum().sort_values(ascending=False)

    summary = {
        "row_count": row_count,
        "column_count": column_count,
        "columns": [str(column) for column in df.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "missing_values": missing_counts.to_dict(),
        "date_ranges": detect_date_ranges(df),
    }
    return summary


def write_outputs(df: pd.DataFrame, summary: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    numeric_stats = df.describe(include=["number"]).transpose()
    if not numeric_stats.empty:
        numeric_stats.to_csv(output_dir / "numeric_summary.csv")

    column_profile = pd.DataFrame({
        "column": [str(column) for column in df.columns],
        "dtype": [str(dtype) for dtype in df.dtypes],
        "non_null_count": df.notna().sum().values,
        "null_count": df.isna().sum().values,
    })
    column_profile["null_percent"] = (
        column_profile["null_count"] / df.shape[0] * 100
    ).round(2)
    column_profile.to_csv(output_dir / "column_profile.csv", index=False)

    md_lines = [
        "# GL Summary",
        "",
        f"* Rows: {summary['row_count']}",
        f"* Columns: {summary['column_count']}",
        "",
        "## Date Ranges",
    ]
    if summary["date_ranges"]:
        md_lines.append("| Column | Min | Max |")
        md_lines.append("| --- | --- | --- |")
        for column, range_values in summary["date_ranges"].items():
            md_lines.append(
                f"| {column} | {range_values['min']} | {range_values['max']} |"
            )
    else:
        md_lines.append("No date columns detected.")

    md_lines.extend(["", "## Top Missing Columns", ""])
    missing_series = pd.Series(summary["missing_values"]).sort_values(ascending=False)
    if not missing_series.empty:
        md_lines.append("| Column | Missing Values |")
        md_lines.append("| --- | --- |")
        for column, count in missing_series.head(10).items():
            md_lines.append(f"| {column} | {count} |")
    else:
        md_lines.append("No missing values detected.")

    (output_dir / "summary.md").write_text("\n".join(md_lines))


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    df = pd.read_excel(input_path)
    summary = build_summary(df)
    write_outputs(df, summary, output_dir)


if __name__ == "__main__":
    main()
