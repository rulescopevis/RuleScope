import json
from typing import List
import os
import sys

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

def load_column_data(json_path, column_name):
    """
    Read column_data from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.

    Returns:
        list: valueList.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    value_list = data[column_name]["valueList"]

    return value_list

def load_missing_duplicate_detect_flag(json_path, column_name):
    """
    Read missing/duplicate detect flags from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data[column_name]["missingDetectFlag"], data[column_name]["duplicateDetectFlag"]

def load_missing_duplicate_flag(json_path, column_name):
    """
    Read missing/duplicate flags from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.

    Returns:
        missing_flag, duplicate_flag: boolean, boolean.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data[column_name]["missingValueFlag"], data[column_name]["duplicateFlag"]

def load_special_missing_values(json_file_path, column_name):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)
    special_missing_values = json_data.get(column_name, {}).get("specialMissingValueList", [''])
    return special_missing_values

def parse_json_result(text):
    # Attempt direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If direct parse fails, try to clean Markdown formatting
        try:
            if '```json' in text:
                text = text.split('```json')[-1]
            if '```' in text:
                text = text.split('```')[0]
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError as e:
            print("Failed to parse JSON after cleaning:", e)
            print("Cleaned text:", text)
            raise

def load_sequence_rule_json(json_path, column_name):
    """
    Read sequenceRule config from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_status'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data[column_name]["sequenceRule"]

def load_sort_conditions(json_path, column_name):
    """
    Read sort_conditions config from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_status'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data[column_name]["orderCondition"]

def load_decimal_json(json_path, column_name):
    """
    Read decimal config from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_status'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data[column_name]["decimal"]

def load_absolute_difference_json(json_path, column_name):
    """
    Read absolute difference config from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_status'.

    Returns:
        difference.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    difference = data[column_name]["difference"]["difference"]
    return difference

def load_relative_difference_json(json_path, column_name):
    """
    Read relative difference config from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_status'.

    Returns:
        difference.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    relative_difference = data[column_name]["difference"]["relativeDifference"]
    return relative_difference

def load_range_rule_json(json_path, column_name):
    """
    Read range rules from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data[column_name]["range"]

def load_outlier_rule_json(json_path, column_name):
    """
    Read outlier range rules from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data[column_name]["outlierRange"]

def load_outlier_method_json(json_path, column_name):
    """
    Read outlier method from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_name: Target field name, e.g., 'ball_x'.

    Returns:
        list: Rule list.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data[column_name]["outlierFunction"]

def load_condition_logic_json(condition_json_file, selectedColumns):
    # Read local JSON file
    with open(condition_json_file, 'r') as file:
        condition_logic_data = json.load(file)

    parsed_conditions = []

    for logic in condition_logic_data["conditionLogicColumnList"]:
        # Check whether all selected columns are included
        if all(col in logic["conditionColumns"] + logic["constraintColumns"] for col in selectedColumns):
            # Build condition_list and constraint_dict per conditionAndLogicList item
            for logic_item in logic["conditionAndLogicList"]:
                # Build condition list
                condition_list = []
                for condition_col_val in logic_item["conditionColumnValue"]:
                    for col, values in condition_col_val.items():
                        condition_list.append({
                            "conditionColumn": col,
                            "conditionType": logic["columnType"][col],
                            "conditionContent": values
                        })
                
                # Build constraint dict
                constraint_dict_list = []
                for constraint_col_val in logic_item["constraintColumnValue"]:
                    for col, values in constraint_col_val.items():
                        if logic["columnType"][col] == "RangeBased":
                            constraint_dict = {
                                "constraintColumn": col,
                                "constraintType": logic["columnType"][col],
                                "constraintContent": [
                                    {
                                        "start": range_val["start"],
                                        "end": range_val["end"],
                                        "startInclusive": range_val.get("startInclusive", True),
                                        "endInclusive": range_val.get("endInclusive", True)
                                    } for range_val in values
                                ] if isinstance(values, list) else [values]
                            }
                        else:  # EqualityBased
                            constraint_dict = {
                                "constraintColumn": col,
                                "constraintType": logic["columnType"][col],
                                "constraintContent": values
                            }
                        constraint_dict_list.append(constraint_dict)
                
                # Append to result
                for constraint_dict in constraint_dict_list:
                    parsed_conditions.append((condition_list, constraint_dict))

    return parsed_conditions

def get_opposite_compare_type(compare_type):
    opposite_types = {
        "larger": "smaller",
        "larger_equal": "smaller_equal",
        "equal": "equal",
        "smaller": "larger",
        "smaller_equal": "larger_equal",
        "not_equal": "not_equal"
    }
    return opposite_types.get(compare_type, None)

def load_compare_numeric(json_path, selectedColumns):
    with open(json_path, 'r') as file:
        data= json.load(file)
    compare_numeric = data.get('numericCompareList', [])
    for compare_item in compare_numeric:
        if [compare_item["column1"], compare_item["column2"]] == selectedColumns:
            return compare_item["compareRelation"]
        
        elif [compare_item["column2"], compare_item["column1"]] == selectedColumns:
            opposite_compare_type = get_opposite_compare_type(compare_item["compareRelation"])
            return opposite_compare_type
    return None


def _load_date_formats_for_column(column_info: dict) -> List[str]:
    formats: List[str] = []
    date_format = column_info.get("dateFormat")
    if date_format:
        formats.append(date_format)

    other_formats = column_info.get("otherDateFormats", [])
    if isinstance(other_formats, list):
        formats.extend([fmt for fmt in other_formats if fmt])

    return formats


def load_compare_date(json_path, selectedColumns: List[str]):
    if len(selectedColumns) != 2:
        return None

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    compare_date = data.get('dateCompareList', [])

    for compare_item in compare_date:
        relation = None
        if [compare_item.get("column1"), compare_item.get("column2")] == selectedColumns:
            relation = compare_item.get("compareRelation")
        elif [compare_item.get("column2"), compare_item.get("column1")] == selectedColumns:
            relation = get_opposite_compare_type(compare_item.get("compareRelation"))

        if relation:
            column_formats: List[List[str]] = []
            for column in selectedColumns:
                column_info = data.get(column, {}) if isinstance(data.get(column, {}), dict) else {}
                column_formats.append(_load_date_formats_for_column(column_info))

            return {
                "compareRelation": relation,
                "columnFormats": column_formats,
            }

    return None


def load_compare_relation(json_path, selectedColumns: List[str]):
    """Load comparison relation, prefer numeric and fall back to date if needed."""

    numeric_relation = load_compare_numeric(json_path, selectedColumns)
    if numeric_relation:
        return numeric_relation

    date_relation = load_compare_date(json_path, selectedColumns)
    if date_relation:
        return date_relation.get("compareRelation")

    return None

def load_order_condition_json(json_path, column_name):
    # Read local JSON file
    with open(json_path, 'r') as file:
        data= json.load(file)
    order_condition = data[column_name]["orderCondition"]
    return order_condition

def load_multi_difference_order_condition_json(json_path, column_names):
    with open(json_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        for multi_diff in json_data.get('multiDifference', []):
            if set(multi_diff.get('columns', [])) == set(column_names):
                orderCondition = multi_diff.get('orderCondition', {})
                break
            else:
                orderCondition = {}
    return orderCondition

def invalid_pairs_to_indices(invalid_pairs):
    invalid_indices = set()
    
    for pair in invalid_pairs:
        invalid_indices.add(pair['currentIndex'])
        invalid_indices.add(pair['nextIndex'])
    
    return list(invalid_indices)

def invalid_pairs_to_sorted_indices(invalid_pairs):
    sorted_indices = []
    for pair in invalid_pairs:
        sorted_indices.append(pair['sortCurrentIndex'])
        sorted_indices.append(pair['sortNextIndex'])
    return sorted_indices

def load_lookup_list(json_path, column_names: List[str]):
    """
    Load lookup rules from the specified JSON file.

    Args:
        json_path (str): JSON file path.
        column_names (List[str]): Column names to read.

    Returns:
        dict: Lookup rule list, or None if not found.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for lookup_rule in data.get("lookupList", []):
        if set([lookup_rule["parentColumnName"], lookup_rule["childColumnName"]]) == set(column_names):
            return lookup_rule["lookupList"]

    return None

def load_multiple_condition_logic(json_path, column_names):
    """
    Load multi-column condition logic rules from the specified JSON file.

    Args:
        json_path: JSON file path.
        column_names: Column name list, e.g., ['County', 'City'].

    Returns:
        dict: Rule dict if found, otherwise None.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get multi-column condition logic list
        multiple_condition_logic_list = data.get("multipleConditionLogicColumnList", [])
        
        # Iterate the list to find matching column combinations
        for logic_rule in multiple_condition_logic_list:
            condition_columns = logic_rule.get("conditionColumns", [])
            constraint_columns = logic_rule.get("constraintColumns", [])
            
            # Check whether condition and constraint columns include all targets
            if all(col in condition_columns + constraint_columns for col in column_names):
                return logic_rule
        
        return None
    
    except Exception as e:
        print(f"Error loading multiple condition logic: {str(e)}")
        return None
def load_multi_difference_json(json_file_path, column_names: List[str]) -> List[float]:
    """
    Load multi-difference range from JSON.

    Args:
        json_file_path (str): JSON file path.
        column_names (List[str]): Column name list.

    Returns:
        List[float]: [min_diff, max_diff] difference range.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Check whether column names match
        for multi_diff in json_data.get("multiDifference", []):
            if set(multi_diff["columns"]) == set(column_names):
                return multi_diff["differenceDict"]
                
        raise ValueError(f"No difference rule found for columns {column_names}")
            
    except Exception as e:
        print(f"Error loading multi-difference from JSON: {str(e)}")
        raise
