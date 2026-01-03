import json
import os
import pandas as pd
import sys
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)
# from json_parser import load_condition_logic_json

def detect_logic_condition(dataframe, conditionList, constraintDict):
    """
    Optimized version: Use vectorized operations to detect rows in dataframe that do not meet logical conditions.
    
    Args:
        dataframe: Data table
        conditionList: List of conditional column information
        constraintDict: Information of constrained columns
        
    Returns:
        Index list of rows that do not meet logical conditions
    """
    # Initialize condition mask - all rows are assumed to meet conditions by default
    condition_mask = pd.Series(True, index=dataframe.index)

    # Vectorized processing of all conditions
    for condition in conditionList:
        condition_column = condition["conditionColumn"]
        condition_type = condition["conditionType"]
        condition_content = condition["conditionContent"]
        
        # Get the values of this column
        column_values = dataframe[condition_column]
        
        # Null handling - rows with null values do not meet conditions
        condition_mask &= ~column_values.isna()
        
        # Perform vectorized checks based on condition type
        if condition_type == "EqualityBased":
            # Vectorized equality check
            condition_mask &= column_values.isin(condition_content)
            
        elif condition_type == "RangeBased":
            # Vectorized range check
            range_mask = pd.Series(False, index=dataframe.index)

            for range_dict in condition_content:
                start = range_dict.get('start')
                end = range_dict.get('end')
                start_inclusive = range_dict.get('startInclusive', True)
                end_inclusive = range_dict.get('endInclusive', True)

                # Create mask for the current range
                temp_mask = pd.Series(True, index=dataframe.index)

                # Vectorized boundary check
                if start is not None:
                    if start_inclusive:
                        temp_mask &= column_values >= start
                    else:
                        temp_mask &= column_values > start

                if end is not None:
                    if end_inclusive:
                        temp_mask &= column_values <= end
                    else:
                        temp_mask &= column_values < end

                # Accumulate range mask (OR operation)
                range_mask |= temp_mask

            condition_mask &= range_mask

    # Only check constraints for rows that meet all conditions
    constraint_column = constraintDict["constraintColumn"]
    constraint_type = constraintDict["constraintType"]
    constraint_content = constraintDict["constraintContent"]

    # Get values of constraint column
    constraint_values = dataframe[constraint_column]

    # Initialize constraint mask
    constraint_mask = pd.Series(False, index=dataframe.index)

    if constraint_type == "EqualityBased":
        # Vectorized constraint check
        constraint_mask = constraint_values.isin(constraint_content)
        
    elif constraint_type == "RangeBased":
        for range_dict in constraint_content:
            start = range_dict.get('start')
            end = range_dict.get('end')
            start_inclusive = range_dict.get('startInclusive', True)
            end_inclusive = range_dict.get('endInclusive', True)

            temp_mask = pd.Series(True, index=dataframe.index)

            if start is not None:
                if start_inclusive:
                    temp_mask &= constraint_values >= start
                else:
                    temp_mask &= constraint_values > start

            if end is not None:
                if end_inclusive:
                    temp_mask &= constraint_values <= end
                else:
                    temp_mask &= constraint_values < end

            constraint_mask |= temp_mask
    
    # Identify violating rows: rows that meet conditions but do not meet constraints (including rows where constraint column is null)
    invalid_mask = condition_mask & (~constraint_mask | constraint_values.isna())

    # Return violating indices
    return sorted(dataframe.index[invalid_mask].tolist())

def detect_logic_condition_mod(dataframe, conditions_constraints):
    """
    Vectorized detection of row indices in dataframe that do not meet logical conditions.
    If there are missing values in columns involved in calculations, skip them.
    
    Args:
        dataframe: Data table (pd.DataFrame)
        conditions_constraints: List of condition and constraint combinations, each item is (conditionList, constraintDict)

    Returns:
        List of indices that do not meet logical conditions
    """
    # Initialize mask for all rows to False
    overall_invalid_mask = pd.Series(False, index=dataframe.index)

    # Iterate through each condition and constraint pair
    for condition_list, constraint_dict in conditions_constraints:
        # Initialize condition mask to True
        condition_mask = pd.Series(True, index=dataframe.index)

        # Initialize null mask to False (indicating no null values)
        has_null_mask = pd.Series(False, index=dataframe.index)

        # Iterate through condition_list, processing each condition
        for condition in condition_list:
            column = condition["conditionColumn"]

            # Check for null values and mark them if present
            has_null_mask |= dataframe[column].isna()

            if condition["conditionType"] == "EqualityBased":
                # Equality-based condition check
                # Convert data and condition content to strings for comparison
                column_data = dataframe[column].astype(str)
                condition_content_str = [str(item) for item in condition["conditionContent"]]
                condition_mask &= column_data.isin(condition_content_str)
            elif condition["conditionType"] == "RangeBased":
                # Range-based condition check
                range_mask = pd.Series(False, index=dataframe.index)
                for range_dict in condition["conditionContent"]:
                    start = range_dict.get("start")
                    end = range_dict.get("end")
                    start_inclusive = range_dict.get("startInclusive", True)
                    end_inclusive = range_dict.get("endInclusive", True)


                    # Construct range condition
                    temp_mask = pd.Series(True, index=dataframe.index)
                    if start is not None:
                        if start_inclusive:
                            temp_mask &= dataframe[column] >= start
                        else:
                            temp_mask &= dataframe[column] > start
                    if end is not None:
                        if end_inclusive:
                            temp_mask &= dataframe[column] <= end
                        else:
                            temp_mask &= dataframe[column] < end

                    # Accumulate range check
                    range_mask |= temp_mask


                # Update condition mask
                condition_mask &= range_mask

        # Check if constraint column has null values
        constraint_column = constraint_dict["constraintColumn"]
        has_null_mask |= dataframe[constraint_column].isna()

        # Exclude rows with null values
        valid_rows_mask = ~has_null_mask

        # Initialize constraint mask
        constraint_mask = pd.Series(False, index=dataframe.index)

        if constraint_dict["constraintType"] == "EqualityBased":
            # Equality-based constraint check
            # Convert data and constraint content to strings for comparison
            column_data = dataframe[constraint_column].astype(str)
            constraint_content_str = [str(item) for item in constraint_dict["constraintContent"] if item is not None]
            constraint_mask = column_data.isin(constraint_content_str)

            # If constraint_dict["constraintContent"] contains None, treat NaN as a valid value
            if None in constraint_dict["constraintContent"]:
                constraint_mask |= dataframe[constraint_column].isna()
        elif constraint_dict["constraintType"] == "RangeBased":
            # Range-based constraint check
            for range_dict in constraint_dict["constraintContent"]:
                start = range_dict.get("start")
                end = range_dict.get("end")
                start_inclusive = range_dict.get("startInclusive", True)
                end_inclusive = range_dict.get("endInclusive", True)


                # Construct range condition
                temp_mask = pd.Series(True, index=dataframe.index)
                if start is not None:
                    if start_inclusive:
                        temp_mask &= dataframe[constraint_column] >= start
                    else:
                        temp_mask &= dataframe[constraint_column] > start
                if end is not None:
                    if end_inclusive:
                        temp_mask &= dataframe[constraint_column] <= end
                    else:
                        temp_mask &= dataframe[constraint_column] < end

                # Accumulate range check
                constraint_mask |= temp_mask

        # Find invalid rows under the current condition and constraint combination (conditions met but constraints not met)
        # Only consider rows that pass condition checks and have no null values
        invalid_mask = condition_mask & valid_rows_mask & ~constraint_mask

        # Update overall invalid mask
        overall_invalid_mask |= invalid_mask


    # Return indices of invalid rows
    return sorted(dataframe.index[overall_invalid_mask])

def detect_logic_condition_mod_1(dataframe, conditions_constraints):
     """
     Vectorized detection of row indices in dataframe that do not meet logical conditions.
     If there are missing values in columns involved in calculations, skip them.
     
     Args:
         dataframe: Data table (pd.DataFrame)
         conditions_constraints: List of condition and constraint combinations, each item is (conditionList, constraintDict)
 
     Returns:
         List of indices that do not meet logical conditions
     """
     # Initialize mask for all rows to False
     overall_invalid_mask = pd.Series(False, index=dataframe.index)
 
     # Iterate through each condition and constraint pair
     for condition_list, constraint_dict in conditions_constraints:
         # Initialize condition mask to True
         condition_mask = pd.Series(True, index=dataframe.index)
 
         # Iterate through condition_list, processing each condition
         for condition in condition_list:
             column = condition["conditionColumn"]
             if condition["conditionType"] == "EqualityBased":
                 # Equality-based condition check
                 condition_mask &= dataframe[column].isin(condition["conditionContent"])
             elif condition["conditionType"] == "RangeBased":
                 # Range-based condition check
                 range_mask = pd.Series(False, index=dataframe.index)
                 for range_dict in condition["conditionContent"]:
                     start = range_dict.get("start")
                     end = range_dict.get("end")
                     start_inclusive = range_dict.get("startInclusive", True)
                     end_inclusive = range_dict.get("endInclusive", True)
 

                     # Construct range condition
                     temp_mask = pd.Series(True, index=dataframe.index)
                     if start is not None:
                         if start_inclusive:
                             temp_mask &= dataframe[column] >= start
                         else:
                             temp_mask &= dataframe[column] > start
                     if end is not None:
                         if end_inclusive:
                             temp_mask &= dataframe[column] <= end
                         else:
                             temp_mask &= dataframe[column] < end

                     # Accumulate range check
                     range_mask |= temp_mask

                 # Update condition mask
                 condition_mask &= range_mask

         # If all conditions are met, then check constraints
         constraint_column = constraint_dict["constraintColumn"]
         constraint_mask = pd.Series(True, index=dataframe.index)
 
         if constraint_dict["constraintType"] == "EqualityBased":
             # Equality-based constraint check
             constraint_mask = dataframe[constraint_column].isin(constraint_dict["constraintContent"])
             # If dataframe[constraint_column] is NaN and constraint_dict["constraintContent"] contains None
             if constraint_dict["constraintContent"] == [None]:
                 constraint_mask |= dataframe[constraint_column].isna()
         elif constraint_dict["constraintType"] == "RangeBased":
             # Range-based constraint check
             range_mask = pd.Series(False, index=dataframe.index)
             for range_dict in constraint_dict["constraintContent"]:
                 start = range_dict.get("start")
                 end = range_dict.get("end")
                 start_inclusive = range_dict.get("startInclusive", True)
                 end_inclusive = range_dict.get("endInclusive", True)
 

                 # Construct range condition
                 temp_mask = pd.Series(True, index=dataframe.index)
                 if start is not None:
                     if start_inclusive:
                         temp_mask &= dataframe[constraint_column] >= start
                     else:
                         temp_mask &= dataframe[constraint_column] > start
                 if end is not None:
                     if end_inclusive:
                         temp_mask &= dataframe[constraint_column] <= end
                     else:
                         temp_mask &= dataframe[constraint_column] < end

                 # Accumulate range check
                 range_mask |= temp_mask

             # Update constraint mask
             constraint_mask = range_mask

         # Find invalid rows under the current condition and constraint combination
         invalid_mask = condition_mask & ~constraint_mask
         overall_invalid_mask |= invalid_mask

     # Return indices of invalid rows
     return sorted(dataframe.index[overall_invalid_mask])


def detect_multiple_logic_condition(dataframe, conditions_constraints):
    """
    Vectorized detection of row indices in dataframe that do not match any defined valid combination.

    New logic: Treat each logic item as a complete "valid combination". If a row of data cannot match
    any valid combination defined in conditions_constraints, and the row has complete data (can be judged)
    on at least one combination's required columns, then the row is considered non-compliant.

    Args:
        dataframe: Data table (pd.DataFrame)
        conditions_constraints: List of multi-column condition and constraint combinations, where each combination is now treated as a complete valid rule.

    Returns:
         tuple: (Index list of rows that do not meet logical conditions, Formatted logic rule list)
    """
    # ==================================================================
    # Function 1: Format conditionAndLogicList (this part remains unchanged)
    # The design of this part is generic, merging each logic item's conditions and constraints into a dictionary,
    # representing a complete rule.
    # ==================================================================
    formatted_logic_list = []
    for logic_item in conditions_constraints["conditionAndLogicList"]:
        current_rule = {}
        # Merge condition columns and values
        for condition_dict in logic_item["conditionColumnValue"]:
            current_rule.update(condition_dict)
        # Merge constraint columns and values
        for constraint_dict in logic_item["constraintColumnValue"]:
            current_rule.update(constraint_dict)
        formatted_logic_list.append(current_rule)

    # ==================================================================
    # Function 2: Detect rows that do not meet conditions based on new logic
    # Core idea: Identify all "valid" rows, then find those that are "judgeable" but "invalid".
    # ==================================================================
    
    column_types = conditions_constraints["columnType"]

    # Initialize two core masks
    # 1. is_judgeable_mask: Mark rows with complete data on at least one rule's required columns
    is_judgeable_mask = pd.Series(False, index=dataframe.index)
    # 2. rows_with_any_valid_rule: Mark rows that match at least one complete rule
    rows_with_any_valid_rule = pd.Series(False, index=dataframe.index)

    # Iterate through each "valid combination" rule
    for logic_item in conditions_constraints["conditionAndLogicList"]:
        # current_rule_matches: Mark rows that match all parts of the current rule
        current_rule_matches = pd.Series(True, index=dataframe.index)
        # rule_has_null_mask: Mark rows with missing values in the current rule's required columns
        rule_has_null_mask = pd.Series(False, index=dataframe.index)

        # Treat the original condition and constraint as a combined part of the rule
        all_columns_in_rule = logic_item["conditionColumnValue"] + logic_item["constraintColumnValue"]

        for col_val_dict in all_columns_in_rule:
            for col, values in col_val_dict.items():
                # Check and accumulate the current rule's null mask
                rule_has_null_mask |= dataframe[col].isna()

                # Calculate matching mask based on column type
                if column_types[col] == "EqualityBased":
                    # Exact match
                    values_str = [str(v).strip() for v in values]
                    col_data_str = dataframe[col].astype(str).str.strip()
                    current_rule_matches &= col_data_str.isin(values_str)

                elif column_types[col] == "RangeBased":
                    # Range match
                    range_mask = pd.Series(False, index=dataframe.index)
                    for range_dict in values:
                        start, end = range_dict.get("start"), range_dict.get("end")
                        start_inc, end_inc = range_dict.get("startInclusive", True), range_dict.get("endInclusive", True)

                        temp_mask = pd.Series(True, index=dataframe.index)
                        if start is not None:
                            temp_mask &= dataframe[col].ge(start) if start_inc else dataframe[col].gt(start)
                        if end is not None:
                            temp_mask &= dataframe[col].le(end) if end_inc else dataframe[col].lt(end)
                        range_mask |= temp_mask
                    current_rule_matches &= range_mask

        # Update global masks
        # If a row has no null values on the current rule's required columns, then it is "judgeable"
        is_judgeable_mask |= ~rule_has_null_mask

        # If a row matches all parts of the current rule and has no null values on these columns,
        # then it is a "compliant" row.
        rows_with_any_valid_rule |= (current_rule_matches & ~rule_has_null_mask)

    # Final logic: Non-compliant rows are those that are "judgeable" but do not satisfy any compliant rule
    overall_invalid_mask = is_judgeable_mask & ~rows_with_any_valid_rule
    
    invalid_indices = sorted(dataframe.index[overall_invalid_mask].tolist())

    return invalid_indices, formatted_logic_list

# Parse conditions from JSON
def load_condition_logic_json(condition_json_file, selectedColumns):
    # Read local JSON file
    with open(condition_json_file, 'r') as file:
        condition_logic_data = json.load(file)

    parsed_conditions = []

    for logic in condition_logic_data["conditionLogicColumnList"]:
        # Check if all selected columns are included
        if all(col in logic["conditionColumns"] + logic["constraintColumns"] for col in selectedColumns):
            # Construct condition_list and constraint_dict for each conditionAndLogicList item
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

                # Build constraint dictionary
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

                # Add to results
                for constraint_dict in constraint_dict_list:
                    parsed_conditions.append((condition_list, constraint_dict))

    return parsed_conditions

def load_multiple_condition_logic(json_path, column_names):
    """
    Load multi-column condition logic rules from a specified JSON file.
    
    Parameters:
        json_path: Path to the JSON file
        column_names: List of column names to read, e.g., ['County', 'City']
    
    Returns:
        dict: Dictionary containing multi-column condition logic rules, or None if no matching rule is found
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Get multi-column condition logic list
        multiple_condition_logic_list = data.get("multipleConditionLogicColumnList", [])

        # Iterate through multi-column condition logic list to find matching column combinations
        for logic_rule in multiple_condition_logic_list:
            condition_columns = logic_rule.get("conditionColumns", [])
            constraint_columns = logic_rule.get("constraintColumns", [])

            # Check if condition columns and constraint columns include all specified column names
            if all(col in condition_columns + constraint_columns for col in column_names):
                return logic_rule

        # If no matching rule is found, return None
        return None

    except Exception as e:
        print(f"Error loading multi-column condition logic: {str(e)}")
        return None