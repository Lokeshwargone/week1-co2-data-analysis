"""Reproducible acquisition, cleaning, EDA, figures, and DOCX reporting for CO2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_URL = "https://www.statsmodels.org/devel/datasets/generated/co2.html"
FIGURE_NAMES = {
    "missing": "01_missing_values.png",
    "time_series": "02_co2_time_series.png",
    "annual": "03_annual_mean.png",
    "distribution": "04_distribution.png",
    "monthly": "05_monthly_pattern.png",
}


def acquire_dataset() -> pd.DataFrame:
    """Load the public Statsmodels CO2 series without altering missing values."""
    frame = sm.datasets.co2.load_pandas().data.copy()
    frame.index.name = "date"
    frame.columns = ["co2"]
    return frame


def clean_dataset(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate dates, deduplicate by date, and interpolate interior time gaps."""
    original_rows = len(raw)
    original_missing = int(raw["co2"].isna().sum())
    frame = raw.copy()
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index, errors="coerce"), name="date")
    if frame.index.isna().any():
        raise ValueError("The source contains dates that cannot be parsed.")
    frame["co2"] = pd.to_numeric(frame["co2"], errors="coerce")
    frame = frame.sort_index(kind="stable")
    duplicate_dates = int(frame.index.duplicated(keep="first").sum())
    # Duplicate observations are defined by date, not by repeated CO2 values.
    frame = frame.loc[~frame.index.duplicated(keep="first")].copy()
    frame["co2"] = frame["co2"].interpolate(method="time", limit_area="inside")
    remaining_missing = int(frame["co2"].isna().sum())
    if remaining_missing:
        raise ValueError(
            f"Time interpolation left {remaining_missing} missing values; "
            "inspect edge gaps before choosing an extrapolation policy."
        )
    details = {
        "raw_rows": original_rows,
        "raw_missing": original_missing,
        "duplicate_dates_removed": duplicate_dates,
        "clean_rows": len(frame),
        "clean_missing": remaining_missing,
        "raw_start": raw.index.min(),
        "raw_end": raw.index.max(),
        "clean_start": frame.index.min(),
        "clean_end": frame.index.max(),
    }
    return frame, details


def calculate_statistics(clean: pd.DataFrame) -> dict[str, Any]:
    values = clean["co2"]
    annual = values.resample("YS").mean().dropna()
    monthly = values.groupby(clean.index.month).mean().reindex(range(1, 13))
    elapsed_years = np.asarray((clean.index - clean.index[0]).days, dtype=float) / 365.2425
    slope, intercept = np.polyfit(elapsed_years, values.to_numpy(), 1)
    predicted = slope * elapsed_years + intercept
    residual_sum = float(np.square(values.to_numpy() - predicted).sum())
    total_sum = float(np.square(values.to_numpy() - values.mean()).sum())
    r_squared = 1 - residual_sum / total_sum if total_sum else float("nan")
    descriptive = values.describe(percentiles=[0.25, 0.5, 0.75])
    return {
        "descriptive": {key: float(value) for key, value in descriptive.items()},
        "annual_mean": {str(index.year): float(value) for index, value in annual.items()},
        "monthly_mean": {str(month): float(value) for month, value in monthly.items()},
        "trend_ppm_per_year": float(slope),
        "trend_r_squared": float(r_squared),
        "annual_first_year": int(annual.index[0].year),
        "annual_last_year": int(annual.index[-1].year),
        "annual_first_mean": float(annual.iloc[0]),
        "annual_last_mean": float(annual.iloc[-1]),
        "annual_mean_change": float(annual.iloc[-1] - annual.iloc[0]),
        "monthly_min_month": int(monthly.idxmin()),
        "monthly_max_month": int(monthly.idxmax()),
        "monthly_range": float(monthly.max() - monthly.min()),
        "annual_series": annual,
        "monthly_series": monthly,
    }


def create_visualizations(
    raw: pd.DataFrame, clean: pd.DataFrame, output_dir: Path
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook", palette="deep")
    paths = {key: output_dir / name for key, name in FIGURE_NAMES.items()}

    missing_by_year = raw["co2"].isna().resample("YS").sum()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar(missing_by_year.index, missing_by_year.values, width=300, color="#cf6a3c")
    ax.set(title="Missing Weekly CO₂ Observations Before Cleaning", xlabel="Year", ylabel="Missing observations (count)")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(paths["missing"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.plot(clean.index, clean["co2"], color="#216b72", linewidth=1.1, label="Cleaned weekly series")
    observed = raw["co2"].dropna()
    ax.scatter(observed.index, observed, s=5, color="#173f5f", alpha=0.3, label="Observed values", zorder=2)
    ax.set(title="Mauna Loa Weekly Atmospheric CO₂", xlabel="Date", ylabel="CO₂ concentration (ppm)")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths["time_series"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    annual = clean["co2"].resample("YS").mean().dropna()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(annual.index, annual.values, color="#c75b39", linewidth=2, marker="o", markersize=3)
    ax.set(title="Annual Mean Atmospheric CO₂", xlabel="Year", ylabel="Annual mean CO₂ (ppm)")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(paths["annual"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    sns.histplot(clean["co2"], bins=35, kde=True, color="#438b70", edgecolor="white", ax=ax)
    ax.set(title="Distribution of Weekly CO₂ Measurements", xlabel="CO₂ concentration (ppm)", ylabel="Number of weekly observations")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths["distribution"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    monthly = clean.groupby(clean.index.month)["co2"].mean()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(month_names, monthly.reindex(range(1, 13)).values, color="#536da6", linewidth=2, marker="o")
    ax.set(title="Average CO₂ by Calendar Month", xlabel="Calendar month", ylabel="Mean CO₂ concentration (ppm)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(paths["monthly"], dpi=180, bbox_inches="tight")
    plt.close(fig)
    return paths


def _add_table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1"
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text
    for row in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text


def _add_code(document: Document, code: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(code)
    run.font.name = "Consolas"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(45, 55, 65)


def create_report(
    details: dict[str, Any], stats: dict[str, Any], raw: pd.DataFrame,
    clean: pd.DataFrame, figures: dict[str, Path], report_path: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(6)
    for style_name in ("Heading 1", "Heading 2"):
        doc.styles[style_name].font.name = "Calibri"
        doc.styles[style_name].font.color.rgb = RGBColor(29, 79, 88)

    cover = doc.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cover.paragraph_format.space_before = Pt(90)
    title = cover.add_run("Data Acquisition, Cleaning and Exploratory Data\nAnalysis of Mauna Loa Atmospheric CO₂ Data")
    title.bold = True
    title.font.size = Pt(24)
    title.font.color.rgb = RGBColor(29, 79, 88)
    doc.add_paragraph("", style="Normal")
    for line in (
        "Student: Lokeshwar Reddy", "Branch: CSE (AI & ML)", "Institution: VBIT",
        "Internship: YUVA Intern", "Task: Week 1 — Data Acquisition, Cleaning and Exploratory Analysis",
        "Date: 30 September 2026",
    ):
        para = doc.add_paragraph(line)
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "This project acquires the public Mauna Loa atmospheric CO₂ series, validates and cleans its time index and measurements, and uses descriptive analysis and visualizations to characterize its temporal behavior. All reported values are computed from the Statsmodels dataset during the reproducible run."
    )
    doc.add_heading("2. Dataset Selection", level=1)
    doc.add_paragraph("The selected dataset is a regularly sampled weekly series of atmospheric carbon dioxide concentration. The measurements are expressed in parts per million (ppm).")
    doc.add_heading("3. Dataset Source", level=1)
    doc.add_paragraph("Statsmodels public dataset interface: statsmodels.datasets.co2. Documentation: " + DATASET_URL)
    doc.add_heading("4. Data Acquisition Method", level=1)
    doc.add_paragraph("The source was loaded directly with statsmodels.datasets.co2.load_pandas().data.copy(). The unmodified measurements, including their original missing entries, were saved as data/co2_raw_acquired.csv.")
    doc.add_heading("5. Initial Data Inspection", level=1)
    raw_dates = pd.DatetimeIndex(raw.index)
    _add_table(doc, ["Property", "Raw dataset"], [
        ["Rows × columns", f"{len(raw)} × {raw.shape[1]}"],
        ["Date range", f"{raw_dates.min():%Y-%m-%d} to {raw_dates.max():%Y-%m-%d}"],
        ["Column / source dtype", f"{raw.columns[0]} / {raw.dtypes.iloc[0]}"],
        ["Missing CO₂ observations", str(int(raw["co2"].isna().sum()))],
        ["Duplicate date records", str(int(raw.index.duplicated().sum()))],
    ])
    doc.add_paragraph("Raw descriptive statistics (pandas excludes missing values):")
    raw_desc = raw["co2"].describe(percentiles=[0.25, 0.5, 0.75])
    _add_table(doc, ["Statistic", "Value"], [[k, f"{v:.4f}"] for k, v in raw_desc.items()])

    doc.add_heading("6. Data Cleaning", level=1)
    doc.add_heading("6.1 Missing Values", level=2)
    doc.add_paragraph(
        f"WHAT: {details['raw_missing']} missing CO₂ values were identified in the {details['raw_rows']}-row source. Interior gaps were filled with pandas time-based interpolation. WHY: observations are ordered in time, so this estimates a missing point using nearby values and their elapsed time; a global mean would flatten local behavior and ignore chronology. WHAT CHANGED: {details['raw_missing']} missing values were filled; {details['clean_missing']} remain. The interpolation is an estimate, not a newly observed measurement."
    )
    doc.add_heading("6.2 Duplicate Records", level=2)
    doc.add_paragraph(
        f"Duplicate dates were checked as duplicate observations. {details['duplicate_dates_removed']} duplicate date rows were removed (keep first, after chronological sorting). Equal CO₂ readings on different dates were retained because repeated values do not identify duplicate records."
    )
    doc.add_heading("6.3 Data Type Validation", level=2)
    doc.add_paragraph("The index was explicitly converted and validated as a DatetimeIndex, and CO₂ was passed through pandas.to_numeric(..., errors='coerce'). Invalid numeric entries would therefore be treated as missing and included in the subsequent gap handling.")
    doc.add_heading("6.4 Time-Series Ordering", level=2)
    doc.add_paragraph("Observations were sorted chronologically before duplicate-date handling and interpolation, ensuring that the time-based operation follows the measurement sequence.")
    doc.add_heading("6.5 Cleaning Validation", level=2)
    _add_table(doc, ["Validation", "Result"], [
        ["Final rows", str(details["clean_rows"])],
        ["Final date range", f"{details['clean_start']:%Y-%m-%d} to {details['clean_end']:%Y-%m-%d}"],
        ["Missing CO₂ values after cleaning", str(details["clean_missing"])],
        ["Duplicate dates after cleaning", str(int(clean.index.duplicated().sum()))],
        ["Index / value dtype", f"{type(clean.index).__name__} / {clean['co2'].dtype}"],
    ])

    doc.add_heading("7. Exploratory Data Analysis", level=1)
    doc.add_heading("7.1 Descriptive Statistics", level=2)
    desc = stats["descriptive"]
    key_order = ["count", "mean", "50%", "std", "min", "25%", "75%", "max"]
    stat_labels = {"50%": "median (50%)"}
    _add_table(doc, ["Statistic", "CO₂ (ppm)"], [[stat_labels.get(k, k), f"{desc[k]:,.3f}"] for k in key_order])
    doc.add_paragraph("The count includes interpolated values; summary statistics describe the cleaned series and should be interpreted with that in mind.")
    doc.add_heading("7.2 CO₂ Time-Series Trend", level=2)
    doc.add_paragraph(f"An ordinary least-squares straight-line fit across elapsed time estimates a trend of {stats['trend_ppm_per_year']:.3f} ppm per year (R² = {stats['trend_r_squared']:.3f}). This is a descriptive association over this period, not evidence of causation, and a linear fit does not represent all seasonal or nonlinear variation.")
    doc.add_heading("7.3 Annual Mean Analysis", level=2)
    doc.add_paragraph(f"The annual mean increased from {stats['annual_first_mean']:.2f} ppm in {stats['annual_first_year']} to {stats['annual_last_mean']:.2f} ppm in {stats['annual_last_year']}, a difference of {stats['annual_mean_change']:.2f} ppm across the available endpoints. The 1958 group is partial because observations begin in March, and the final group ends on December 29; annual endpoint means reflect the available weeks rather than identical full-calendar coverage. Annual aggregation reduces within-year seasonal fluctuations.")
    doc.add_heading("7.4 Distribution Analysis", level=2)
    doc.add_paragraph(f"Across the cleaned observations, the median is {desc['50%']:.2f} ppm and the interquartile range is {desc['75%'] - desc['25%']:.2f} ppm. The histogram combines multiple decades, so its shape reflects both long-term change and seasonal variability rather than a stationary single-period distribution.")
    doc.add_heading("7.5 Seasonal Analysis", level=2)
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    doc.add_paragraph(f"The calendar-month means range by {stats['monthly_range']:.2f} ppm, from {month_names[stats['monthly_min_month'] - 1]} to {month_names[stats['monthly_max_month'] - 1]}. These means pool years with different background concentrations; they summarize recurring seasonal shape but are not seasonally adjusted estimates.")

    doc.add_heading("8. Visualizations", level=1)
    figure_info = [
        ("missing", "Figure 1. Missing weekly observations before cleaning", "Annual counts locate when source CO₂ readings are absent. Missing observations are not the same as duplicate dates; only missing measurement values are visualized."),
        ("time_series", "Figure 2. Complete weekly CO₂ time series", "The continuous line shows the cleaned series and points identify original observed values. The sustained upward pattern and repeating short-term oscillations are visible; interpolated points should not be mistaken for direct observations."),
        ("annual", "Figure 3. Annual mean CO₂", "Annual averaging emphasizes the long-term direction while reducing the within-year cycle. The observed increase is descriptive and does not establish cause."),
        ("distribution", "Figure 4. Distribution of weekly CO₂ measurements", "The histogram and density estimate summarize the pooled values. Because the time series trends over decades, this pooled distribution is not a snapshot of one stable population."),
        ("monthly", "Figure 5. Average CO₂ by calendar month", "Month-of-year means reveal the average seasonal profile across the whole record. Pooling years may blend seasonal behavior with the long-term trend."),
    ]
    for key, caption, explanation in figure_info:
        doc.add_paragraph(caption, style="Caption")
        doc.add_picture(str(figures[key]), width=Inches(6.25))
        doc.add_paragraph(explanation)

    doc.add_heading("9. Key Insights", level=1)
    insight_lines = [
        f"The cleaned record contains {details['clean_rows']} weekly observations from {details['clean_start']:%Y-%m-%d} through {details['clean_end']:%Y-%m-%d}.",
        f"The source had {details['raw_missing']} missing measurement values; time interpolation filled the interior gaps, leaving {details['clean_missing']} missing values.",
        f"The fitted linear trend is {stats['trend_ppm_per_year']:.3f} ppm per year across the complete observed period; it summarizes association over time, not causation.",
        f"The annual endpoint means differ by {stats['annual_mean_change']:.2f} ppm ({stats['annual_first_year']} to {stats['annual_last_year']}).",
        f"Calendar-month averages span {stats['monthly_range']:.2f} ppm from the lowest-mean month to the highest-mean month.",
        f"The cleaned distribution has a mean of {desc['mean']:.2f} ppm, median {desc['50%']:.2f} ppm, and standard deviation {desc['std']:.2f} ppm.",
    ]
    for insight in insight_lines:
        doc.add_paragraph(insight, style="List Bullet")
    doc.add_heading("10. Limitations", level=1)
    doc.add_paragraph("This is one monitoring record at Mauna Loa and should not be treated as a complete representation of every location or source of atmospheric variation. Interpolated values are estimates that can smooth short-lived fluctuations. The first calendar-year group is partial (the series begins in March 1958), and the final group ends on December 29, so endpoint annual means do not have exactly equal calendar coverage. Aggregated annual and calendar-month means hide some weekly structure, and the pooled histogram combines a changing series. The straight-line trend is descriptive, omits explicit seasonal terms, and does not identify causation.")
    doc.add_heading("11. Future Work", level=1)
    doc.add_paragraph("Possible extensions include comparing this series with other monitoring sites, modeling trend and seasonal components separately, quantifying uncertainty around fitted trends, and testing sensitivity to excluding rather than interpolating missing observations.")
    doc.add_heading("12. Conclusion", level=1)
    doc.add_paragraph(f"The source data were acquired reproducibly, checked for date and numeric validity, cleaned with time-aware interpolation, and summarized with five complementary figures. The observed series rises over the sampled decades while showing recurring within-year variation; these are descriptive findings from the dataset, not causal conclusions.")
    doc.add_heading("13. Code Summary", level=1)
    doc.add_paragraph("The reusable implementation in src/analysis.py performs acquisition, validation, cleaning, statistics, visualization, CSV export, and DOCX generation. The core operations are:")
    _add_code(doc, "raw = sm.datasets.co2.load_pandas().data.copy()\nclean['co2'] = pd.to_numeric(clean['co2'], errors='coerce')\nclean['co2'] = clean['co2'].interpolate(method='time', limit_area='inside')")
    doc.add_heading("14. Dataset Citation", level=1)
    doc.add_paragraph("Statsmodels Developers. CO2 dataset (statsmodels.datasets.co2). Statsmodels documentation. " + DATASET_URL)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("YUVA Intern | Week 1 | Mauna Loa CO₂ EDA")
    doc.save(report_path)


def run_analysis(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    project_root = Path(project_root)
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw = acquire_dataset()
    raw.to_csv(data_dir / "co2_raw_acquired.csv", index_label="date")
    clean, details = clean_dataset(raw)
    clean.to_csv(data_dir / "co2_cleaned.csv", index_label="date", date_format="%Y-%m-%d")
    stats = calculate_statistics(clean)
    figures = create_visualizations(raw, clean, project_root / "visualizations")
    create_report(details, stats, raw, clean, figures, project_root / "report" / "Week_1_Data_Acquisition_Cleaning_EDA.docx")
    serializable = {key: value for key, value in stats.items() if not key.endswith("_series")}
    summary = {
        "source": DATASET_URL,
        "raw_shape": [len(raw), raw.shape[1]],
        "raw_columns": list(raw.columns),
        "raw_dtypes": {str(key): str(value) for key, value in raw.dtypes.items()},
        "raw_missing_by_column": {str(key): int(value) for key, value in raw.isna().sum().items()},
        "raw_duplicate_dates": int(raw.index.duplicated().sum()),
        "raw_date_range": [str(raw.index.min().date()), str(raw.index.max().date())],
        "cleaning": {key: (value.isoformat() if isinstance(value, pd.Timestamp) else value) for key, value in details.items()},
        "statistics": serializable,
        "visualizations": {key: str(path.relative_to(project_root)) for key, path in figures.items()},
    }
    (project_root / "data" / "analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return {"raw": raw, "clean": clean, "details": details, "statistics": stats, "figures": figures, "summary": summary}


def main() -> None:
    result = run_analysis()
    details = result["details"]
    stats = result["statistics"]
    print(f"Raw rows: {details['raw_rows']}; missing values: {details['raw_missing']}")
    print(f"Clean rows: {details['clean_rows']}; remaining missing: {details['clean_missing']}")
    print(f"Date range: {details['clean_start']:%Y-%m-%d} to {details['clean_end']:%Y-%m-%d}")
    print(f"Linear trend: {stats['trend_ppm_per_year']:.3f} ppm/year (R²={stats['trend_r_squared']:.3f})")
    print("Generated 5 visualizations, raw/clean CSVs, analysis_summary.json, and DOCX report.")


if __name__ == "__main__":
    main()
