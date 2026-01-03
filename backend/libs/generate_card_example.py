import pandas as pd
import numpy as np
from json_parser import *
import json


def _normalize_numeric_bound(value):
    """Convert range rule boundary to float, returning None when missing."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        value = stripped
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric_value):
        return None
    return numeric_value


def _format_numeric(value):
    if value is None:
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if value.is_integer():
            return str(int(value))
        value_str = f"{value}"
        if "." in value_str:
            value_str = value_str.rstrip("0").rstrip(".")
        return value_str
    return str(value)


def _format_interval_text(start, end, start_inclusive, end_inclusive):
    start_label = _format_numeric(start) if start is not None else "-inf"
    end_label = _format_numeric(end) if end is not None else "+inf"
    start_bracket = "[" if start is not None and start_inclusive else "("
    end_bracket = "]" if end is not None and end_inclusive else ")"
    return f"{start_bracket}{start_label}, {end_label}{end_bracket}"


def _in_numeric_bounds(value, lower, lower_inclusive, upper, upper_inclusive):
    if lower is not None:
        if lower_inclusive:
            if value < lower:
                return False
        else:
            if value <= lower:
                return False
    if upper is not None:
        if upper_inclusive:
            if value > upper:
                return False
        else:
            if value >= upper:
                return False
    return True

def generate_card_example(new_json_file_path, csv_file_path, column_name, rule_type):
    """
    Generate example card content based on rule type.

    Args:
        new_json_file_path: Path to the rule JSON file.
        csv_file_path: Path to the CSV file.
        column_name: Target column name list, e.g., ['ball_status'].
        rule_type: Rule type, e.g., 'Sequence'.

    Returns:
        str: Example text for the card.
    """

    if rule_type == "Sequence":
        # Ensure column_name is a non-empty list
        if not isinstance(column_name, list) or not column_name:
            return "Error: column_name should be a non-empty list"
        
        # Get sequence rules for the first column
        first_column = column_name[0]
        sequence_rules = load_sequence_rule_json(new_json_file_path, first_column)
        
        # If no rules are found, return empty string
        if not sequence_rules:
            return f"Sequence rules for {first_column} not found"
        
        # Select up to three example pairs
        examples = []
        count = 0
        
        for rule in sequence_rules:
            value = rule.get("value", "")
            allowed_next_list = rule.get("allowed_next", [])
            
            if allowed_next_list:
                # Pick the first allowed next value
                for next_value in allowed_next_list[:1]:
                    examples.append(f"{value} -> {next_value}")
                    count += 1
                    if count >= 3:
                        break
            
            if count >= 3:
                break
        
        return f"The sequence relationship within the {first_column}.; " + ", ".join(examples) + "..."
    
    elif rule_type == "Logical and condition":
        # Ensure column_name is a list with at least two elements
        if not isinstance(column_name, list) or len(column_name) < 2:
            return "Error: column_name should be a list with at least two elements"
        
        if len(column_name) > 2:
            # Handle cases with more than two columns
            if len(column_name) == 3:
                return f"{column_name[0]}, {column_name[1]} and {column_name[2]} exist mapping relations."
            else:
                # Handle cases with more than three columns
                column_list = ", ".join(column_name[:-1]) + f" and {column_name[-1]}"
                return f"{column_list} exist mapping relations."

        # Load condition logic rules
        conditions_constraints = load_condition_logic_json(new_json_file_path, column_name)
        
        # If no rules are found, return empty string
        if not conditions_constraints:
            return f"Condition logic rules for {', '.join(column_name)} not found"
        
        # Select the first rule as an example
        if conditions_constraints:
            condition_list, constraint_dict = conditions_constraints[0]
            
            # Check if all condition columns are EqualityBased
            all_condition_equality_based = True
            for condition in condition_list:
                if condition["conditionType"] != "EqualityBased":
                    all_condition_equality_based = False
                    break
            
            # Build condition text
            condition_parts = []
            for condition in condition_list:
                condition_column = condition["conditionColumn"]
                condition_values = condition["conditionContent"]
                condition_values_str = ", ".join([f'"{v}"' for v in condition_values])
                condition_parts.append(f"{condition_column} is {condition_values_str}")
            
            condition_str = " and ".join(condition_parts)
            
            # Handle constraint section
            constraint_column = constraint_dict["constraintColumn"]
            constraint_type = constraint_dict["constraintType"]
            
            if constraint_type == "EqualityBased":
                # Handle EqualityBased constraint
                constraint_values = constraint_dict["constraintContent"]
                constraint_values_str = ", ".join([f'"{v}"' for v in constraint_values])
                return f'When {condition_str}, then {constraint_column} can be {constraint_values_str}.'
            
            elif constraint_type == "RangeBased":
                # Handle RangeBased constraints
                constraint_content = constraint_dict["constraintContent"]
                if isinstance(constraint_content, list) and len(constraint_content) > 0:
                    range_item = constraint_content[0]
                    start = range_item.get("start")
                    end = range_item.get("end")
                    start_inclusive = range_item.get("startInclusive", True)
                    end_inclusive = range_item.get("endInclusive", True)
                    
                    # Use brackets depending on inclusivity
                    start_bracket = "[" if start_inclusive else "("
                    end_bracket = "]" if end_inclusive else ")"
                    
                    return f'When {condition_str}, then the range of {constraint_column} needs to be {start_bracket}{start}, {end}{end_bracket}.'
                else:
                    # 如果约束内容不是预期的格式
                    return f'When {condition_str}, then {constraint_column} has range constraints (details unavailable).'
            
            else:
                # Handle other constraint types
                return f'When {condition_str}, then {constraint_column} has constraints of type {constraint_type}.'
        
        return "logic and condition rule example not found"
    
    elif rule_type == "Lookup":
        # Ensure column_name is a list with two elements
        if not isinstance(column_name, list) or len(column_name) != 2:
            return "Error: column_name should be a list with two elements"
        
        # Load lookup rules
        lookup_rules = load_lookup_list(new_json_file_path, column_name)
        
        # If no rules are found, return empty string
        if not lookup_rules:
            return f"Lookup rules for {', '.join(column_name)} not found"
        
        # Select the first rule as an example
        if lookup_rules and len(lookup_rules) > 0:
            lookup_rule = lookup_rules[0]
            parent_value = lookup_rule.get("parentValue", "")
            child_value_list = lookup_rule.get("childValueList", [])
            
            # Determine parent and child columns
            parent_column = None
            child_column = None
            
            # Iterate through lookup_list to find a matching rule
            with open(new_json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for lookup_item in data.get("lookupList", []):
                if set([lookup_item["parentColumnName"], lookup_item["childColumnName"]]) == set(column_name):
                    parent_column = lookup_item["parentColumnName"]
                    child_column = lookup_item["childColumnName"]
                    break
            
            if parent_column and child_column:
                # Format child value list
                child_values_str = ", ".join([f'"{v}"' for v in child_value_list])
                
                # Build example
                return f'When {parent_column} is "{parent_value}", then {child_column} can be [{child_values_str}].'
            else:
                return f"Unable to determine parent-child relationship for {', '.join(column_name)}"
        
        return "Suitable lookup rule example not found"
    
    elif rule_type == "Difference":
        # Ensure column_name is a non-empty list
        if not isinstance(column_name, list) or not column_name:
            return "Error: column_name should be a non-empty list"
        
        # Target column
        target_column = column_name[0]
        
        # Load difference rules
        difference_rule = load_absolute_difference_json(new_json_file_path, target_column)
        
        if not difference_rule:
            return f"Difference rule for {target_column} not found"
        
        # Get range bounds
        start = _normalize_numeric_bound(difference_rule.get("start"))
        end = _normalize_numeric_bound(difference_rule.get("end"))
        start_inclusive = difference_rule.get("startInclusive", True)
        end_inclusive = difference_rule.get("endInclusive", True)

        if start is None and end is None:
            return f"{target_column} difference rule lacks valid bounds"
        
        # Prepare interval text
        interval_text = _format_interval_text(start, end, start_inclusive, end_inclusive)
        
        # Read CSV data
        try:
            df = pd.read_csv(csv_file_path)
            
            # Ensure target column exists
            if target_column not in df.columns:
                return f"CSV file is missing column: {target_column}"
            
            # Convert column to numeric
            df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
            
            # Drop NaN values
            df = df.dropna(subset=[target_column])
            
            # Calculate differences between adjacent rows
            df['diff'] = df[target_column].diff().abs()
            
            # Find adjacent rows that satisfy the rule
            valid_diffs = []
            
            for i in range(1, len(df)):
                diff = df['diff'].iloc[i]
                val1 = df[target_column].iloc[i-1]
                val2 = df[target_column].iloc[i]
                
                # Check if difference is within bounds
                if _in_numeric_bounds(diff, start, start_inclusive, end, end_inclusive):
                    valid_diffs.append((val1, val2, diff))
                
                # Two examples are enough
                if len(valid_diffs) >= 2:
                    break
            
            # Build examples
            examples = []
            for val1, val2, diff in valid_diffs:
                # Pick comparison symbols based on inclusivity
                start_symbol = "<=" if start_inclusive else "<"
                end_symbol = "<=" if end_inclusive else "<"
                start_display = _format_numeric(start) if start is not None else ""
                end_display = _format_numeric(end) if end is not None else ""

                if val1 > val2:
                    # Format example expression
                    diff_expr = f"{_format_numeric(val1)}-{_format_numeric(val2)}"
                else:
                    # Format example expression
                    diff_expr = f"{_format_numeric(val2)}-{_format_numeric(val1)}"

                if start is not None and end is not None:
                    examples.append(f"{start_display} {start_symbol} {diff_expr} {end_symbol} {end_display}")
                elif start is None:
                    examples.append(f"{diff_expr} {end_symbol} {end_display}")
                else:
                    examples.append(f"{start_display} {start_symbol} {diff_expr}")
            
            if not examples:
                examples.append(f"{interval_text} includes the difference of adjacent values")
            
            return f"The difference of {target_column} needs to be in {interval_text}.; " + ", ".join(examples) + "..."
            
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return f"The difference of {target_column} needs to be in {interval_text}."
    
    elif rule_type == "Range":
        # Ensure column_name is a non-empty list
        if not isinstance(column_name, list) or not column_name:
            return "Error: column_name should be a non-empty list"
        
        # Target column
        target_column = column_name[0]
        
        # Load range rules
        range_rules = load_range_rule_json(new_json_file_path, target_column)
        if not range_rules:
            return f"Outlier range rule for {target_column} not found"

        range_rule = range_rules[0]

        # Get bounds
        start = _normalize_numeric_bound(range_rule.get("start"))
        end = _normalize_numeric_bound(range_rule.get("end"))
        start_inclusive = range_rule.get("startInclusive", True)
        end_inclusive = range_rule.get("endInclusive", True)

        if start is None and end is None:
            return f"{target_column} range rule lacks valid bounds"

        interval_text = _format_interval_text(start, end, start_inclusive, end_inclusive)

        # Determine comparison symbols
        start_symbol = "<=" if start_inclusive else "<"
        end_symbol = "<=" if end_inclusive else "<"
        
        # Read CSV data
        try:
            df = pd.read_csv(csv_file_path)
            
            # Ensure target column exists
            if target_column not in df.columns:
                return f"CSV file is missing column: {target_column}"
            
            # Convert column to numeric
            df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
            
            # Drop NaN values
            df = df.dropna(subset=[target_column])
            
            # Find values within bounds
            valid_values = []
            
            for i in range(len(df)):
                val = df[target_column].iloc[i]
                
                # Check if value is within bounds
                if _in_numeric_bounds(val, start, start_inclusive, end, end_inclusive):
                    valid_values.append(val)
                
                # Two examples are enough
                if len(valid_values) >= 2:
                    break
            
            # Build examples
            examples = []
            for val in valid_values:
                val_display = _format_numeric(val)
                if start is not None and end is not None:
                    start_display = _format_numeric(start)
                    end_display = _format_numeric(end)
                    examples.append(f"{start_display}{start_symbol}{val_display}{end_symbol}{end_display}")
                elif start is None:
                    end_display = _format_numeric(end)
                    examples.append(f"{val_display}{end_symbol}{end_display}")
                else:
                    start_display = _format_numeric(start)
                    examples.append(f"{start_display}{start_symbol}{val_display}")
            
            if not examples:
                examples.append(f"value should be within the {interval_text} range")
            
            return f"The range of {target_column} needs to be in {interval_text}.; " + ", ".join(examples) + "..."
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return f"The range of {target_column} needs to be in {interval_text}."
        
    elif rule_type == "Outlier":
        # Ensure column_name is a non-empty list
        if not isinstance(column_name, list) or not column_name:
            return "Error: column_name should be a non-empty list"
        
        # Target column
        target_column = column_name[0]
        
        # Load outlier rules
        outlier_rule = load_outlier_rule_json(new_json_file_path, target_column)
        
        if not outlier_rule:
            return f"Outlier range rule for {target_column} not found"
        
        # Get bounds
        start = _normalize_numeric_bound(outlier_rule.get("start"))
        end = _normalize_numeric_bound(outlier_rule.get("end"))
        start_inclusive = outlier_rule.get("startInclusive", True)
        end_inclusive = outlier_rule.get("endInclusive", True)

        if start is None and end is None:
            return f"{target_column} range rule lacks valid bounds"

        interval_text = _format_interval_text(start, end, start_inclusive, end_inclusive)

        # Determine comparison symbols
        start_symbol = "<=" if start_inclusive else "<"
        end_symbol = "<=" if end_inclusive else "<"
        
        # Read CSV data
        try:
            df = pd.read_csv(csv_file_path)
            
            # Ensure target column exists
            if target_column not in df.columns:
                return f"CSV file is missing column: {target_column}"
            
            # Convert column to numeric
            df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
            
            # Drop NaN values
            df = df.dropna(subset=[target_column])
            
            # Find values within bounds
            valid_values = []
            
            for i in range(len(df)):
                val = df[target_column].iloc[i]
                
                # Check if value is within bounds
                if _in_numeric_bounds(val, start, start_inclusive, end, end_inclusive):
                    valid_values.append(val)
                
                # Two examples are enough
                if len(valid_values) >= 2:
                    break
            
            # Build examples
            examples = []
            for val in valid_values:
                val_display = _format_numeric(val)
                if start is not None and end is not None:
                    start_display = _format_numeric(start)
                    end_display = _format_numeric(end)
                    examples.append(f"{start_display}{start_symbol}{val_display}{end_symbol}{end_display}")
                elif start is None:
                    end_display = _format_numeric(end)
                    examples.append(f"{val_display}{end_symbol}{end_display}")
                else:
                    start_display = _format_numeric(start)
                    examples.append(f"{start_display}{start_symbol}{val_display}")
            
            if not examples:
                examples.append(f"Values need to be within the range of {interval_text}")
            
            return f"The outlier range of {target_column} needs to be in {interval_text}.; " + ", ".join(examples) + "..."
            
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return f"The outlier range of {target_column} needs to be in {interval_text}."
    
    elif rule_type == "Compare":
        if not isinstance(column_name, list) or len(column_name) != 2:
            return "Error: column_name should be a list containing two elements"

        compare_relation = load_compare_relation(new_json_file_path, column_name)
        if not compare_relation:
            return f"Comparison rule for {', '.join(column_name)} not found"

        column1, column2 = column_name
        
        # Determine comparison symbol
        if compare_relation == "smaller":
            compare_symbol = "<"
        elif compare_relation == "larger":
            compare_symbol = ">"
        elif compare_relation == "equal":
            compare_symbol = "="
        elif compare_relation == "smaller_equal":
            compare_symbol = "<="
        elif compare_relation == "larger_equal":
            compare_symbol = ">="
        elif compare_relation == "not_equal":
            compare_symbol = "≠"
        else:
            compare_symbol = "?"
        
        # Read CSV data
        try:
            df = pd.read_csv(csv_file_path)
            
            # Ensure both columns exist
            if column1 not in df.columns or column2 not in df.columns:
                missing_columns = []
                if column1 not in df.columns:
                    missing_columns.append(column1)
                if column2 not in df.columns:
                    missing_columns.append(column2)
                return f"CSV file is missing columns: {', '.join(missing_columns)}"
            
            def normalize_series(series: pd.Series) -> pd.Series:
                numeric_series = pd.to_numeric(series, errors='coerce')
                if numeric_series.notna().any():
                    return numeric_series
                datetime_series = pd.to_datetime(series, errors='coerce')
                if datetime_series.notna().any():
                    return datetime_series
                return numeric_series

            df[column1] = normalize_series(df[column1])
            df[column2] = normalize_series(df[column2])
            
            # Drop rows with NaN in either column
            df = df.dropna(subset=[column1, column2])
            
            # Find rows that satisfy the compare rule
            valid_pairs = []
            
            for i in range(len(df)):
                val1 = df[column1].iloc[i]
                val2 = df[column2].iloc[i]
                
                # Check if values satisfy the rule
                if compare_relation == "smaller" and val1 < val2:
                    valid_pairs.append((val1, val2))
                elif compare_relation == "larger" and val1 > val2:
                    valid_pairs.append((val1, val2))
                elif compare_relation == "equal" and val1 == val2:
                    valid_pairs.append((val1, val2))
                elif compare_relation == "smaller_equal" and val1 <= val2:
                    valid_pairs.append((val1, val2))
                elif compare_relation == "larger_equal" and val1 >= val2:
                    valid_pairs.append((val1, val2))
                elif compare_relation == "not_equal" and val1 != val2:
                    valid_pairs.append((val1, val2))
                else:
                    continue

                # Two examples are enough
                if len(valid_pairs) >= 2:
                    break
            
            # Build examples
            examples = []
            for val1, val2 in valid_pairs:
                examples.append(f"{val1}{compare_symbol}{val2}")
            
            if not examples:
                examples.append(f"{column1}{compare_symbol}{column2}")
            
            relation_text = {
                "smaller": "smaller than",
                "larger": "larger than",
                "equal": "equal to",
                "smaller_equal": "smaller than or equal to",
                "larger_equal": "larger than or equal to",
                "not_equal": "not equal to",
            }.get(compare_relation, compare_relation)
            
            return f"The value of {column1} needs to be {relation_text} {column2}.; " + ", ".join(examples) + "..."
            
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            relation_text = {
                "smaller": "smaller than",
                "larger": "larger than",
                "equal": "equal to",
                "smaller_equal": "smaller than or equal to",
                "larger_equal": "larger than or equal to",
                "not_equal": "not equal to",
            }.get(compare_relation, compare_relation)
            return f"The value of {column1} needs to be {relation_text} {column2}."
    
    # Additional rule types can be handled here
    return "Unknown rule type."