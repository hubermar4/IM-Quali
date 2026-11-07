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

    df, starter_gender_counts = age_group_rows(year, df, NON_AGE_GROUP_DIVISIONS)
    df = ranked_finishers(df)
    if df.empty:
        return None
    winners = age_group_winners(df)

    male_auto = int(winners['gender'].eq('Male').sum())
    female_auto = int(winners['gender'].eq('Female').sum())
    male_performance_slots = male_slots - male_auto
    female_performance_slots = female_slots - female_auto
    if male_performance_slots < 0 or female_performance_slots < 0:
        raise ValueError(
            f'Year {year}: automatic slots exceed the per-gender allocation'
        )

    male_pool, female_pool = performance_pools(year, df, winners, get_ratio, cycle)

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

    return {
        **shared_result_fields(
            year, cycle, df, winners, male_pool, female_pool,
            male_performance_slots, female_performance_slots,
        ),
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
