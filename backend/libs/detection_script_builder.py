import json
import os
import time
from string import Template
from textwrap import dedent
from typing import Dict, Optional, Tuple

HELPER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "detection_script_helpers.py")
HELPER_START_MARKER = "# BEGIN_DETECTION_HELPERS"
HELPER_END_MARKER = "# END_DETECTION_HELPERS"


def _load_runtime_helpers() -> str:
    with open(HELPER_FILE, "r", encoding="utf-8") as helper_source:
        helper_content = helper_source.read()
    if HELPER_START_MARKER not in helper_content or HELPER_END_MARKER not in helper_content:
        raise RuntimeError("Unable to locate helper markers in detection_script_helpers.py")
    body = helper_content.split(HELPER_START_MARKER, 1)[1]
    body = body.split(HELPER_END_MARKER, 1)[0]
    return dedent(body).strip() + "\n"


RUNTIME_HELPERS = _load_runtime_helpers()

DETECTION_SCRIPT_TEMPLATE = Template(
    """#!/usr/bin/env python3
\"\"\"Auto-generated detection script.

Dataset: ${dataset_label_comment}
Generated: ${timestamp_comment}
\"\"\"

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import re

import numpy as np
import pandas as pd

${runtime_helpers}

VALIDATION_RULES = json.loads(
    ${validation_rules}
)

DATE_FORMAT_LOOKUP = json.loads(
    ${date_formats}
)

DEFAULT_CSV_PATH = Path(${csv_path})
DEFAULT_RESULT_NAME = ${default_output}
DATASET_LABEL = ${dataset_label_literal}
SCRIPT_GENERATED_AT = ${timestamp_literal}

TABLE_FORMAT_DICT = {col: {"mainFormat": fmt} for col, fmt in DATE_FORMAT_LOOKUP.items()}


def _coerce_index_value(value: Any) -> Any:
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        try:
            as_int = int(value)
            if float(as_int) == float(value):
                return as_int
        except (ValueError, TypeError):
            pass
        return float(value)
    return value


def _normalize_indices(values: Sequence[Any] | None) -> List[Any]:
    if not values:
        return []
    normalized: List[Any] = []
    seen = set()
    for value in values:
        coerced = _coerce_index_value(value)
        key = coerced if isinstance(coerced, (int, str)) else None
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        normalized.append(coerced)
    return normalized


def _to_serializable(value: Any) -> Any:
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.ndarray):
        return [_to_serializable(v) for v in value.tolist()]
    if isinstance(value, dict):
        return {k: _to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_serializable(v) for v in value]
    return value


def _combine_patterns(patterns: Sequence[str]) -> str:
    wrapped = [f"(?:{pattern})" for pattern in patterns if pattern]
    return "|".join(wrapped)


def _get_date_formats_for_column(column_name: str) -> List[str]:
    rule = VALIDATION_RULES.get(column_name, {})
    formats: List[str] = []
    if isinstance(rule, dict):
        primary = rule.get("dateFormat")
        if primary:
            formats.append(primary)
        for fmt in rule.get("otherDateFormats", []) or []:
            if fmt and fmt not in formats:
                formats.append(fmt)
    fallback = DATE_FORMAT_LOOKUP.get(column_name)
    if fallback and fallback not in formats:
        formats.append(fallback)
    return formats


def _prepare_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.replace([None], np.nan, inplace=True)
    df = df.replace(r"^\s*$$", np.nan, regex=True)
    return df


def _run_column_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for column_name in sorted(VALIDATION_RULES.keys()):
        rule = VALIDATION_RULES[column_name]
        if not isinstance(rule, dict):
            continue
        column_type = rule.get("type")
        if not column_type or column_name not in df.columns:
            continue
        series = df[column_name]
        column_checks: List[Dict[str, Any]] = []
        lower_type = str(column_type).lower()

        if rule.get("missingDetectFlag"):
            try:
                special_missing = list(rule.get("specialMissingValueList") or [])
                if lower_type == "numeric":
                    result = numeric_missing(series, numeric_missing_values=special_missing)
                elif lower_type == "date":
                    result = date_missing(series, special_missing_values=special_missing)
                else:
                    result = character_missing(series, special_missing_values=special_missing)
                missing_dict = result.get("missingDict") if isinstance(result, dict) else None
                indices = _normalize_indices(missing_dict.get("index", [])) if isinstance(missing_dict, dict) else []
                column_checks.append(
                    {
                        "rule": "missing",
                        "invalid_indices": indices,
                        "details": _to_serializable(missing_dict),
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "missing", "error": str(exc)})

        if rule.get("duplicateDetectFlag"):
            try:
                duplicate_indices = detect_duplicate(series)
                column_checks.append(
                    {
                        "rule": "duplicate",
                        "invalid_indices": _normalize_indices(duplicate_indices),
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "duplicate", "error": str(exc)})

        if rule.get("format"):
            try:
                combined_pattern = _combine_patterns(rule.get("format", []))
                if combined_pattern:
                    invalid_indices = detect_format(series, combined_pattern)
                    column_checks.append(
                        {
                            "rule": "format",
                            "invalid_indices": _normalize_indices(invalid_indices),
                            "pattern": combined_pattern,
                        }
                    )
            except Exception as exc:
                column_checks.append({"rule": "format", "error": str(exc)})

        if isinstance(rule.get("range"), list) and rule["range"]:
            try:
                if lower_type == "date":
                    main_format = rule.get("dateFormat") or DATE_FORMAT_LOOKUP.get(column_name)
                    other_formats = rule.get("otherDateFormats", []) or []
                    invalid_indices = detect_date_range(series, rule["range"], main_format, other_formats)
                else:
                    invalid_indices = detect_numeric_range(series, rule["range"])
                column_checks.append(
                    {
                        "rule": "range",
                        "invalid_indices": _normalize_indices(invalid_indices),
                        "ranges": rule["range"],
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "range", "error": str(exc)})

        if rule.get("outlierRange"):
            try:
                invalid_indices = detect_numeric_range(series, [rule["outlierRange"]])
                column_checks.append(
                    {
                        "rule": "outlier",
                        "invalid_indices": _normalize_indices(invalid_indices),
                        "range": rule["outlierRange"],
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "outlier", "error": str(exc)})

        order_condition = rule.get("orderCondition") or {}
        has_order = isinstance(order_condition, dict) and any(
            order_condition.get(key)
            for key in ("firstOrderColumn", "secondOrderColumn", "thirdOrderColumn")
        )
        difference_block = rule.get("difference") or {}

        if has_order and difference_block.get("difference"):
            try:
                invalid_pairs = detect_absolute_difference(
                    df,
                    column_name,
                    order_condition,
                    difference_block["difference"],
                    TABLE_FORMAT_DICT,
                )
                column_checks.append(
                    {
                        "rule": "absoluteDifference",
                        "invalid_pairs": _to_serializable(invalid_pairs),
                        "invalid_indices": _normalize_indices(invalid_pairs_to_indices(invalid_pairs)),
                        "threshold": difference_block["difference"],
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "absoluteDifference", "error": str(exc)})

        if has_order and difference_block.get("relativeDifference"):
            try:
                invalid_pairs = detect_relative_difference(
                    df,
                    column_name,
                    order_condition,
                    difference_block["relativeDifference"],
                    TABLE_FORMAT_DICT,
                )
                column_checks.append(
                    {
                        "rule": "relativeDifference",
                        "invalid_pairs": _to_serializable(invalid_pairs),
                        "invalid_indices": _normalize_indices(invalid_pairs_to_indices(invalid_pairs)),
                        "threshold": difference_block["relativeDifference"],
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "relativeDifference", "error": str(exc)})

        if has_order and rule.get("sequenceRule"):
            try:
                invalid_pairs = detect_sequence(
                    df,
                    column_name,
                    order_condition,
                    rule["sequenceRule"],
                    TABLE_FORMAT_DICT,
                )
                column_checks.append(
                    {
                        "rule": "sequence",
                        "invalid_pairs": _to_serializable(invalid_pairs),
                        "invalid_indices": _normalize_indices(invalid_pairs_to_indices(invalid_pairs)),
                    }
                )
            except Exception as exc:
                column_checks.append({"rule": "sequence", "error": str(exc)})

        if column_checks:
            results.append({"column": column_name, "checks": column_checks})

    return results


def _condition_logic_entries() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for key in ("conditionLogicColumnList", "multipleConditionLogicColumnList"):
        block = VALIDATION_RULES.get(key)
        if isinstance(block, list):
            entries.extend([entry for entry in block if isinstance(entry, dict)])
    return entries


def _build_condition_constraints(entry: Dict[str, Any]) -> List[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    column_types = entry.get("columnType", {}) or {}
    parsed: List[Tuple[List[Dict[str, Any]], Dict[str, Any]]] = []
    for item in entry.get("conditionAndLogicList", []) or []:
        condition_list: List[Dict[str, Any]] = []
        for condition in item.get("conditionColumnValue", []) or []:
            for column, values in condition.items():
                condition_list.append(
                    {
                        "conditionColumn": column,
                        "conditionType": column_types.get(column, "EqualityBased"),
                        "conditionContent": values,
                    }
                )
        for constraint in item.get("constraintColumnValue", []) or []:
            for column, values in constraint.items():
                constraint_type = column_types.get(column, "EqualityBased")
                if constraint_type == "RangeBased":
                    normalized = []
                    target = values if isinstance(values, list) else [values]
                    for entry_value in target:
                        normalized.append(
                            {
                                "start": entry_value.get("start"),
                                "end": entry_value.get("end"),
                                "startInclusive": entry_value.get("startInclusive", True),
                                "endInclusive": entry_value.get("endInclusive", True),
                            }
                        )
                    constraint_content = normalized
                else:
                    constraint_content = values
                parsed.append(
                    (
                        list(condition_list),
                        {
                            "constraintColumn": column,
                            "constraintType": constraint_type,
                            "constraintContent": constraint_content,
                        },
                    )
                )
    return parsed


def _run_condition_logic_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for entry in _condition_logic_entries():
        condition_columns = entry.get("conditionColumns", []) or []
        constraint_columns = entry.get("constraintColumns", []) or []
        involved = [*condition_columns, *constraint_columns]
        if not involved or not all(col in df.columns for col in involved):
            continue
        try:
            constraints = _build_condition_constraints(entry)
            if not constraints:
                continue
            invalid_indices = detect_logic_condition_mod(df, constraints)
            results.append(
                {
                    "rule": "conditionLogic",
                    "columns": involved,
                    "conditionColumns": condition_columns,
                    "constraintColumns": constraint_columns,
                    "invalid_indices": _normalize_indices(sorted(list(invalid_indices))),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "rule": "conditionLogic",
                    "columns": involved,
                    "error": str(exc),
                }
            )
    return results


def _run_multi_difference_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for spec in VALIDATION_RULES.get("multiDifference", []) or []:
        columns = spec.get("columns", []) or []
        difference_dict = spec.get("differenceDict")
        order_condition = spec.get("orderCondition", {}) or {}
        if not columns or not difference_dict:
            continue
        if not all(col in df.columns for col in columns):
            continue
        try:
            invalid_pairs = detect_multi_difference(
                df,
                columns,
                order_condition,
                difference_dict,
                TABLE_FORMAT_DICT,
            )
            results.append(
                {
                    "rule": "multiDifference",
                    "columns": columns,
                    "invalid_pairs": _to_serializable(invalid_pairs),
                    "invalid_indices": _normalize_indices(invalid_pairs_to_indices(invalid_pairs)),
                    "threshold": difference_dict,
                }
            )
        except Exception as exc:
            results.append({"rule": "multiDifference", "columns": columns, "error": str(exc)})
    return results


def _run_multi_duplicate_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for columns in VALIDATION_RULES.get("multipleDuplicateColumnsList", []) or []:
        if not isinstance(columns, list) or len(columns) < 2:
            continue
        if not all(col in df.columns for col in columns):
            continue
        try:
            invalid_indices = detect_multi_duplicate([df[col] for col in columns])
            results.append(
                {
                    "rule": "multiDuplicate",
                    "columns": columns,
                    "invalid_indices": _normalize_indices(invalid_indices),
                }
            )
        except Exception as exc:
            results.append({"rule": "multiDuplicate", "columns": columns, "error": str(exc)})
    return results


def _run_numeric_compare_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for spec in VALIDATION_RULES.get("numericCompareList", []) or []:
        column1 = spec.get("column1")
        column2 = spec.get("column2")
        relation = spec.get("compareRelation")
        if not column1 or not column2 or not relation:
            continue
        if column1 not in df.columns or column2 not in df.columns:
            continue
        try:
            invalid_indices = detect_compare_numeric([df[column1], df[column2]], relation)
            results.append(
                {
                    "rule": "numericCompare",
                    "columns": [column1, column2],
                    "relation": relation,
                    "invalid_indices": _normalize_indices(invalid_indices),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "rule": "numericCompare",
                    "columns": [column1, column2],
                    "error": str(exc),
                }
            )
    return results


def _run_date_compare_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for spec in VALIDATION_RULES.get("dateCompareList", []) or []:
        column1 = spec.get("column1")
        column2 = spec.get("column2")
        relation = spec.get("compareRelation")
        if not column1 or not column2 or not relation:
            continue
        if column1 not in df.columns or column2 not in df.columns:
            continue
        try:
            formats = [
                _get_date_formats_for_column(column1),
                _get_date_formats_for_column(column2),
            ]
            invalid_indices = detect_compare_date(
                [df[column1], df[column2]], relation, formats
            )
            results.append(
                {
                    "rule": "dateCompare",
                    "columns": [column1, column2],
                    "relation": relation,
                    "invalid_indices": _normalize_indices(invalid_indices),
                    "formats": formats,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "rule": "dateCompare",
                    "columns": [column1, column2],
                    "error": str(exc),
                }
            )
    return results


def _run_lookup_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for spec in VALIDATION_RULES.get("lookupList", []) or []:
        parent_column = spec.get("parentColumnName")
        child_column = spec.get("childColumnName")
        lookup_pairs = spec.get("lookupList", [])
        if not parent_column or not child_column or not lookup_pairs:
            continue
        if parent_column not in df.columns or child_column not in df.columns:
            continue
        try:
            invalid_indices = detect_lookup(df[parent_column], df[child_column], lookup_pairs)
            results.append(
                {
                    "rule": "lookup",
                    "columns": [parent_column, child_column],
                    "invalid_indices": _normalize_indices(invalid_indices),
                    "pairs": lookup_pairs,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "rule": "lookup",
                    "columns": [parent_column, child_column],
                    "error": str(exc),
                }
            )
    return results


def _run_substring_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for spec in VALIDATION_RULES.get("substringList", []) or []:
        child_column = spec.get("childColumn")
        parent_column = spec.get("parentColumn")
        if not child_column or not parent_column:
            continue
        if child_column not in df.columns or parent_column not in df.columns:
            continue
        try:
            invalid_indices = detect_substring_character([df[child_column], df[parent_column]])
            results.append(
                {
                    "rule": "substring",
                    "columns": [child_column, parent_column],
                    "invalid_indices": _normalize_indices(invalid_indices),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "rule": "substring",
                    "columns": [child_column, parent_column],
                    "error": str(exc),
                }
            )
    return results


def _run_all_multi_column_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    results.extend(_run_numeric_compare_rules(df))
    results.extend(_run_date_compare_rules(df))
    results.extend(_run_condition_logic_rules(df))
    results.extend(_run_multi_difference_rules(df))
    results.extend(_run_multi_duplicate_rules(df))
    results.extend(_run_lookup_rules(df))
    results.extend(_run_substring_rules(df))
    return results


def _resolve_csv_path(cli_value: Optional[str]) -> Path:
    if cli_value:
        candidate = Path(cli_value).expanduser().resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"CSV file not found: {candidate}")
    if DEFAULT_CSV_PATH.exists():
        return DEFAULT_CSV_PATH
    raise FileNotFoundError(
        "Default CSV path is unavailable. Provide --csv to specify the dataset."
    )


def _resolve_output_path(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    return Path.cwd() / DEFAULT_RESULT_NAME


def _summarize(results: Dict[str, Any]) -> None:
    column_total = len(results.get("column_rules", []))
    multi_total = len(results.get("multi_column_rules", []))
    print(f"[dataset] {results.get('dataset')} :: {results.get('csv_path')}")
    print(f"[summary] column rules={column_total} multi rules={multi_total}")
    for entry in results.get("column_rules", []):
        column = entry.get("column")
        for check in entry.get("checks", []):
            invalid = len(check.get("invalid_indices") or check.get("invalid_pairs") or [])
            print(f"  - {column} :: {check.get('rule')} => {invalid} issues")
    for entry in results.get("multi_column_rules", []):
        invalid = len(entry.get("invalid_indices") or entry.get("invalid_pairs") or [])
        print(
            f"  - {entry.get('rule')} :: {', '.join(entry.get('columns', []))} => {invalid} issues"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the active dataset with the exported Watchtower rules."
    )
    parser.add_argument("--csv", help="Path to the CSV data file.")
    parser.add_argument(
        "--output",
        help="Path to the JSON report. Defaults to ./" + DEFAULT_RESULT_NAME,
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Suppress the console summary output.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    csv_path = _resolve_csv_path(args.csv)
    output_path = _resolve_output_path(args.output)
    df = _prepare_dataframe(csv_path)
    column_rules = _run_column_checks(df)
    multi_rules = _run_all_multi_column_rules(df)
    results = {
        "dataset": DATASET_LABEL,
        "csv_path": str(csv_path),
        "generated_at": SCRIPT_GENERATED_AT,
        "column_rules": column_rules,
        "multi_column_rules": multi_rules,
    }
    serializable = _to_serializable(results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[output] Results saved to {output_path}")
    if not args.no_summary:
        _summarize(serializable)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[error] {exc}")
        sys.exit(1)
"""
)


def build_detection_script(
    csv_path: Optional[str],
    rule_path: Optional[str],
    table_info_path: Optional[str],
    dataset_name: str,
) -> Tuple[str, str]:
    if not csv_path:
        raise ValueError("CSV data path is not configured. Please select a dataset first.")
    if not os.path.exists(csv_path):
        raise ValueError(f"CSV file not found: {csv_path}")
    if not rule_path:
        raise ValueError("Validation rule path is not configured.")
    if not os.path.exists(rule_path):
        raise ValueError(f"Validation rule file not found: {rule_path}")

    dataset_display = dataset_name or "dataset"
    dataset_slug = dataset_display.replace(" ", "_")
    script_timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    with open(rule_path, "r", encoding="utf-8") as source:
        validation_rules = json.load(source)
    validation_rules_str = json.dumps(validation_rules, ensure_ascii=True, indent=2)

    date_format_lookup: Dict[str, str] = {}
    if table_info_path and os.path.exists(table_info_path):
        try:
            with open(table_info_path, "r", encoding="utf-8") as table_file:
                table_info = json.load(table_file)
            for column, metadata in table_info.items():
                if isinstance(metadata, dict):
                    main_format = metadata.get("mainFormat")
                    if main_format:
                        date_format_lookup[column] = main_format
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[detection-script] Failed to parse table info: {exc}")
    date_format_str = json.dumps(date_format_lookup, ensure_ascii=True, indent=2)

    default_output = f"detection_results_{dataset_slug}_{script_timestamp}.json"

    script_content = DETECTION_SCRIPT_TEMPLATE.substitute(
        csv_path=json.dumps(csv_path),
        dataset_label_comment=dataset_display,
        dataset_label_literal=json.dumps(dataset_display),
        default_output=json.dumps(default_output),
        timestamp_comment=script_timestamp,
        timestamp_literal=json.dumps(script_timestamp),
        validation_rules=repr(validation_rules_str),
        date_formats=repr(date_format_str),
        runtime_helpers=RUNTIME_HELPERS,
    )

    filename = f"detect_functions_{dataset_slug}_{script_timestamp}.py"
    return script_content, filename
