from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# BEGIN_DETECTION_HELPERS

def _ensure_series(values: pd.Series | Sequence[Any]) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.copy()
    return pd.Series(values)


def _coerce_indices(raw_indices: Sequence[Any]) -> List[Any]:
    cleaned: List[Any] = []
    for idx in raw_indices:
        cleaned.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return cleaned


def _missing_with_special(
    series: pd.Series | Sequence[Any],
    special_values: Optional[Sequence[Any]] = None,
    count_rate_decimal: int = 6,
    *,
    numeric: bool = False,
) -> Dict[str, Any]:
    ser = _ensure_series(series)
    if numeric:
        ser = pd.to_numeric(ser, errors="coerce")
    total = len(ser)
    if total == 0:
        raise ValueError("Input column is empty")

    base_mask = ser.isna()
    all_indices = _coerce_indices(ser.index[base_mask].tolist())
    special_entries: List[Dict[str, Any]] = []

    values = list(special_values or [])
    numeric_array: Optional[np.ndarray] = ser.to_numpy() if numeric else None

    for raw_value in values:
        entry_key = "numericMissingValue" if numeric else "specialMissingValue"
        if numeric:
            assert numeric_array is not None
            try:
                numeric_target = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
            except Exception:
                continue
            if pd.isna(numeric_target):
                continue
            mask_values = np.isclose(
                numeric_array.astype(float),
                float(numeric_target),
                rtol=1e-05,
                atol=1e-08,
                equal_nan=False,
            )
            mask = pd.Series(mask_values, index=ser.index)
        else:
            if raw_value is None:
                continue
            mask = ser == raw_value
        mask &= ~ser.isna()
        count = int(mask.sum())
        if count == 0:
            continue
        idx_list = _coerce_indices(ser.index[mask].tolist())
        all_indices.extend(idx_list)
        special_entries.append(
            {
                entry_key: raw_value,
                "count": count,
                "rate": round(count / total, count_rate_decimal),
                "index": idx_list,
            }
        )

    unique_indices = sorted(set(all_indices))
    result: Dict[str, Any] = {
        "missingStatus": True,
        "missingDict": {
            "count": len(unique_indices),
            "rate": round(len(unique_indices) / total, count_rate_decimal),
            "index": unique_indices,
        },
    }
    if special_entries:
        key = "numericMissingList" if numeric else "specialMissingList"
        result["missingDict"][key] = special_entries
    return result


def character_missing(
    series: pd.Series | Sequence[Any],
    count_rate_decimal: int = 6,
    special_missing_values: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    try:
        return _missing_with_special(
            series,
            special_values=special_missing_values,
            count_rate_decimal=count_rate_decimal,
            numeric=False,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"missingStatus": False, "missingDict": str(exc)}


def numeric_missing(
    series: pd.Series | Sequence[Any],
    count_rate_decimal: int = 6,
    numeric_missing_values: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    try:
        return _missing_with_special(
            series,
            special_values=numeric_missing_values,
            count_rate_decimal=count_rate_decimal,
            numeric=True,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"missingStatus": False, "missingDict": str(exc)}


def date_missing(
    series: pd.Series | Sequence[Any],
    count_rate_decimal: int = 6,
    special_missing_values: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    try:
        return _missing_with_special(
            series,
            special_values=special_missing_values,
            count_rate_decimal=count_rate_decimal,
            numeric=False,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"missingStatus": False, "missingDict": str(exc)}


def detect_duplicate(series: pd.Series | Sequence[Any]) -> List[Any]:
    ser = _ensure_series(series)
    if ser.empty:
        return []
    counts = ser.value_counts(dropna=True)
    duplicate_values = set(counts[counts > 1].index)
    duplicates: List[Any] = []
    for idx, value in ser.items():
        if pd.isna(value):
            continue
        if value in duplicate_values:
            duplicates.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return sorted(duplicates)


def detect_format(series: pd.Series | Sequence[Any], pattern: str) -> List[Any]:
    if not pattern:
        return []
    regex = re.compile(pattern)
    ser = _ensure_series(series)
    invalid: List[Any] = []
    for idx, value in ser.items():
        if pd.isna(value):
            continue
        if not regex.match(str(value)):
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def detect_numeric_range(series: pd.Series | Sequence[Any], range_rules: List[Dict[str, Any]]) -> List[Any]:
    if not isinstance(range_rules, list) or not range_rules:
        return []
    ser = pd.to_numeric(_ensure_series(series), errors="coerce")
    valid_mask = ~ser.isna()
    if not valid_mask.any():
        return []
    in_any_range = pd.Series(False, index=ser.index)
    for rule in range_rules:
        mask = pd.Series(True, index=ser.index)
        start = rule.get("start")
        end = rule.get("end")
        if start is not None:
            if rule.get("startInclusive", True):
                mask &= ser >= start
            else:
                mask &= ser > start
        if end is not None:
            if rule.get("endInclusive", True):
                mask &= ser <= end
            else:
                mask &= ser < end
        in_any_range |= mask
    outlier_mask = valid_mask & ~in_any_range
    return _coerce_indices(ser.index[outlier_mask].tolist())


def _parse_date_value(value: Any, formats: Sequence[str]) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.to_datetime(value)
    for fmt in formats:
        try:
            return pd.to_datetime(value, format=fmt)
        except Exception:
            continue
    return pd.to_datetime(value, errors="coerce")


def _parse_date_bound(value: Any, formats: Sequence[str]) -> Optional[pd.Timestamp]:
    if value is None or pd.isna(value):
        return None
    parsed = _parse_date_value(value, formats)
    if pd.isna(parsed):
        raise ValueError("Invalid date format in range rules")
    return parsed


def detect_date_range(
    series: pd.Series | Sequence[Any],
    range_rules: List[Dict[str, Any]],
    main_format: Optional[str],
    other_format_list: Optional[Sequence[str]] = None,
) -> List[Any]:
    if not isinstance(range_rules, list) or not range_rules:
        return []
    ser = _ensure_series(series)
    formats: List[str] = []
    if main_format:
        formats.append(main_format)
    formats.extend([fmt for fmt in other_format_list or [] if fmt])
    parsed_series = ser.apply(lambda value: _parse_date_value(value, formats))

    processed_rules: List[Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp], bool, bool]] = []
    for rule in range_rules:
        start = _parse_date_bound(rule.get("start"), formats)
        end = _parse_date_bound(rule.get("end"), formats)
        if start is None and end is None:
            raise ValueError("Range rule must provide at least one bound")
        processed_rules.append(
            (
                start,
                end,
                rule.get("startInclusive", True),
                rule.get("endInclusive", True),
            )
        )

    invalid: List[Any] = []
    for idx, value in parsed_series.items():
        if pd.isna(value):
            continue
        in_range = False
        for start, end, start_inclusive, end_inclusive in processed_rules:
            start_ok = True
            end_ok = True
            if start is not None:
                start_ok = value >= start if start_inclusive else value > start
            if end is not None:
                end_ok = value <= end if end_inclusive else value < end
            if start_ok and end_ok:
                in_range = True
                break
        if not in_range:
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def _build_sort_keys(order_condition: Optional[Dict[str, Any]], columns: Sequence[str]) -> Tuple[List[str], List[bool]]:
    if not order_condition:
        return [], []
    sort_columns: List[str] = []
    sort_ascending: List[bool] = []
    for prefix in ("first", "second", "third"):
        column_name = order_condition.get(f"{prefix}OrderColumn")
        if column_name and column_name in columns:
            sort_columns.append(column_name)
            order_type = order_condition.get(f"{prefix}OrderType", "asc")
            sort_ascending.append(str(order_type).lower() == "asc")
    return sort_columns, sort_ascending


def _prepare_sorted_frame(
    dataframe: pd.DataFrame,
    order_condition: Optional[Dict[str, Any]],
    table_dict: Optional[Dict[str, Any]],
) -> Tuple[pd.DataFrame, np.ndarray]:
    df_copy = dataframe.copy()
    order_condition = order_condition or {}
    date_columns = [col for col in order_condition.get("dateColumns", []) if col in df_copy.columns]
    for col in date_columns:
        fmt = ((table_dict or {}).get(col) or {}).get("mainFormat")
        df_copy[col] = pd.to_datetime(df_copy[col], format=fmt, errors="coerce") if fmt else pd.to_datetime(df_copy[col], errors="coerce")
    sort_columns, sort_ascending = _build_sort_keys(order_condition, df_copy.columns)
    if sort_columns:
        df_sorted = df_copy.sort_values(by=sort_columns, ascending=sort_ascending, kind="mergesort")
    else:
        df_sorted = df_copy
    return df_sorted, df_sorted.index.to_numpy()


def detect_absolute_difference(
    dataframe: pd.DataFrame,
    column_name: str,
    order_condition: Optional[Dict[str, Any]],
    difference_threshold: Dict[str, Any],
    table_dict: Optional[Dict[str, Any]],
) -> List[Dict[str, int]]:
    if column_name not in dataframe.columns:
        return []
    start = difference_threshold.get("start", 0)
    end = difference_threshold.get("end", 0)
    if start is None or end is None:
        raise ValueError("differenceThreshold requires start and end")
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be <= end")

    df_sorted, sorted_indices = _prepare_sorted_frame(dataframe, order_condition, table_dict)
    values = df_sorted[column_name].to_numpy()
    if len(values) < 2:
        return []
    current = values[:-1]
    nxt = values[1:]
    valid_mask = ~(pd.isna(current) | pd.isna(nxt))
    if not valid_mask.any():
        return []
    diffs = np.abs(nxt[valid_mask] - current[valid_mask])
    start_check = diffs >= start if difference_threshold.get("startInclusive", True) else diffs > start
    end_check = diffs <= end if difference_threshold.get("endInclusive", True) else diffs < end
    in_range = start_check & end_check
    outlier_positions = np.where(~in_range)[0]
    base_indices = np.where(valid_mask)[0]
    result: List[Dict[str, int]] = []
    for pos in outlier_positions:
        original_idx = int(base_indices[pos])
        result.append(
            {
                "currentIndex": int(sorted_indices[original_idx]),
                "nextIndex": int(sorted_indices[original_idx + 1]),
                "sortCurrentIndex": int(original_idx),
                "sortNextIndex": int(original_idx + 1),
            }
        )
    return result


def detect_relative_difference(
    dataframe: pd.DataFrame,
    column_name: str,
    order_condition: Optional[Dict[str, Any]],
    difference_threshold: Dict[str, Any],
    table_dict: Optional[Dict[str, Any]],
) -> List[Dict[str, int]]:
    if column_name not in dataframe.columns:
        return []
    start = difference_threshold.get("start", 0)
    end = difference_threshold.get("end", 0)
    if start is None or end is None:
        raise ValueError("differenceThreshold requires start and end")
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be <= end")

    df_sorted, sorted_indices = _prepare_sorted_frame(dataframe, order_condition, table_dict)
    values = df_sorted[column_name].to_numpy()
    if len(values) < 2:
        return []
    current = values[:-1]
    nxt = values[1:]
    valid_mask = ~(pd.isna(current) | pd.isna(nxt))
    if not valid_mask.any():
        return []
    abs_diff = np.abs(nxt[valid_mask] - current[valid_mask])
    base_values = current[valid_mask]
    non_zero_mask = base_values != 0
    relative = np.zeros_like(abs_diff)
    relative[non_zero_mask] = abs_diff[non_zero_mask] / np.abs(base_values[non_zero_mask])
    start_check = relative >= start if difference_threshold.get("startInclusive", True) else relative > start
    end_check = relative <= end if difference_threshold.get("endInclusive", True) else relative < end
    in_range = start_check & end_check & non_zero_mask
    outlier_positions = np.where(~in_range)[0]
    base_indices = np.where(valid_mask)[0]
    result: List[Dict[str, int]] = []
    for pos in outlier_positions:
        original_idx = int(base_indices[pos])
        result.append(
            {
                "currentIndex": int(sorted_indices[original_idx]),
                "nextIndex": int(sorted_indices[original_idx + 1]),
                "sortCurrentIndex": int(original_idx),
                "sortNextIndex": int(original_idx + 1),
            }
        )
    return result


def is_empty_sequence_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return pd.isna(value)


def detect_sequence(
    dataframe: pd.DataFrame,
    column_name: str,
    order_condition: Optional[Dict[str, Any]],
    sequence_rule: List[Dict[str, Any]],
    table_dict: Optional[Dict[str, Any]],
) -> List[Dict[str, int]]:
    if column_name not in dataframe.columns or len(sequence_rule) == 0:
        return []
    df_sorted, sorted_indices = _prepare_sorted_frame(dataframe, order_condition, table_dict)
    values = df_sorted[column_name]
    if len(values) < 2:
        return []
    rule_map: Dict[Any, List[Any]] = {}
    for rule in sequence_rule:
        key = rule.get("value")
        if pd.isna(key):
            key = np.nan
        allowed = []
        for entry in rule.get("allowed_next", []) or []:
            allowed.append(np.nan if pd.isna(entry) else entry)
        rule_map[key] = allowed
    outliers: List[Dict[str, int]] = []
    for pos in range(len(values) - 1):
        current_val = values.iloc[pos]
        next_val = values.iloc[pos + 1]
        if is_empty_sequence_value(current_val) or is_empty_sequence_value(next_val):
            continue
        key = np.nan if pd.isna(current_val) else current_val
        allowed = rule_map.get(key)
        if not allowed:
            continue
        match = False
        for candidate in allowed:
            if pd.isna(candidate) and pd.isna(next_val):
                match = True
                break
            if not pd.isna(candidate) and candidate == next_val:
                match = True
                break
        if not match:
            outliers.append(
                {
                    "currentIndex": int(sorted_indices[pos]),
                    "nextIndex": int(sorted_indices[pos + 1]),
                    "sortCurrentIndex": int(pos),
                    "sortNextIndex": int(pos + 1),
                }
            )
    return outliers


def detect_multi_difference(
    dataframe: pd.DataFrame,
    column_names: Sequence[str],
    order_condition: Optional[Dict[str, Any]],
    difference_threshold: Dict[str, Any],
    table_dict: Optional[Dict[str, Any]],
) -> List[Dict[str, int]]:
    if not column_names:
        return []
    start = difference_threshold.get("start", 0)
    end = difference_threshold.get("end", 0)
    if start is None or end is None:
        raise ValueError("differenceThreshold requires start and end")
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be <= end")

    df_sorted, sorted_indices = _prepare_sorted_frame(dataframe, order_condition, table_dict)
    if len(df_sorted) < 2:
        return []
    outliers: List[Dict[str, int]] = []
    for pos in range(len(df_sorted) - 1):
        current_idx = sorted_indices[pos]
        next_idx = sorted_indices[pos + 1]
        squared_sum = 0.0
        has_null = False
        for column in column_names:
            current_value = df_sorted.loc[current_idx, column]
            next_value = df_sorted.loc[next_idx, column]
            if pd.isna(current_value) or pd.isna(next_value):
                has_null = True
                break
            diff = float(next_value) - float(current_value)
            squared_sum += diff * diff
        if has_null:
            continue
        distance = float(np.sqrt(squared_sum))
        start_ok = distance >= start if difference_threshold.get("startInclusive", True) else distance > start
        end_ok = distance <= end if difference_threshold.get("endInclusive", True) else distance < end
        if not (start_ok and end_ok):
            outliers.append(
                {
                    "currentIndex": int(current_idx),
                    "nextIndex": int(next_idx),
                    "sortCurrentIndex": int(pos),
                    "sortNextIndex": int(pos + 1),
                }
            )
    return outliers


def detect_multi_duplicate(column_list: Sequence[pd.Series]) -> List[Any]:
    if not column_list or len(column_list) < 2:
        raise ValueError("column_list must contain at least two Series")
    base_index = column_list[0].index
    for series in column_list[1:]:
        if not series.index.equals(base_index):
            raise ValueError("All Series must share the same index")
    temp_df = pd.concat(column_list, axis=1)
    all_na = temp_df.isna().all(axis=1)
    duplicated_rows = temp_df.duplicated(keep=False) & ~all_na
    return _coerce_indices(temp_df.index[duplicated_rows].tolist())


def detect_logic_condition_mod(
    dataframe: pd.DataFrame,
    conditions_constraints: Sequence[Tuple[List[Dict[str, Any]], Dict[str, Any]]],
) -> List[Any]:
    overall_invalid = pd.Series(False, index=dataframe.index)
    for condition_list, constraint_dict in conditions_constraints:
        condition_mask = pd.Series(True, index=dataframe.index)
        has_null_mask = pd.Series(False, index=dataframe.index)
        for condition in condition_list:
            column = condition["conditionColumn"]
            has_null_mask |= dataframe[column].isna()
            if condition["conditionType"] == "EqualityBased":
                column_data = dataframe[column].astype(str)
                targets = [str(item) for item in condition.get("conditionContent", []) or []]
                condition_mask &= column_data.isin(targets)
            else:
                range_mask = pd.Series(False, index=dataframe.index)
                for range_dict in condition.get("conditionContent", []) or []:
                    start = range_dict.get("start")
                    end = range_dict.get("end")
                    start_inclusive = range_dict.get("startInclusive", True)
                    end_inclusive = range_dict.get("endInclusive", True)
                    temp_mask = pd.Series(True, index=dataframe.index)
                    if start is not None:
                        temp_mask &= dataframe[column] >= start if start_inclusive else dataframe[column] > start
                    if end is not None:
                        temp_mask &= dataframe[column] <= end if end_inclusive else dataframe[column] < end
                    range_mask |= temp_mask
                condition_mask &= range_mask
        constraint_column = constraint_dict["constraintColumn"]
        has_null_mask |= dataframe[constraint_column].isna()
        valid_rows = ~has_null_mask
        if constraint_dict["constraintType"] == "EqualityBased":
            column_data = dataframe[constraint_column].astype(str)
            targets = [str(item) for item in constraint_dict.get("constraintContent", []) if item is not None]
            constraint_mask = column_data.isin(targets)
            if None in constraint_dict.get("constraintContent", []):
                constraint_mask |= dataframe[constraint_column].isna()
        else:
            constraint_mask = pd.Series(False, index=dataframe.index)
            for range_dict in constraint_dict.get("constraintContent", []) or []:
                start = range_dict.get("start")
                end = range_dict.get("end")
                start_inclusive = range_dict.get("startInclusive", True)
                end_inclusive = range_dict.get("endInclusive", True)
                temp_mask = pd.Series(True, index=dataframe.index)
                if start is not None:
                    temp_mask &= dataframe[constraint_column] >= start if start_inclusive else dataframe[constraint_column] > start
                if end is not None:
                    temp_mask &= dataframe[constraint_column] <= end if end_inclusive else dataframe[constraint_column] < end
                constraint_mask |= temp_mask
        invalid_mask = condition_mask & valid_rows & ~constraint_mask
        overall_invalid |= invalid_mask
    return _coerce_indices(dataframe.index[overall_invalid].tolist())


def _normalize_formats(formats: Optional[Sequence[str]]) -> List[str]:
    if not formats:
        return []
    return [fmt for fmt in formats if isinstance(fmt, str) and fmt.strip()]


def _convert_series_to_datetime(series: pd.Series, formats: Optional[Sequence[str]]) -> pd.Series:
    normalized_formats = _normalize_formats(formats)

    def _convert(value: Any) -> pd.Timestamp:
        if pd.isna(value):
            return pd.NaT
        for fmt in normalized_formats:
            try:
                return pd.to_datetime(value, format=fmt)
            except Exception:
                continue
        return pd.to_datetime(value, errors="coerce")

    return series.apply(_convert)


def detect_compare_numeric(column_list: Sequence[pd.Series], compare_status: str) -> List[Any]:
    if len(column_list) < 2:
        raise ValueError("column_list must contain at least two Series")
    series1, series2 = column_list[0], column_list[1]
    invalid: List[Any] = []
    comparison_map = {
        "larger": lambda a, b: a > b,
        "larger_equal": lambda a, b: a >= b,
        "equal": lambda a, b: a == b,
        "smaller": lambda a, b: a < b,
        "smaller_equal": lambda a, b: a <= b,
        "not_equal": lambda a, b: a != b,
    }
    comparator = comparison_map.get(compare_status)
    if comparator is None:
        raise ValueError(f"Unsupported compareStatus: {compare_status}")
    for idx in series1.index:
        val1 = series1.loc[idx]
        val2 = series2.loc[idx]
        if pd.isna(val1) or pd.isna(val2):
            continue
        if not comparator(val1, val2):
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def detect_compare_date(
    column_list: Sequence[pd.Series],
    compare_status: str,
    column_formats: Optional[Sequence[Sequence[str]]] = None,
) -> List[Any]:
    if len(column_list) < 2:
        raise ValueError("column_list must contain at least two Series")
    column_formats = column_formats or []
    series1 = _convert_series_to_datetime(
        column_list[0], column_formats[0] if len(column_formats) > 0 else None
    )
    series2 = _convert_series_to_datetime(
        column_list[1], column_formats[1] if len(column_formats) > 1 else None
    )
    comparison_map = {
        "larger": lambda a, b: a > b,
        "larger_equal": lambda a, b: a >= b,
        "equal": lambda a, b: a == b,
        "smaller": lambda a, b: a < b,
        "smaller_equal": lambda a, b: a <= b,
        "not_equal": lambda a, b: a != b,
    }
    comparator = comparison_map.get(compare_status)
    if comparator is None:
        raise ValueError(f"Unsupported compareStatus: {compare_status}")
    invalid: List[Any] = []
    for idx in series1.index:
        val1 = series1.loc[idx]
        val2 = series2.loc[idx]
        if pd.isna(val1) or pd.isna(val2):
            continue
        if not comparator(val1, val2):
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def detect_substring_character(column_list: Sequence[pd.Series]) -> List[Any]:
    if len(column_list) < 2:
        raise ValueError("column_list must contain two Series")
    series1, series2 = column_list[0], column_list[1]
    invalid: List[Any] = []
    for idx in series1.index:
        val1 = series1.loc[idx]
        val2 = series2.loc[idx]
        if pd.isna(val1) or pd.isna(val2):
            continue
        if str(val1).strip() not in str(val2).strip():
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def detect_lookup(parent_column: pd.Series, child_column: pd.Series, lookup_list: Sequence[Dict[str, Any]]) -> List[Any]:
    parent_str = parent_column.astype(str)
    child_str = child_column.astype(str)
    lookup_dict: Dict[str, set[str]] = {}
    valid_parents: set[str] = set()
    for item in lookup_list:
        parent_value = str(item.get("parentValue")) if item.get("parentValue") is not None else "None"
        valid_parents.add(parent_value)
        for child in item.get("childValueList", []) or []:
            child_value = str(child) if child is not None else "None"
            lookup_dict.setdefault(child_value, set()).add(parent_value)
    invalid: List[Any] = []
    for idx in parent_str.index:
        parent_value = parent_str.loc[idx]
        child_value = child_str.loc[idx]
        if parent_value not in valid_parents:
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
            continue
        if child_value not in lookup_dict:
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
            continue
        if parent_value not in lookup_dict[child_value]:
            invalid.append(int(idx) if isinstance(idx, (np.integer, int)) else idx)
    return invalid


def invalid_pairs_to_indices(invalid_pairs: Sequence[Dict[str, Any]]) -> List[Any]:
    indices: set[Any] = set()
    for pair in invalid_pairs:
        indices.add(pair.get("currentIndex"))
        indices.add(pair.get("nextIndex"))
    return sorted(idx for idx in indices if idx is not None)

# END_DETECTION_HELPERS
