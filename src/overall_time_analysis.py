import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
from datetime import datetime, time, timedelta
from math import ceil
from pathlib import Path

from project_paths import DIST_DIR, LEGACY_DATA_DIR, ensure_output_directories


EXCEL_FILE = LEGACY_DATA_DIR / 'ironmanaustria_updatedRules_2.xlsx'
OUTPUT_FILE = DIST_DIR / 'overall_finishing_time_stats.png'
TEN_MINUTES_IN_HOURS = 10 / 60
THIRTY_MINUTES_IN_HOURS = 30 / 60


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
        td = pd.to_timedelta(value)
        if pd.isna(td):
            return None
        return td
    except Exception:
        return None


def format_duration(td):
    if td is None:
        return None
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def load_year_data(sheet_name):
    df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    df = df.dropna(how='all')
    if df.empty:
        return None
    if 'Overall Time' not in df.columns:
        raise ValueError(f"Sheet {sheet_name}: missing Overall Time column")

    df['finish_td'] = df['Overall Time'].apply(parse_duration)
    df = df.dropna(subset=['finish_td']).copy()
    df['finish_seconds'] = df['finish_td'].map(lambda td: td.total_seconds())
    return df


def sort_sheet_names(sheet_names):
    def key(name):
        try:
            return int(name)
        except Exception:
            return name
    return sorted(sheet_names, key=key)


def seconds_to_hours(seconds):
    return seconds / 3600.0 if seconds is not None else None


def format_hours_minutes(hours, _position=None):
    total_minutes = int(round(hours * 60))
    display_hours, minutes = divmod(total_minutes, 60)
    return f'{display_hours:02d}:{minutes:02d}'


def main():
    xls = pd.ExcelFile(EXCEL_FILE)
    sheets = [s for s in xls.sheet_names if s not in ('Kona Standards', 'Overview', 'Sub 9')]
    sheets = sort_sheet_names(sheets)

    stats = []
    hist_data = []

    for sheet in sheets:
        df = load_year_data(sheet)
        if df is None or df.empty:
            continue
        df = df.sort_values('finish_seconds').reset_index(drop=True)
        n = len(df)
        if n == 0:
            continue

        overall_mean = df['finish_seconds'].mean()
        overall_median = df['finish_seconds'].median()
        top20_count = ceil(n * 0.2)
        cutoff_top20pct = df.iloc[top20_count - 1]['finish_seconds']
        cutoff_top100 = df.iloc[min(99, n - 1)]['finish_seconds']
        cutoff_top20 = df.iloc[min(19, n - 1)]['finish_seconds']

        stats.append({
            'year': sheet,
            'finishers': n,
            'mean_sec': overall_mean,
            'median_sec': overall_median,
            'top20pct_cutoff_sec': cutoff_top20pct,
            'top100_cutoff_sec': cutoff_top100,
            'top20_cutoff_sec': cutoff_top20,
        })
        hist_data.append((sheet, df['finish_seconds'].values))

    if not stats:
        raise RuntimeError('No valid yearly finishing-time data found.')

    years = [item['year'] for item in stats]
    mean_hours = [seconds_to_hours(item['mean_sec']) for item in stats]
    median_hours = [seconds_to_hours(item['median_sec']) for item in stats]
    cutoff_20pct_hours = [seconds_to_hours(item['top20pct_cutoff_sec']) for item in stats]
    cutoff_100_hours = [seconds_to_hours(item['top100_cutoff_sec']) for item in stats]
    cutoff_20_hours = [seconds_to_hours(item['top20_cutoff_sec']) for item in stats]

    fig, axes = plt.subplots(3, 1, figsize=(14, 18), constrained_layout=True)

    time_formatter = FuncFormatter(format_hours_minutes)

    # Cumulative distribution by year
    ax = axes[0]
    hist_hours = [
        (year, [seconds_to_hours(seconds) for seconds in data])
        for year, data in hist_data
    ]
    for year, data in hist_hours:
        cumulative_percent = [100.0 * rank / len(data) for rank in range(1, len(data) + 1)]
        ax.step(
            data,
            cumulative_percent,
            where='post',
            linewidth=1.8,
            label=str(year),
        )
    ax.set_title('Cumulative Finishing Time Distribution by Year')
    ax.set_xlabel('Finishing Time (HH:MM)')
    ax.set_ylabel('Finishers completed (%)')
    ax.xaxis.set_major_formatter(time_formatter)
    ax.xaxis.set_major_locator(MultipleLocator(THIRTY_MINUTES_IN_HOURS))
    ax.xaxis.set_minor_locator(MultipleLocator(TEN_MINUTES_IN_HOURS))
    ax.set_ylim(0, 100)
    ax.legend(title='Year')
    ax.grid(True, alpha=0.35)
    ax.grid(which='minor', axis='x', alpha=0.12)

    # Average / median over years
    ax = axes[1]
    ax.plot(years, mean_hours, marker='o', label='Mean')
    ax.plot(years, median_hours, marker='s', label='Median')
    ax.set_title('Mean and Median Overall Finishing Time by Year')
    ax.set_xlabel('Year')
    ax.set_ylabel('Time (HH:MM)')
    ax.yaxis.set_major_formatter(time_formatter)
    ax.yaxis.set_major_locator(MultipleLocator(TEN_MINUTES_IN_HOURS))
    ax.legend()
    ax.grid(True, alpha=0.35)

    # Top cutoff times
    ax = axes[2]
    ax.plot(years, cutoff_20pct_hours, marker='o', label='Top 20% cutoff')
    ax.plot(years, cutoff_100_hours, marker='s', label='Top 100 cutoff')
    ax.plot(years, cutoff_20_hours, marker='^', label='Top 20 cutoff')
    ax.set_title('Top Finisher Cutoff Times Over Years')
    ax.set_xlabel('Year')
    ax.set_ylabel('Cutoff Time (HH:MM)')
    ax.yaxis.set_major_formatter(time_formatter)
    ax.yaxis.set_major_locator(MultipleLocator(TEN_MINUTES_IN_HOURS))
    ax.legend()
    ax.grid(True, alpha=0.35)

    fig.suptitle('Ironman Austria Overall Finishing Time Statistics', fontsize=18)

    fig.savefig(OUTPUT_FILE, dpi=150)
    print(f'Saved plot to {OUTPUT_FILE.resolve()}')


if __name__ == '__main__':
    ensure_output_directories()
    main()
