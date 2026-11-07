"""Helpers shared by the 140.6 (`qualification_full`) and 70.3 (`qualification_703`) models.

Both distances clean result rows, rank finishers and compare the strict model
with the official `Qualified` flags in exactly the same way; only the slot
allocation differs. Keeping these steps here ensures a fix applies to both.
"""
import warnings
from datetime import time, timedelta

import pandas as pd

AGE_GROUP_DIVISION = r'^[MF]\d{2}-\d{2}$'


def parse_time(value):
    """Return a duration for a result cell, or None if it is empty or unparseable."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timedelta):
        return value
    if isinstance(value, timedelta):
        return pd.Timedelta(value)
    if isinstance(value, time):
        return timedelta(
            hours=value.hour,
            minutes=value.minute,
            seconds=value.second,
            microseconds=value.microsecond,
        )
    if isinstance(value, pd.Timestamp):
        return pd.to_timedelta(value - value.normalize())
    # Numeric values from spreadsheets are fractions of a day.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return timedelta(seconds=float(value) * 86400)
    try:
        parsed = pd.to_timedelta(value)
        if not pd.isna(parsed):
            return parsed
    except (TypeError, ValueError):
        pass
    # Fallback for strings pandas rejects, e.g. '9:05:07.' or ' 09:05:07 '.
    parts = str(value).strip().split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        try:
            return timedelta(
                hours=int(hours), minutes=int(minutes), seconds=int(seconds.split('.')[0]),
            )
        except ValueError:
            pass
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
    """Row at 1-based pool rank `slots + extra`, or None when that rank does not exist."""
    index = slots + extra - 1
    if index < 0 or index >= len(pool):
        return None
    return pool.iloc[index]


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


def _warn_groups(year, message, frame):
    details = ', '.join(
        f'{gender}/{division} ({count})'
        for (gender, division), count in frame.groupby(['gender', 'Division']).size().items()
    )
    warnings.warn(f'Year {year}: {message}: {details}', stacklevel=3)


def age_group_rows(year, df, non_age_group_divisions):
    """Normalise gender/division and keep rows of canonical, gender-consistent age groups.

    Returns `(rows, starter_gender_counts)`; starters exclude DNS and are counted
    before finishers are selected, because slot allocation uses eligible starters.
    """
    gender_column = 'Gender' if 'Gender' in df.columns else 'gender'
    df['gender'] = df[gender_column].astype(str).str.strip().str.title()
    df['Division'] = df['Division'].astype(str).str.strip().str.upper()
    canonical = df['Division'].str.match(AGE_GROUP_DIVISION, na=False)
    consistent = (
        df['gender'].eq('Male') & df['Division'].str.startswith('M')
    ) | (
        df['gender'].eq('Female') & df['Division'].str.startswith('F')
    )
    unsupported = df[~(canonical & consistent) & ~df['Division'].isin(non_age_group_divisions)]
    if not unsupported.empty:
        _warn_groups(
            year,
            'excluded rows with inconsistent or unsupported gender/division values',
            unsupported.fillna({'gender': 'missing', 'Division': 'missing'}),
        )
    rows = df[canonical & consistent].copy()
    starters = rows
    if 'Finish' in starters.columns:
        starters = starters[~starters['Finish'].astype(str).str.strip().str.upper().eq('DNS')]
    return rows, starters['gender'].value_counts()


def ranked_finishers(df):
    """Official finishers with a positive parsed `finish_td` and numeric age-group rank."""
    if 'Finish' in df.columns:
        df = df[df['Finish'].astype(str).str.strip().str.upper().eq('FIN')].copy()
    if df.empty:
        return df
    df['finish_td'] = df['Overall Time'].apply(parse_time)
    df = df.dropna(subset=['finish_td'])
    df = df[df['finish_td'] > timedelta(0)].copy()
    df['Age Group Rank'] = pd.to_numeric(df['Age Group Rank'], errors='coerce')
    return df


def age_group_winners(df):
    """The fastest age-group rank-1 finisher per division (automatic-slot route)."""
    return (
        df[df['Age Group Rank'].eq(1)]
        .sort_values('finish_td')
        .drop_duplicates('Division')
    )


def performance_pools(year, df, winners, get_ratio, cycle):
    """Age-graded male and female performance pools, excluding automatic winners.

    Finishers whose age group has no published standard are excluded with a warning.
    """
    df['ratio'] = pd.Series(
        [get_ratio(gender, division, cycle) for gender, division in zip(df['gender'], df['Division'])],
        index=df.index,
        dtype='float64',
    )
    missing_standard = df[df['ratio'].isna()]
    if not missing_standard.empty:
        _warn_groups(
            year,
            'excluded finishers from the performance pool because the official '
            'age-group standard is TBD',
            missing_standard,
        )
    performance_df = df.dropna(subset=['ratio']).copy()
    performance_df['age_graded'] = performance_df['finish_td'] * performance_df['ratio']
    non_winners = performance_df.loc[
        ~performance_df.index.isin(winners.index)
    ].rename_axis('row_id').reset_index()

    def pool(gender):
        return (
            non_winners[non_winners['gender'].eq(gender)]
            .sort_values('age_graded', kind='stable')
            .reset_index(drop=True)
        )

    return pool('Male'), pool('Female')


def pool_entries(pool):
    return [
        (division, value.total_seconds())
        for division, value in zip(pool['Division'], pool['age_graded'])
    ]


def shared_result_fields(year, cycle, df, winners, male_pool, female_pool, male_slots, female_slots):
    """Result fields identical for both distances (pools, winners, official check)."""
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
                df[df['gender'].eq('Male')], winners[winners['gender'].eq('Male')],
                male_pool, male_slots,
            ),
            'female': official_check(
                df[df['gender'].eq('Female')], winners[winners['gender'].eq('Female')],
                female_pool, female_slots,
            ),
        },
    }
