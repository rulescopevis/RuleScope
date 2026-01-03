import pandas as pd
from typing import List, Sequence, Optional


def _normalize_formats(formats: Optional[Sequence[str]]) -> List[str]:
    """Clean provided datetime formats by removing None or empty strings."""

    if not formats:
        return []
    return [fmt for fmt in formats if isinstance(fmt, str) and fmt.strip()]


def _convert_series_to_datetime(
    series: pd.Series, formats: Optional[Sequence[str]]
) -> pd.Series:
    """Convert the series to datetimes using the provided format list."""

    normalized_formats = _normalize_formats(formats)

    def _convert(value):
        if pd.isna(value):
            return pd.NaT

        for fmt in normalized_formats:
            try:
                return pd.to_datetime(value, format=fmt)
            except Exception:
                continue

        # Fall back to pandas auto-parsing if no format matched
        try:
            return pd.to_datetime(value, errors="coerce")
        except Exception:
            return pd.NaT

    return series.apply(_convert)


def detect_compare_date(
    columnList: Sequence[pd.Series],
    compareStatus: str,
    columnFormats: Optional[Sequence[Sequence[str]]] = None,
) -> List[int]:
    """Return the indices where the date comparison fails."""

    if len(columnList) < 2:
        raise ValueError("columnList must contain at least two Series")

    columnFormats = columnFormats or []
    series1 = _convert_series_to_datetime(
        columnList[0], columnFormats[0] if len(columnFormats) > 0 else None
    )
    series2 = _convert_series_to_datetime(
        columnList[1], columnFormats[1] if len(columnFormats) > 1 else None
    )

    invalid_index: List[int] = []

    comparison_map = {
        "larger": lambda a, b: a > b,
        "larger_equal": lambda a, b: a >= b,
        "equal": lambda a, b: a == b,
        "smaller": lambda a, b: a < b,
        "smaller_equal": lambda a, b: a <= b,
        "not_equal": lambda a, b: a != b,
    }

    comparator = comparison_map.get(compareStatus)
    if comparator is None:
        raise ValueError(f"Unsupported compareStatus: {compareStatus}")

    for idx in series1.index:
        val1 = series1.loc[idx]
        val2 = series2.loc[idx]

        if pd.isna(val1) or pd.isna(val2):
            continue

        if not comparator(val1, val2):
            invalid_index.append(idx)

    return invalid_index


def detect_compare_date_valid(
    columnList: Sequence[pd.Series],
    compareStatus: str,
    columnFormats: Optional[Sequence[Sequence[str]]] = None,
) -> List[int]:
    """Return the sorted indices where the comparison holds."""

    invalid_indices = set(
        detect_compare_date(columnList, compareStatus, columnFormats)
    )
    all_indices = set(columnList[0].index)
    valid_indices = sorted(all_indices - invalid_indices)
    return valid_indices