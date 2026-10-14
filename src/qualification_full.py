import math
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from pathlib import Path
import warnings

from project_paths import DIST_DIR, LEGACY_DATA_DIR, ensure_output_directories


excel_file = LEGACY_DATA_DIR / 'ironmanaustria_updatedRules_2.xlsx'
OUTPUT_IMAGE = DIST_DIR / 'qualification_summary_table.png'
OUTPUT_TARGETS = DIST_DIR / 'qualification_time_targets.csv'
TOTAL_SLOTS = 40
NON_AGE_GROUP_DIVISIONS = {
    'MPRO', 'FPRO', 'MPC', 'FPC', 'MPC/ID', 'FPC/ID',
    'MHC', 'FHC', 'MST', 'FST', 'MGUIDE', 'FGUIDE',
}

# --- Kona ratios ---
known_men_ratios = {
    'M18-24': 0.9698, 'M25-29': 0.9921, 'M30-34': 1.0,
    'M35-39': 0.9895, 'M40-44': 0.9683, 'M45-49': 0.9401,
    'M50-54': 0.9002, 'M55-59': 0.8667, 'M60-64': 0.8262,
    'M65-69': 0.7552, 'M70-74': 0.6876, 'M75-79': 0.6768,
    'M80-84': 0.5555, 'M85-89': 0.5416,
}

known_women_ratios = {
    'F18-24': 0.9543, 'F25-29': 0.9982, 'F30-34': 1.0,
    'F35-39': 0.9877, 'F40-44': 0.9699, 'F45-49': 0.9470,
    'F50-54': 0.9051, 'F55-59': 0.8665, 'F60-64': 0.8041,
    'F65-69': 0.7606, 'F70-74': 0.7173, 'F75-79': 0.6150,
}

# Kona Standard by qualifying cycle (ironman.com/about/age-group-qualification);
# the published 2026 and 2027 tables are identical.
STANDARDS = {
    '2026': (known_men_ratios, known_women_ratios),
    '2027': (known_men_ratios, known_women_ratios),
}
CURRENT_CYCLE = '2027'


def get_ratio(gender, division, cycle=CURRENT_CYCLE):
    men, women = STANDARDS[cycle]
    if gender == 'Male':
        return men.get(division)
    elif gender == 'Female':
        return women.get(division)
    return None


def round_half_up(value):
    return math.floor(value + 0.5)


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

    # pandas Timedelta (already a duration)
    if isinstance(value, pd.Timedelta):
        return value

    # pandas Timestamp / datetime-like: extract time since midnight
    if isinstance(value, pd.Timestamp):
        td = value - value.normalize()
        return pd.to_timedelta(td)

    # Numeric values from Excel (days as float) -> convert to timedelta
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            seconds = int(float(value) * 86400)
            return timedelta(seconds=seconds)
        except Exception:
            pass

    # Try pandas parsing (handles strings like '1 days 01:23:45' or '01:23:45')
    try:
        td = pd.to_timedelta(value)
        if pd.isna(td):
            raise ValueError
        return td
    except Exception:
        # Fallback: manual hh:mm:ss parsing from strings
        parts = str(value).split(':')
        if len(parts) == 3:
            h, m, s = parts
            s = s.split('.')[0]
            try:
                return timedelta(hours=int(h), minutes=int(m), seconds=int(s))
            except Exception:
                pass

    return None


def format_td(td):
    if td is None:
        return None
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_cutoff(pool, slots, extra=0):
    idx = slots + extra - 1
    if idx >= len(pool) or idx < 0:
        return None
    return pool.iloc[idx]


def process_year(sheet_name):
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    return process_dataframe(sheet_name, df)


def process_dataframe(year, df, total_slots=TOTAL_SLOTS, cycle=CURRENT_CYCLE):
    df = df.dropna(how='all')

    if df.empty:
        return None

    gender_column = 'Gender' if 'Gender' in df.columns else 'gender'
    df['gender'] = df[gender_column].astype(str).str.strip().str.title()
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
            f"{gender}/{division} ({count})"
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

    male_winners = len(winners[winners['gender'] == 'Male'])
    female_winners = len(winners[winners['gender'] == 'Female'])

    remaining_slots = total_slots - len(winners)
    if remaining_slots < 0:
        raise ValueError(
            f'Year {year}: automatic slots exceed the total race allocation'
        )

    male_df = df[df['gender'] == 'Male']
    female_df = df[df['gender'] == 'Female']

    male_count = len(male_df)
    female_count = len(female_df)
    male_starters = int(starter_gender_counts.get('Male', 0))
    female_starters = int(starter_gender_counts.get('Female', 0))
    total_starters = male_starters + female_starters

    if total_starters == 0:
        return None

    # Validated against official results: the pool is the allocation minus
    # automatic slots awarded to age-group winners who finished.
    male_slots = round_half_up(remaining_slots * male_starters / total_starters)
    female_slots = remaining_slots - male_slots

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
            f"{gender}/{division} ({count})"
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

    male_pool = non_winners[non_winners['gender'] == 'Male'].sort_values('age_graded', kind='stable').reset_index(drop=True)
    female_pool = non_winners[non_winners['gender'] == 'Female'].sort_values('age_graded', kind='stable').reset_index(drop=True)

    def fmt(cut):
        return format_td(cut['age_graded']) if cut is not None else None

    def pool_entries(pool):
        return [
            (division, value.total_seconds())
            for division, value in zip(pool['Division'], pool['age_graded'])
        ]

    male_cut = get_cutoff(male_pool, male_slots)
    female_cut = get_cutoff(female_pool, female_slots)

    return {
        'year': year,
        'standard_cycle': cycle,
        'male_finishers': male_count,
        'female_finishers': female_count,
        'male_starters': male_starters,
        'female_starters': female_starters,
        'male_slots': male_slots,
        'female_slots': female_slots,
        'male_auto': male_winners,
        'female_auto': female_winners,
        'male_cut': fmt(male_cut),
        'male_cut_td': male_cut['age_graded'] if male_cut is not None else None,
        'male_cut_15': fmt(get_cutoff(male_pool, male_slots, 15)),
        'male_cut_30': fmt(get_cutoff(male_pool, male_slots, 30)),
        'female_cut': fmt(female_cut),
        'female_cut_td': female_cut['age_graded'] if female_cut is not None else None,
        'pools': {'male': pool_entries(male_pool), 'female': pool_entries(female_pool)},
        'pool_row_ids': {
            'male': male_pool['row_id'].tolist(),
            'female': female_pool['row_id'].tolist(),
        },
        'automatic_row_ids': winners.index.tolist(),
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
                male_slots,
            ),
            'female': official_check(
                df[df['gender'].eq('Female')],
                winners[winners['gender'].eq('Female')],
                female_pool,
                female_slots,
            ),
        },
    }


def build_target_rows(results):
    rows = []
    for result in results:
        men, women = STANDARDS[result.get('standard_cycle', CURRENT_CYCLE)]
        ratio_sets = (
            ('Male', men, 'male_cut_td'),
            ('Female', women, 'female_cut_td'),
        )
        for gender, ratios, cutoff_key in ratio_sets:
            age_graded_cutoff = result[cutoff_key]
            if age_graded_cutoff is None:
                continue
            for division, ratio in ratios.items():
                raw_target = age_graded_cutoff / ratio
                rows.append({
                    'Year': result['year'],
                    'Gender': gender,
                    'Division': division,
                    'Kona ratio': ratio,
                    'Age-graded cutoff': format_td(age_graded_cutoff),
                    'Finish at or below': format_td(raw_target),
                    'Scenario': 'Strict estimate: all AG winners accept; no roll-down',
                    'Representation basis': 'Eligible age-group starters',
                })
    return rows


if __name__ == "__main__":
    ensure_output_directories()
    xls = pd.ExcelFile(excel_file)
    sheets = [s for s in xls.sheet_names if s not in ['Kona Standards', 'Overview', 'Sub 9']]

    results = [process_year(s) for s in sorted(sheets)]
    results = [r for r in results if r]

    target_rows = build_target_rows(results)
    pd.DataFrame(target_rows).to_csv(OUTPUT_TARGETS, index=False)

    table_rows = []
    for r in results:
        table_rows.append([
            r['year'],
            r['male_finishers'],
            r['female_finishers'],
            r['male_auto'],
            r['female_auto'],
            r['male_slots'],
            r['female_slots'],
            r['male_cut'] or '-',
            r['female_cut'] or '-',
            r['male_cut_15'] or '-',
            r['male_cut_30'] or '-'
        ])

    # --- Color normalization ---
    def collect_times(key):
        vals = []
        for r in results:
            if r.get(key):
                vals.append(parse_time(r[key]))
        return vals

    male_times = collect_times('male_cut') + collect_times('male_cut_15') + collect_times('male_cut_30')
    female_times = collect_times('female_cut')

    min_m, max_m = (min(male_times), max(male_times)) if male_times else (None, None)
    min_f, max_f = (min(female_times), max(female_times)) if female_times else (None, None)

    cell_colors = []
    for r in results:
        row_colors = ['white'] * 11

        def color(val, min_t, max_t, cmap):
            if not val or not min_t or not max_t or min_t == max_t:
                return 'white'
            t = parse_time(val)
            norm = (max_t - t) / (max_t - min_t)
            return plt.get_cmap(cmap)(0.6 + 0.3 * norm)

        row_colors[7] = color(r['male_cut'], min_m, max_m, 'Blues')
        row_colors[8] = color(r['female_cut'], min_f, max_f, 'Oranges')
        row_colors[9] = color(r['male_cut_15'], min_m, max_m, 'Blues')
        row_colors[10] = color(r['male_cut_30'], min_m, max_m, 'Blues')

        cell_colors.append(row_colors)

    fig, ax = plt.subplots(figsize=(18, 0.6 * len(table_rows) + 1.5))
    ax.axis('off')

    columns = [
        'Year',
        'M finishers*', 'F finishers*',
        'M auto', 'F auto',
        'M perf slots', 'F perf slots',
        'M AG cutoff', 'F AG cutoff',
        'M rank +15', 'M rank +30'
    ]

    table = ax.table(
        cellText=table_rows,
        colLabels=columns,
        cellLoc='center',
        loc='center',
        cellColours=cell_colors
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    ax.set_title(
        f'Strict IM Qualification Estimate — Total slots: {TOTAL_SLOTS}\n'
        '*Finisher representation used because starter counts are unavailable',
        pad=20,
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=150, bbox_inches='tight')

    print(f'Saved summary table to {OUTPUT_IMAGE}')
    print(f'Saved age-group finish-time targets to {OUTPUT_TARGETS}')