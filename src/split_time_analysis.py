from datetime import datetime, time, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd

from project_paths import DIST_DIR, LEGACY_DATA_DIR, ensure_output_directories

EXCEL_FILE = LEGACY_DATA_DIR / "IM 70.3 Zell am See Result History.xlsx"
OUTPUT_PLOT = DIST_DIR / "split_time_overview_0425_0430.png"
OUTPUT_CSV = DIST_DIR / "split_time_overview_0425_0430.csv"

LOWER_LIMIT = timedelta(hours=4, minutes=25)
UPPER_LIMIT = timedelta(hours=4, minutes=30)
SWIM_DISTANCE_METERS = 1900
BIKE_DISTANCE_KM = 90
RUN_DISTANCE_KM = 21.1
SPLIT_COLUMNS = {
    "Swim": "Swim Time",
    "T1": "Transition 1 Time",
    "Bike": "Bike Time",
    "T2": "Transition 2 Time",
    "Run": "Run Time",
}
COLORS = {
    "Swim": "#277DA1",
    "T1": "#F9C74F",
    "Bike": "#00FDB1",
    "T2": "#F9844A",
    "Run": "#F94144",
}


def parse_duration(value):
    if pd.isna(value):
        return None
    if isinstance(value, timedelta):
        return value
    if isinstance(value, time):
        return timedelta(
            hours=value.hour,
            minutes=value.minute,
            seconds=value.second,
            microseconds=value.microsecond,
        )
    if isinstance(value, datetime):
        return value - datetime.combine(value.date(), time())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return timedelta(seconds=float(value) * 86400)
    try:
        duration = pd.to_timedelta(value)
        return None if pd.isna(duration) else duration
    except (TypeError, ValueError):
        return None


def format_duration(duration):
    total_seconds = round(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_minutes_as_time(minutes, _position=None):
    total_minutes = round(minutes)
    hours, remaining_minutes = divmod(total_minutes, 60)
    return f"{hours}:{remaining_minutes:02d}"


def format_pace(seconds):
    total_seconds = round(seconds)
    minutes, remaining_seconds = divmod(total_seconds, 60)
    return f"{minutes}:{remaining_seconds:02d}"


def pace_or_speed(split_name, duration):
    seconds = duration.total_seconds()
    if split_name == "Swim":
        return f"{format_pace(seconds / (SWIM_DISTANCE_METERS / 100))}/100 m"
    if split_name == "Bike":
        speed = BIKE_DISTANCE_KM / (seconds / 3600)
        return f"{speed:.1f} km/h"
    if split_name == "Run":
        return f"{format_pace(seconds / RUN_DISTANCE_KM)}/km"
    return "–"


def format_time_with_metric(split_name, duration):
    metric = pace_or_speed(split_name, duration)
    if metric == "–":
        return format_duration(duration)
    return f"{format_duration(duration)} ({metric})"


def load_finishers():
    required_columns = [
        "Bib",
        "Name",
        "Gender",
        "Division",
        "Overall Time",
        "Finish",
        *SPLIT_COLUMNS.values(),
    ]
    finishers = []

    workbook = pd.ExcelFile(EXCEL_FILE)
    for sheet_name in sorted(workbook.sheet_names):
        frame = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        missing_columns = set(required_columns) - set(frame.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Sheet {sheet_name} is missing columns: {missing}")

        frame = frame[required_columns].copy()
        duration_columns = ["Overall Time", *SPLIT_COLUMNS.values()]
        for column in duration_columns:
            frame[column] = frame[column].map(parse_duration)

        in_time_window = frame["Overall Time"].map(
            lambda duration: duration is not None
            and LOWER_LIMIT <= duration <= UPPER_LIMIT
        )
        frame = frame.loc[in_time_window & frame["Finish"].eq("FIN")].copy()
        frame.insert(0, "Year", sheet_name)
        finishers.append(frame)

    if not finishers:
        raise RuntimeError("The workbook contains no yearly result sheets.")

    result = pd.concat(finishers, ignore_index=True)
    result = result.dropna(subset=["Overall Time", *SPLIT_COLUMNS.values()])
    result = result.sort_values(["Year", "Overall Time", "Name"]).reset_index(drop=True)
    if result.empty:
        raise RuntimeError("No finishers found from 04:25:00 through 04:30:00.")
    return result


def export_csv(finishers):
    exported = finishers.copy()
    exported["Swim Pace (min:sec/100m)"] = finishers["Swim Time"].map(
        lambda duration: format_pace(
            duration.total_seconds() / (SWIM_DISTANCE_METERS / 100)
        )
    )
    exported["Bike Speed (km/h)"] = finishers["Bike Time"].map(
        lambda duration: round(
            BIKE_DISTANCE_KM / (duration.total_seconds() / 3600), 1
        )
    )
    exported["Run Pace (min:sec/km)"] = finishers["Run Time"].map(
        lambda duration: format_pace(duration.total_seconds() / RUN_DISTANCE_KM)
    )
    duration_columns = ["Overall Time", *SPLIT_COLUMNS.values()]
    for column in duration_columns:
        exported[column] = exported[column].map(format_duration)
    exported.to_csv(OUTPUT_CSV, index=False)


def add_summary_table(axis, finishers):
    rows = []
    for split_name, column in SPLIT_COLUMNS.items():
        durations = finishers[column]
        durations = durations[durations.map(lambda value: value.total_seconds() > 0)]
        seconds = durations.map(lambda value: value.total_seconds())
        average = timedelta(seconds=seconds.mean())
        sigma = timedelta(seconds=seconds.std(ddof=0))
        minimum = min(durations)
        maximum = max(durations)
        average_metric = pace_or_speed(split_name, average)
        average_text = format_duration(average)
        if average_metric != "–":
            average_text = f"{average_text} ({average_metric})"
        rows.append(
            [
                split_name,
                f"{average_text} ± {format_duration(sigma)}",
                format_time_with_metric(split_name, minimum),
                format_time_with_metric(split_name, maximum),
            ]
        )

    axis.axis("off")
    table = axis.table(
        cellText=rows,
        colLabels=[
            "Split",
            "Average ± 1σ",
            "Minimum time (pace / speed)",
            "Maximum time (pace / speed)",
        ],
        cellLoc="center",
        colLoc="center",
        loc="center",
        colWidths=[0.10, 0.30, 0.26, 0.26],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.25)
    for (row, _column), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#E8ECEF")
            cell.set_text_props(weight="bold")
    axis.set_title(
        "Split-time summary (zero-duration placeholders excluded)",
        fontsize=11,
        pad=2,
    )


def add_stacked_bars(axis, finishers):
    positions = range(len(finishers))
    left = [0.0] * len(finishers)

    for split_name, column in SPLIT_COLUMNS.items():
        values = finishers[column].map(lambda duration: duration.total_seconds() / 60)
        axis.barh(
            positions,
            values,
            left=left,
            height=0.72,
            color=COLORS[split_name],
            label=split_name,
        )
        left = [start + value for start, value in zip(left, values)]

    labels = [
        f"{row.Year}  {row.Name} ({row.Division})"
        for row in finishers.itertuples(index=False)
    ]
    axis.set_yticks(list(positions), labels=labels, fontsize=7)
    axis.invert_yaxis()
    axis.set_xlim(0, 275)
    axis.xaxis.set_major_locator(MultipleLocator(30))
    axis.xaxis.set_minor_locator(MultipleLocator(10))
    axis.xaxis.set_major_formatter(FuncFormatter(format_minutes_as_time))
    axis.grid(axis="x", which="major", alpha=0.3)
    axis.grid(axis="x", which="minor", alpha=0.12)
    axis.set_axisbelow(True)


def main():
    finishers = load_finishers()
    export_csv(finishers)

    midpoint = (len(finishers) + 1) // 2
    groups = [finishers.iloc[:midpoint], finishers.iloc[midpoint:]]
    figure_height = max(14, 0.36 * max(len(group) for group in groups) + 2)
    figure = plt.figure(figsize=(18, figure_height), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, height_ratios=[1.4, 10])
    summary_axis = figure.add_subplot(grid[0, :])
    axes = [
        figure.add_subplot(grid[1, 0]),
        figure.add_subplot(grid[1, 1]),
    ]
    axes[1].sharex(axes[0])

    add_summary_table(summary_axis, finishers)

    for axis, group in zip(axes, groups):
        add_stacked_bars(axis, group)
        axis.set_xlabel("Cumulative race time (H:MM)")

    summary_axis.legend(
        handles=axes[0].get_legend_handles_labels()[0],
        labels=axes[0].get_legend_handles_labels()[1],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=5,
        frameon=False,
    )
    figure.suptitle(
        "IRONMAN 70.3 Zell am See Split Times: 04:25:00–04:30:00 Finishers",
        fontsize=16,
    )
    figure.text(
        0.5,
        0.005,
        "Inclusive time window; 2022 source data records T1 and T2 as 00:00:00.",
        ha="center",
        fontsize=8,
        color="#555555",
    )
    figure.savefig(OUTPUT_PLOT, dpi=180, bbox_inches="tight")
    plt.close(figure)

    counts = finishers.groupby("Year").size().to_dict()
    count_summary = ", ".join(f"{year}: {count}" for year, count in counts.items())
    print(f"Found {len(finishers)} finishers ({count_summary}).")
    print(f"Saved plot to {OUTPUT_PLOT.resolve()}")
    print(f"Saved data to {OUTPUT_CSV.resolve()}")


if __name__ == "__main__":
    ensure_output_directories()
    main()