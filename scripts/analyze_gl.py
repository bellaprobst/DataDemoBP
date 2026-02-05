#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import matplotlib.pyplot as plt


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


def first_digit(value: float) -> int | None:
    if pd.isna(value):
        return None
    value = abs(float(value))
    if value == 0:
        return None
    while value < 1:
        value *= 10
    while value >= 10:
        value /= 10
    return int(value)


def benford_expected_distribution() -> pd.Series:
    return pd.Series({digit: math.log10(1 + 1 / digit) for digit in range(1, 10)})


def benford_distribution(series: pd.Series) -> pd.Series:
    digits = series.dropna().apply(first_digit)
    digits = digits.dropna().astype(int)
    counts = digits.value_counts().reindex(range(1, 10), fill_value=0)
    return counts


def benford_stats(counts: pd.Series) -> Dict[str, float]:
    total = counts.sum()
    expected = benford_expected_distribution()
    if total == 0:
        return {"n": 0, "mad": float("nan"), "chi_square": float("nan")}
    actual = counts / total
    mad = float((actual - expected).abs().mean())
    chi_square = float((((actual - expected) ** 2) / expected).sum() * total)
    return {"n": int(total), "mad": mad, "chi_square": chi_square}


def write_benford_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    benford_dir = output_dir / "benford"
    chart_dir = benford_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        (benford_dir / "benford_overview.csv").write_text("column,n,mad,chi_square\n")
        return

    combined_series = numeric_df.stack()
    combined_counts = benford_distribution(combined_series)
    combined_expected = benford_expected_distribution()
    combined_total = combined_counts.sum()
    combined_actual = combined_counts / combined_total if combined_total else combined_counts

    distribution_df = pd.DataFrame({
        "digit": range(1, 10),
        "actual": combined_actual.values,
        "expected": combined_expected.values,
        "count": combined_counts.values,
    })
    distribution_df.to_csv(benford_dir / "benford_distribution.csv", index=False)

    overview_rows = []
    for column in numeric_df.columns:
        counts = benford_distribution(numeric_df[column])
        stats = benford_stats(counts)
        overview_rows.append({
            "column": str(column),
            "n": stats["n"],
            "mad": stats["mad"],
            "chi_square": stats["chi_square"],
        })
    overview_df = pd.DataFrame(overview_rows).sort_values(by="n", ascending=False)
    overview_df.to_csv(benford_dir / "benford_overview.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(distribution_df["digit"], distribution_df["actual"], label="Actual", alpha=0.7)
    ax.plot(distribution_df["digit"], distribution_df["expected"], color="black", marker="o", label="Expected")
    ax.set_title("Benford's Law - Combined Numeric Columns")
    ax.set_xlabel("Leading Digit")
    ax.set_ylabel("Proportion")
    ax.set_xticks(range(1, 10))
    ax.legend()
    fig.tight_layout()
    fig.savefig(chart_dir / "benford_combined.png")
    plt.close(fig)

    top_columns = overview_df.head(3)["column"].tolist()
    for column in top_columns:
        counts = benford_distribution(numeric_df[column])
        total = counts.sum()
        if total == 0:
            continue
        actual = counts / total
        distribution = pd.DataFrame({
            "digit": range(1, 10),
            "actual": actual.values,
            "expected": combined_expected.values,
        })
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(distribution["digit"], distribution["actual"], label="Actual", alpha=0.7)
        ax.plot(distribution["digit"], distribution["expected"], color="black", marker="o", label="Expected")
        ax.set_title(f"Benford's Law - {column}")
        ax.set_xlabel("Leading Digit")
        ax.set_ylabel("Proportion")
        ax.set_xticks(range(1, 10))
        ax.legend()
        fig.tight_layout()
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in column)
        fig.savefig(chart_dir / f"benford_{safe_name}.png")
        plt.close(fig)

    benford_md = [
        "# Benford's Law Summary",
        "",
        "## Combined Numeric Columns",
        "",
        f"* Records analyzed: {combined_total}",
        "",
        "See `benford_distribution.csv` and `charts/benford_combined.png` for details.",
        "",
        "## Column-level Overview",
        "",
        "See `benford_overview.csv` for column metrics (MAD and chi-square).",
    ]
    (benford_dir / "benford_summary.md").write_text("\n".join(benford_md))


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
    write_benford_outputs(df, output_dir)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    df = pd.read_excel(input_path)
    summary = build_summary(df)
    write_outputs(df, summary, output_dir)


if __name__ == "__main__":
    main()
