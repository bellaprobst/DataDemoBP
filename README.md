# DataDemoBP

## GL Summary Workflow

This repository contains a reusable workflow to analyze a GL Excel dump and produce summary outputs.

### Local usage

```bash
python scripts/analyze_gl.py --input "je_samples (1).xlsx" --output-dir outputs
```

Outputs written to `outputs/` include:

- `summary.json` - row/column counts, dtypes, missing values, and date ranges.
- `summary.md` - human-readable summary of the same information.
- `numeric_summary.csv` - descriptive statistics for numeric columns.
- `column_profile.csv` - per-column null counts and percentages.
- `benford/` - Benford's Law analysis outputs and visuals for numeric columns.
  - `benford_distribution.csv` - combined leading-digit distribution vs. expected.
  - `benford_overview.csv` - per-column MAD and chi-square metrics.
  - `charts/benford_combined.png` - combined leading-digit chart.
  - `charts/benford_<column>.png` - top column charts.

### GitHub Actions

The `GL Summary + Benford` workflow runs on every push and on manual dispatch. It installs Python dependencies, runs the analysis, and uploads the `outputs/` folder as an artifact.

To download the results:

1. Go to the **Actions** tab.
2. Select the latest **GL Summary + Benford** run.
3. Download the **gl-summary-outputs** artifact.
