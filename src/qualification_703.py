from datetime import time, timedelta
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd

from project_paths import DIST_DIR, LEGACY_DATA_DIR, ensure_output_directories

EXCEL_FILE = LEGACY_DATA_DIR / 'IM 70.3 Zell am See Result History.xlsx'
OUTPUT_IMAGE = DIST_DIR / 'qualification_703_zell_am_see_summary.png'
OUTPUT_TARGETS = DIST_DIR / 'qualification_703_zell_am_see_targets.csv'
OUTPUT_PLOTS = DIST_DIR / 'qualification_703_zell_am_see_plots.png'
TOTAL_SLOTS = 50
SLOTS_PER_GENDER = 25
NON_AGE_GROUP_DIVISIONS = {
    'MPRO', 'FPRO', 'MPC', 'FPC', 'MPC/ID', 'FPC/ID',
    'MHC', 'FHC', 'MST', 'FST', 'MGUIDE', 'FGUIDE',
}

MEN_RATIOS = {
    'M18-24': 1.0000, 'M25-29': 0.9941, 'M30-34': 0.9708,
    'M35-39': 0.9540, 'M40-44': 0.9309, 'M45-49': 0.9020,
    'M50-54': 0.8871, 'M55-59': 0.8583, 'M60-64': 0.8215,
    'M65-69': 0.7669, 'M70-74': 0.7111, 'M75-79': 0.6431,
    'M80-84': 0.5153, 'M85-89': 0.5415,
}

WOMEN_RATIOS = {
    'F18-24': 0.9899, 'F25-29': 1.0000, 'F30-34': 0.9826,
    'F35-39': 0.9681, 'F40-44': 0.9452, 'F45-49': 0.9198,
    'F50-54': 0.9031, 'F55-59': 0.8747, 'F60-64': 0.8382,
    'F65-69': 0.7785, 'F70-74': 0.7348, 'F75-79': 0.6257,
}

# 2026 qualifying cycle table; reproduces every official Zell am See 2025
# age-graded "Qualifier Time" to the second.
MEN_RATIOS_2026 = {
    'M18-24': 1.0000, 'M25-29': 0.9929, 'M30-34': 0.9655,
    'M35-39': 0.9500, 'M40-44': 0.9262, 'M45-49': 0.8978,
    'M50-54': 0.8833, 'M55-59': 0.8565, 'M60-64': 0.8192,
    'M65-69': 0.7640, 'M70-74': 0.7119, 'M75-79': 0.6419,
    'M80-84': 0.5095, 'M85-89': 0.5402,
}

WOMEN_RATIOS_2026 = {
    'F18-24': 0.9921, 'F25-29': 1.0000, 'F30-34': 0.9828,
    'F35-39': 0.9658, 'F40-44': 0.9426, 'F45-49': 0.9192,
    'F50-54': 0.9016, 'F55-59': 0.8746, 'F60-64': 0.8391,
    'F65-69': 0.7775, 'F70-74': 0.7348, 'F75-79': 0.6234,
}

# IRONMAN 70.3 Standard by qualifying cycle (ironman.com/about/age-group-qualification).
STANDARDS = {
    '2026': (MEN_RATIOS_2026, WOMEN_RATIOS_2026),
    '2027': (MEN_RATIOS, WOMEN_RATIOS),
}
CURRENT_CYCLE = '2027'


def get_ratio(gender, division, cycle=CURRENT_CYCLE):
    men, women = STANDARDS[cycle]
    if gender == 'Male':
        return men.get(division)
    if gender == 'Female':
        return women.get(division)
    return None


def official_check(frame, winners, pool, performance_slots):
    """Compare the strict model with the official results' Qualified flags."""
    if 'Qualified' not in frame.columns:
        return None
    predicted = set(winners.index) | set(pool['row_id'].head(max(performance_slots, 0)))
    official = set(frame.index[pd.to_numeric(frame['Qualified'], errors='coerce').eq(1)])
    return {
        'official': len(official),
        'predicted': len(predicted),
        'matched': len(predicted & official),
    }


def parse_time(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timedelta):
        return value
    if isinstance(value, time):
        return timedelta(
            hours=value.hour,
            minutes=value.minute,
            seconds=value.second,
            microseconds=value.microsecond,
        )
    if isinstance(value, pd.Timestamp):
        return pd.to_timedelta(value - value.normalize())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return timedelta(seconds=float(value) * 86400)
    try:
        parsed = pd.to_timedelta(value)
        return None if pd.isna(parsed) else parsed
    except (TypeError, ValueError):
        return None


def format_td(value):
    if value is None:
        return None
    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def get_cutoff(pool, slots, extra=0):
    index = slots + extra - 1
    if index < 0 or index >= len(pool):
        return None
    return pool.iloc[index]


def process_year(sheet_name):
    df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    return process_dataframe(sheet_name, df)


def process_dataframe(
    year, df, male_slots=SLOTS_PER_GENDER, female_slots=SLOTS_PER_GENDER,
    cycle=CURRENT_CYCLE,
):
    df = df.dropna(how='all')
    if df.empty:
        return None

    required_columns = {
        'Gender', 'Division', 'Overall Time', 'Age Group Rank'
    }
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ', '.join(sorted(missing_columns))
        raise ValueError(f'Year {year}: missing columns: {missing}')

    df['gender'] = df['Gender'].astype(str).str.strip().str.title()
    df['Division'] = df['Division'].astype(str).str.strip().str.upper()
    canonical = df['Division'].str.match(r'^[MF]\d{2}-\d{2}$', na=False)
    consistent = (
        df['gender'].eq('Male') & df['Division'].str.startswith('M')
    ) | (
        df['gender'].eq('Female') & df['Division'].str.startswith('F')
    )
    unsupported = df[
        ~(canonical & consistent)
        & ~df['Division'].isin(NON_AGE_GROUP_DIVISIONS)
    ]
    if not unsupported.empty:
        details = ', '.join(
            f'{gender}/{division} ({count})'
            for (gender, division), count in
            unsupported.fillna({'gender': 'missing', 'Division': 'missing'})
            .groupby(['gender', 'Division']).size().items()
        )
        warnings.warn(
            f'Year {year}: excluded rows with inconsistent or unsupported '
            f'gender/division values: {details}',
            stacklevel=2,
        )
    df = df[canonical & consistent].copy()

    eligible_starters = df
    if 'Finish' in eligible_starters.columns:
        eligible_starters = eligible_starters[
            ~eligible_starters['Finish'].astype(str).str.strip().str.upper().eq('DNS')
        ]
    starter_gender_counts = eligible_starters['gender'].value_counts()

    if 'Finish' in df.columns:
        df = df[df['Finish'].astype(str).str.strip().str.upper().eq('FIN')].copy()
    if df.empty:
        return None

    df['finish_td'] = df['Overall Time'].apply(parse_time)
    df = df.dropna(subset=['finish_td'])
    df = df[df['finish_td'] > timedelta(0)]
    df['Age Group Rank'] = pd.to_numeric(df['Age Group Rank'], errors='coerce')
    winners = (
        df[df['Age Group Rank'].eq(1)]
        .sort_values('finish_td')
        .drop_duplicates('Division')
    )

    male_auto = int(winners['gender'].eq('Male').sum())
    female_auto = int(winners['gender'].eq('Female').sum())
    male_performance_slots = male_slots - male_auto
    female_performance_slots = female_slots - female_auto
    if male_performance_slots < 0 or female_performance_slots < 0:
        raise ValueError(
            f'Year {year}: automatic slots exceed the per-gender allocation'
        )

    df['ratio'] = pd.Series(
        [
            get_ratio(gender, division, cycle)
            for gender, division in zip(df['gender'], df['Division'])
        ],
        index=df.index,
        dtype='float64',
    )
    missing_standard = df[df['ratio'].isna()]
    if not missing_standard.empty:
        details = ', '.join(
            f'{gender}/{division} ({count})'
            for (gender, division), count in
            missing_standard.groupby(['gender', 'Division']).size().items()
        )
        warnings.warn(
            f'Year {year}: excluded finishers from the performance pool '
            f'because the official age-group standard is TBD: {details}',
            stacklevel=2,
        )
    performance_df = df.dropna(subset=['ratio']).copy()
    performance_df['age_graded'] = (
        performance_df['finish_td'] * performance_df['ratio']
    )
    non_winners = performance_df.loc[
        ~performance_df.index.isin(winners.index)
    ].rename_axis('row_id').reset_index()
    male_pool = (
        non_winners[non_winners['gender'].eq('Male')]
        .sort_values('age_graded', kind='stable')
        .reset_index(drop=True)
    )
    female_pool = (
        non_winners[non_winners['gender'].eq('Female')]
        .sort_values('age_graded', kind='stable')
        .reset_index(drop=True)
    )

    male_cutoff = get_cutoff(male_pool, male_performance_slots)
    female_cutoff = get_cutoff(female_pool, female_performance_slots)
    male_rank_10 = get_cutoff(male_pool, male_performance_slots, 10)
    male_rank_20 = get_cutoff(male_pool, male_performance_slots, 20)
    male_rank_25 = get_cutoff(male_pool, male_performance_slots, 25)
    female_rank_10 = get_cutoff(female_pool, female_performance_slots, 10)
    female_rank_20 = get_cutoff(female_pool, female_performance_slots, 20)
    female_rank_25 = get_cutoff(female_pool, female_performance_slots, 25)

    def cutoff_time(row):
        return row['age_graded'] if row is not None else None

    def pool_entries(pool):
        return [
            (division, value.total_seconds())
            for division, value in zip(pool['Division'], pool['age_graded'])
        ]

    return {
        'year': year,
        'standard_cycle': cycle,
        'pools': {'male': pool_entries(male_pool), 'female': pool_entries(female_pool)},
        'winner_times': {
            division: value.total_seconds()
            for division, value in zip(winners['Division'], winners['finish_td'])
        },
        'automatic_divisions': {
            'male': sorted(winners.loc[winners['gender'].eq('Male'), 'Division']),
            'female': sorted(winners.loc[winners['gender'].eq('Female'), 'Division']),
        },
        'official_check': {
            'male': official_check(
                df[df['gender'].eq('Male')],
                winners[winners['gender'].eq('Male')],
                male_pool,
                male_performance_slots,
            ),
            'female': official_check(
                df[df['gender'].eq('Female')],
                winners[winners['gender'].eq('Female')],
                female_pool,
                female_performance_slots,
            ),
        },
        'male_finishers': int(df['gender'].eq('Male').sum()),
        'female_finishers': int(df['gender'].eq('Female').sum()),
        'male_starters': int(starter_gender_counts.get('Male', 0)),
        'female_starters': int(starter_gender_counts.get('Female', 0)),
        'male_auto': male_auto,
        'female_auto': female_auto,
        'male_performance_slots': male_performance_slots,
        'female_performance_slots': female_performance_slots,
        'male_cutoff_td': cutoff_time(male_cutoff),
        'female_cutoff_td': cutoff_time(female_cutoff),
        'male_cutoff': format_td(cutoff_time(male_cutoff)),
        'female_cutoff': format_td(cutoff_time(female_cutoff)),
        'male_rank_10_td': cutoff_time(male_rank_10),
        'male_rank_20_td': cutoff_time(male_rank_20),
        'male_rank_25_td': cutoff_time(male_rank_25),
        'female_rank_10_td': cutoff_time(female_rank_10),
        'female_rank_20_td': cutoff_time(female_rank_20),
        'female_rank_25_td': cutoff_time(female_rank_25),
        'male_rank_10': format_td(cutoff_time(male_rank_10)),
        'male_rank_20': format_td(cutoff_time(male_rank_20)),
        'male_rank_25': format_td(cutoff_time(male_rank_25)),
        'female_rank_10': format_td(cutoff_time(female_rank_10)),
        'female_rank_20': format_td(cutoff_time(female_rank_20)),
        'female_rank_25': format_td(cutoff_time(female_rank_25)),
    }


def build_target_rows(results):
    rows = []
    for result in results:
        men, women = STANDARDS[result.get('standard_cycle', CURRENT_CYCLE)]
        ratio_sets = (
            ('Male', men, 'male_cutoff_td'),
            ('Female', women, 'female_cutoff_td'),
        )
        for gender, ratios, cutoff_key in ratio_sets:
            age_graded_cutoff = result[cutoff_key]
            if age_graded_cutoff is None:
                continue
            for division, ratio in ratios.items():
                rows.append({
                    'Year': result['year'],
                    'Gender': gender,
                    'Division': division,
                    '70.3 ratio': ratio,
                    'Age-graded cutoff': format_td(age_graded_cutoff),
                    'Finish at or below': format_td(age_graded_cutoff / ratio),
                    'Scenario': 'Strict estimate: all AG winners accept; no roll-down',
                    'Gender allocation': 'Equal male/female quota',
                })
    return rows


def build_summary(results):
    columns = [
        'Year', 'M finishers', 'F finishers',
        'M auto', 'F auto',
        'M perf', 'F perf',
        'M AG cutoff', 'F AG cutoff',
        'M rank +10', 'F rank +10',
        'M rank +20', 'F rank +20',
        'M rank +25', 'F rank +25',
    ]
    table_rows = [
        [
            result['year'], result['male_finishers'], result['female_finishers'],
            result['male_auto'], result['female_auto'],
            result['male_performance_slots'], result['female_performance_slots'],
            result['male_cutoff'] or '-', result['female_cutoff'] or '-',
            result['male_rank_10'] or '-', result['female_rank_10'] or '-',
            result['male_rank_20'] or '-', result['female_rank_20'] or '-',
            result['male_rank_25'] or '-', result['female_rank_25'] or '-',
        ]
        for result in results
    ]

    m30_34_ratio = MEN_RATIOS['M30-34']
    m30_34_columns = [
        'Year', 'M30-34 cutoff', 'M30-34 rank +10',
        'M30-34 rank +20', 'M30-34 rank +25',
    ]
    m30_34_rows = [
        [
            result['year'],
            format_td(result['male_cutoff_td'] / m30_34_ratio),
            format_td(result['male_rank_10_td'] / m30_34_ratio),
            format_td(result['male_rank_20_td'] / m30_34_ratio),
            format_td(result['male_rank_25_td'] / m30_34_ratio),
        ]
        for result in results
    ]

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(22, 0.95 * len(table_rows) + 4.0),
        gridspec_kw={'height_ratios': [1.5, 1]},
    )
    for axis in axes:
        axis.axis('off')

    table = axes[0].table(
        cellText=table_rows,
        colLabels=columns,
        cellLoc='center',
        loc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)
    axes[0].set_title(
        'Strict IRONMAN 70.3 Zell am See Qualification Estimate\n'
        f'{TOTAL_SLOTS} total slots: {SLOTS_PER_GENDER} men / '
        f'{SLOTS_PER_GENDER} women; all age-group winners accept; no roll-down',
        pad=20,
    )

    m30_34_table = axes[1].table(
        cellText=m30_34_rows,
        colLabels=m30_34_columns,
        cellLoc='center',
        loc='center',
    )
    m30_34_table.auto_set_font_size(False)
    m30_34_table.set_fontsize(9)
    m30_34_table.scale(1, 1.5)
    axes[1].set_title(
        f'M30-34 Raw Finish-Time Targets — 70.3 Ratio: {m30_34_ratio:.4f}',
        pad=12,
    )

    figure.tight_layout()
    figure.savefig(OUTPUT_IMAGE, dpi=150, bbox_inches='tight')
    plt.close(figure)


def format_hours_minutes(hours, _position=None):
    total_minutes = int(round(hours * 60))
    display_hours, minutes = divmod(total_minutes, 60)
    return f'{display_hours:02d}:{minutes:02d}'


def build_plots(results, target_rows):
    time_formatter = FuncFormatter(format_hours_minutes)
    ten_minutes = 10 / 60
    years = [result['year'] for result in results]

    figure, axes = plt.subplots(3, 1, figsize=(16, 18), constrained_layout=True)

    axis = axes[0]
    rank_scenarios = (
        ('Cutoff', 'male_cutoff_td', 'female_cutoff_td', '-', 2.4),
        ('Rank +10', 'male_rank_10_td', 'female_rank_10_td', '--', 1.8),
        ('Rank +20', 'male_rank_20_td', 'female_rank_20_td', '-.', 1.8),
        ('Rank +25', 'male_rank_25_td', 'female_rank_25_td', ':', 2.0),
    )
    m30_34_ratio = MEN_RATIOS['M30-34']
    for label, male_key, female_key, line_style, line_width in rank_scenarios:
        male_hours = [
            result[male_key].total_seconds() / 3600 for result in results
        ]
        axis.plot(
            years,
            male_hours,
            color='tab:blue',
            linestyle=line_style,
            marker='o',
            linewidth=line_width,
            label=f'Men {label}',
        )
        axis.plot(
            years,
            [result[female_key].total_seconds() / 3600 for result in results],
            color='tab:orange',
            linestyle=line_style,
            marker='s',
            linewidth=line_width,
            label=f'Women {label}',
        )
        axis.plot(
            years,
            [hours / m30_34_ratio for hours in male_hours],
            color='tab:green',
            linestyle=line_style,
            marker='^',
            linewidth=line_width,
            label=f'M30-34 raw {label}',
        )
    axis.set_title('Qualification Cutoffs by Year and Rank Scenario')
    axis.set_xlabel('Year')
    axis.set_ylabel('Qualification time (HH:MM)')
    axis.yaxis.set_major_formatter(time_formatter)
    axis.yaxis.set_major_locator(MultipleLocator(ten_minutes))
    axis.grid(True, alpha=0.35)
    axis.legend(ncols=3)

    targets = pd.DataFrame(target_rows)
    for axis, gender, ratios in (
        (axes[1], 'Male', MEN_RATIOS),
        (axes[2], 'Female', WOMEN_RATIOS),
    ):
        divisions = list(ratios)
        gender_targets = targets[targets['Gender'].eq(gender)]
        for year in years:
            yearly = (
                gender_targets[gender_targets['Year'].eq(year)]
                .set_index('Division')
                .reindex(divisions)
            )
            hours = yearly['Finish at or below'].map(
                lambda value: parse_time(value).total_seconds() / 3600
            )
            axis.plot(divisions, hours, marker='o', linewidth=1.5, label=year)

        axis.set_title(f'{gender} Raw Finish-Time Target by Age Group')
        axis.set_xlabel('Age group')
        axis.set_ylabel('Finish at or below (HH:MM)')
        axis.yaxis.set_major_formatter(time_formatter)
        axis.yaxis.set_major_locator(MultipleLocator(ten_minutes))
        axis.tick_params(axis='x', rotation=45)
        axis.grid(True, alpha=0.35)
        axis.legend(title='Year', ncols=len(years))

    figure.suptitle(
        f'IRONMAN 70.3 Zell am See — {TOTAL_SLOTS} Slots '
        f'({SLOTS_PER_GENDER} Men / {SLOTS_PER_GENDER} Women)',
        fontsize=18,
    )
    figure.savefig(OUTPUT_PLOTS, dpi=150)
    plt.close(figure)


def main():
    workbook = pd.ExcelFile(EXCEL_FILE)
    results = [process_year(sheet) for sheet in sorted(workbook.sheet_names)]
    results = [result for result in results if result]
    if not results:
        raise RuntimeError('No valid Zell am See yearly data found')

    target_rows = build_target_rows(results)
    pd.DataFrame(target_rows).to_csv(OUTPUT_TARGETS, index=False)
    build_summary(results)
    build_plots(results, target_rows)
    print(f'Saved summary table to {OUTPUT_IMAGE}')
    print(f'Saved qualification plots to {OUTPUT_PLOTS}')
    print(f'Saved age-group finish-time targets to {OUTPUT_TARGETS}')


if __name__ == '__main__':
    ensure_output_directories()
    main()