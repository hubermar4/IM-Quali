from datetime import datetime, time, timedelta

import pandas as pd

SPLIT_COLUMNS = {
    "Swim": "Swim Time",
    "T1": "Transition 1 Time",
    "Bike": "Bike Time",
    "T2": "Transition 2 Time",
    "Run": "Run Time",
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
