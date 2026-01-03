import pandas as pd
import numpy as np

def detect_compare_numeric(columnList, compareStatus):
    """Check whether the numerical relationship between two series matches the given comparison."""

    series1 = columnList[0]
    series2 = columnList[1]

    invalid_index = []

    for idx in series1.index:
        if pd.isna(series1[idx]) or pd.isna(series2[idx]):
            continue

        value1 = series1[idx]
        value2 = series2[idx]

        is_valid = True

        if compareStatus == "larger":
            is_valid = value1 > value2
        elif compareStatus == "larger_equal":
            is_valid = value1 >= value2
        elif compareStatus == "equal":
            is_valid = value1 == value2
        elif compareStatus == "smaller":
            is_valid = value1 < value2
        elif compareStatus == "smaller_equal":
            is_valid = value1 <= value2
        elif compareStatus == "not_equal":
            is_valid = value1 != value2

        if not is_valid:
            invalid_index.append(idx)

    return invalid_index


def detect_compare_numeric_valid(columnList, compareStatus):
    """Return the list of indices where the comparison holds after dropping the first entry."""

    outlier_indices = detect_compare_numeric(columnList, compareStatus)
    all_indices = set(columnList[0].index)
    valid_indices = list(all_indices.difference(outlier_indices))
    valid_indices.remove(0)
    valid_indices_sorted = sorted(valid_indices)

    return valid_indices_sorted