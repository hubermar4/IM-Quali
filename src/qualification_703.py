from datetime import time, timedelta
import warnings

import pandas as pd
import reference_data

_CONSTANTS = reference_data.qualification_constants()
TOTAL_SLOTS = _CONSTANTS['half_total_slots']
SLOTS_PER_GENDER = _CONSTANTS['half_slots_per_gender']
NON_AGE_GROUP_DIVISIONS = set(_CONSTANTS['non_age_group_divisions'])

# IRONMAN 70.3 Standard by qualifying cycle (data/reference/age_group_standards.json).
CURRENT_CYCLE, STANDARDS = reference_data.standards('half')


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
