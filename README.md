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

### GitHub Actions

The `GL Summary` workflow runs on every push and on manual dispatch. It installs Python dependencies, runs the analysis, and uploads the `outputs/` folder as an artifact.

To download the results:

1. Go to the **Actions** tab.
2. Select the latest **GL Summary** run.
3. Download the **gl-summary-outputs** artifact.
