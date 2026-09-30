# Data Acquisition, Cleaning and Exploratory Data Analysis of Mauna Loa Atmospheric CO₂ Data

## Overview

This YUVA Intern Week 1 project acquires the public Statsmodels Mauna Loa weekly atmospheric CO₂ series, validates and cleans it, performs exploratory analysis, generates five figures, and builds a DOCX report. The raw dataset is preserved separately from the interpolated cleaned dataset.

## Objectives

- Acquire a public time-series dataset with Python.
- Inspect and clean values, dates, duplicates, and missing observations with documented decisions.
- Summarize the distribution, long-term pattern, annual means, and calendar-month pattern.
- Deliver a reusable pipeline, executable notebook, visualizations, and a Word report.

## Dataset

- **Name:** Mauna Loa Weekly Atmospheric CO₂ Data (`statsmodels.datasets.co2`).
- **Source:** Statsmodels' public dataset interface.
- **Representation:** Weekly atmospheric carbon dioxide concentration measurements at Mauna Loa.
- **Observed period:** 1958-03-29 through 2001-12-29.
- **Unit:** Parts per million (ppm).
- **Documentation:** [Statsmodels CO₂ dataset](https://www.statsmodels.org/devel/datasets/generated/co2.html).

The acquisition run returned 2,284 rows and one measurement column (`co2`, `float64`), indexed by dates. The source contains 59 missing CO₂ values and no duplicate dates.

## Technologies

Python 3, pandas, NumPy, Matplotlib, Seaborn, Statsmodels, Jupyter Notebook, and python-docx.

## Project Structure

```text
README.md
requirements.txt
.gitignore
data/
	co2_raw_acquired.csv
	co2_cleaned.csv
	analysis_summary.json
notebooks/
	Week_1_CO2_EDA.ipynb
src/
	analysis.py
visualizations/
	01_missing_values.png
	02_co2_time_series.png
	03_annual_mean.png
	04_distribution.png
	05_monthly_pattern.png
report/
	Week_1_Data_Acquisition_Cleaning_EDA.docx
```

## Data Cleaning Methodology

- **Missing values:** The source has 59 missing CO₂ readings. Values are converted with `pd.to_numeric(..., errors="coerce")`, so invalid entries become missing and are handled explicitly.
- **Interpolation:** The sorted DatetimeIndex allows `interpolate(method="time", limit_area="inside")` to estimate interior gaps using their time positions. This preserves local temporal continuity better than substituting the overall mean, which ignores chronology and suppresses variation. Interpolated values remain estimates, not observations. The pipeline fails rather than silently extrapolating if edge gaps remain.
- **Duplicate dates:** Duplicate observations are identified by date, not by equality of CO₂ readings. If any repeated date occurs, the first record is kept after stable chronological sorting. Equal readings on distinct dates are retained.
- **Types and ordering:** The index is validated as a DatetimeIndex, sorted chronologically, and the measurement is explicitly numeric. The cleaned output contains 2,284 rows, zero missing values, and zero duplicate dates for this source release.
- **Coverage:** The record starts in March 1958 and ends on 2001-12-29. Annual endpoint groups therefore do not have exactly equal full-calendar coverage.

## Exploratory Data Analysis

The cleaned series has mean 339.652 ppm, median 337.700 ppm, standard deviation 17.104 ppm, minimum 313.000 ppm, and maximum 373.900 ppm. Its fitted straight-line trend is 1.335 ppm per year (R² = 0.974); this is descriptive and does not establish causality. The available annual means rise from 315.188 ppm in 1958 to 370.865 ppm in 2001, a 55.678 ppm difference between endpoint groups. The 1958 group is partial because the series begins in March; annual groups use available observations.

The figures in `visualizations/` show:

1. **Missing values:** Annual counts of source readings absent before cleaning.
2. **Time series:** The complete cleaned weekly series and original observed points, making the long-term pattern, recurring oscillation, and interpolated stretches visible.
3. **Annual mean:** Yearly aggregation that emphasizes the long-term direction while reducing within-year variation.
4. **Distribution:** Histogram and density estimate of pooled weekly measurements; the pooled shape combines multiple decades and is not a stationary snapshot.
5. **Monthly pattern:** Calendar-month means pooled across years to show the average seasonal profile.

The pooled monthly means range by 5.480 ppm: October has the lowest mean and May the highest. Pooling years blends recurring seasonal shape with the long-term trend.

## Key Findings

- The source has 2,284 observations over 1958-03-29 to 2001-12-29, with 59 missing measurements and no duplicate dates.
- Time interpolation filled the 59 missing interior readings; the cleaned dataset has 2,284 rows and no missing values.
- The fitted linear trend is 1.335 ppm/year (R² = 0.974), a descriptive association over time rather than a causal result.
- Annual endpoint means differ by 55.678 ppm between 1958 and 2001.
- Monthly mean concentrations vary by 5.480 ppm across calendar months (lowest in October, highest in May).
- The standard deviation of cleaned weekly values is 17.104 ppm across the full multi-decade record.

All numbers above are generated from the Statsmodels dataset by `src/analysis.py` and recorded in `data/analysis_summary.json`.

## Limitations

This is one monitoring site and does not represent every location or atmospheric process. Interpolation smooths missing periods and estimates rather than observes values. Annual/monthly aggregation hides weekly behavior; pooling over a long-term trend affects distribution and month-of-year summaries. The first annual group is partial because observations begin in March 1958, while the final group ends on December 29. The linear trend is not a causal model and does not separately model seasonal components.

## How to Run

From the repository root:

```bash
python -m pip install -r requirements.txt
python src/analysis.py
```

To execute the notebook from start to finish:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/Week_1_CO2_EDA.ipynb
```

Or open `notebooks/Week_1_CO2_EDA.ipynb` in Jupyter and run all cells. The script downloads/loads the dataset through Statsmodels and recreates both CSV files, all figures, the summary JSON, and DOCX report.

## Reproducibility

Install dependencies from `requirements.txt`, then run the script from the project root. It uses the Statsmodels dataset loader as the source of truth and writes derived outputs to fixed project-relative paths. The raw CSV preserves source missing values; the cleaned CSV and `analysis_summary.json` are regenerated from that acquisition. The notebook calls the same analysis functions rather than maintaining a separate cleaning implementation. Package versions are not pinned, so exact rendering can vary slightly with library versions; the analysis method and source are explicit.
