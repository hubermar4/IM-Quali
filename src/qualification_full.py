import math
import pandas as pd
import reference_data
from datetime import timedelta
import warnings

_CONSTANTS = reference_data.qualification_constants()
TOTAL_SLOTS = _CONSTANTS['full_total_slots']
NON_AGE_GROUP_DIVISIONS = set(_CONSTANTS['non_age_group_divisions'])

# Kona Standard by qualifying cycle (data/reference/age_group_standards.json).
CURRENT_CYCLE, STANDARDS = reference_data.standards('full')


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
