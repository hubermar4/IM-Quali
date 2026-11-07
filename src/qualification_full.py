import math

import reference_data
from qualification_common import (  # noqa: F401 - re-exported for callers and tests
    age_group_rows,
    age_group_winners,
    format_td,
    get_cutoff,
    official_check,
    parse_time,
    performance_pools,
    ranked_finishers,
    shared_result_fields,
)

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


def process_dataframe(year, df, total_slots=TOTAL_SLOTS, cycle=CURRENT_CYCLE):
    df = df.dropna(how='all')

    if df.empty:
        return None

    df, starter_gender_counts = age_group_rows(year, df, NON_AGE_GROUP_DIVISIONS)
    df = ranked_finishers(df)
    if df.empty:
        return None
    winners = age_group_winners(df)

    male_winners = int(winners['gender'].eq('Male').sum())
    female_winners = int(winners['gender'].eq('Female').sum())

    remaining_slots = total_slots - len(winners)
    if remaining_slots < 0:
        raise ValueError(
            f'Year {year}: automatic slots exceed the total race allocation'
        )

    male_starters = int(starter_gender_counts.get('Male', 0))
    female_starters = int(starter_gender_counts.get('Female', 0))
    total_starters = male_starters + female_starters

    if total_starters == 0:
        return None

    # Validated against official results: the pool is the allocation minus
    # automatic slots awarded to age-group winners who finished.
    male_slots = round_half_up(remaining_slots * male_starters / total_starters)
    female_slots = remaining_slots - male_slots

    male_pool, female_pool = performance_pools(year, df, winners, get_ratio, cycle)

    def fmt(cut):
        return format_td(cut['age_graded']) if cut is not None else None

    male_cut = get_cutoff(male_pool, male_slots)
    female_cut = get_cutoff(female_pool, female_slots)

    return {
        **shared_result_fields(
            year, cycle, df, winners, male_pool, female_pool, male_slots, female_slots,
        ),
        'male_finishers': int(df['gender'].eq('Male').sum()),
        'female_finishers': int(df['gender'].eq('Female').sum()),
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
