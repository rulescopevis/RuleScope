import copy
from typing import Dict, List
import os
import sys

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from rule_refiner.refine_range import refine_range

def validate_condition_logic_data(conditionLogicColumnDict: Dict, selectValueList: List[Dict]) -> tuple[List[Dict], List[Dict], List[Dict]]:
    """Validate if data conforms to condition and logic rules, return valid, invalid and unmatched lists"""
    valid_list = []
    invalid_list = []
    unmatched_list = []
    
    condition_columns = conditionLogicColumnDict["conditionColumns"]
    constraint_columns = conditionLogicColumnDict["constraintColumns"]
    column_types = conditionLogicColumnDict["columnType"]
    
    for select_value in selectValueList:
        matches_condition = False
        matches_constraint = False
        
        # Check each condition and logic rule
        for logic_item in conditionLogicColumnDict["conditionAndLogicList"]:
            # First check if condition matches
            all_conditions_match = True
            for condition_col in condition_columns:
                if condition_col not in select_value:
                    all_conditions_match = False
                    break
                    
                col_type = column_types[condition_col]
                value = select_value[condition_col]
                
                if col_type == "EqualityBased":
                    for item in logic_item["conditionColumnValue"]:
                        if condition_col in item.keys():
                            current_values = item[condition_col]
                            if value not in current_values:
                                all_conditions_match = False
                            break
                        else:
                            continue
                else:  # RangeBased
                    range_info = logic_item["conditionColumnValue"][0][condition_col]
                    if not ((range_info["startInclusive"] and value >= range_info["start"] or
                            not range_info["startInclusive"] and value > range_info["start"]) and
                           (range_info["endInclusive"] and value <= range_info["end"] or
                            not range_info["endInclusive"] and value < range_info["end"])):
                        all_conditions_match = False
                        break
            
            if all_conditions_match:
                matches_condition = True
                
                # If condition matches, check constraint
                all_constraints_match = True
                for constraint_col in constraint_columns:
                    if constraint_col not in select_value:
                        all_constraints_match = False
                        break
                        
                    col_type = column_types[constraint_col]
                    value = select_value[constraint_col]
                    
                    if col_type == "EqualityBased":
                        current_values = logic_item["constraintColumnValue"][0][constraint_col]
                        if value not in current_values:
                            all_constraints_match = False
                            break
                    else:  # RangeBased
                        range_info = logic_item["constraintColumnValue"][0][constraint_col]
                        if not ((range_info["startInclusive"] and value >= range_info["start"] or
                                not range_info["startInclusive"] and value > range_info["start"]) and
                               (range_info["endInclusive"] and value <= range_info["end"] or
                                not range_info["endInclusive"] and value < range_info["end"])):
                            all_constraints_match = False
                            break
                
                if all_constraints_match:
                    matches_constraint = True
                    break
        
        # Only consider data validity when condition matches
        if matches_condition:
            if matches_constraint:
                valid_list.append(select_value)
            else:
                invalid_list.append(select_value)
        else:
            unmatched_list.append(select_value)
    
    return valid_list, invalid_list, unmatched_list

def refine_condition_and_logic(conditionLogicColumnDict: Dict, 
                                    validFlag: bool, 
                                    selectValueList: List[Dict]) -> Dict:
    result = {
        "refineStatus": False,
        "originalConditionAndLogicDict": None,
        "refineConditionAndLogicList": []
    }
    
    # If selectValueList is empty, return directly
    if not selectValueList:
        return result
        
    # Handle empty conditionLogicColumnDict case
    if not conditionLogicColumnDict:
        if not validFlag:
            return result
            
        # When validFlag is True, generate new rules from data
        if len(selectValueList) < 2:  # Need at least two records to generate rules
            return result
            
        # Get all column names from first record
        columns = list(selectValueList[0].keys())
        if len(columns) < 2:  # Need at least two columns to generate rules
            return result
            
        # Determine data type for each column
        column_types = {}
        for col in columns:
            # Check if all values are numeric
            is_numeric = all(isinstance(item.get(col), (int, float)) 
                           for item in selectValueList if item.get(col) is not None)
            column_types[col] = "RangeBased" if is_numeric else "EqualityBased"
        
        # Create rules for each pair of columns
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                condition_col = columns[i]
                constraint_col = columns[j]
                
                # Create new rule
                new_rule = {
                    "conditionColumns": [condition_col],
                    "constraintColumns": [constraint_col],
                    "columnType": {
                        condition_col: column_types[condition_col],
                        constraint_col: column_types[constraint_col]
                    },
                    "conditionAndLogicList": []
                }
                
                # Generate rules based on column types
                if column_types[condition_col] == "EqualityBased":
                    # Collect all unique condition values
                    condition_values = list(set(item[condition_col] 
                                             for item in selectValueList 
                                             if item.get(condition_col) is not None))
                    
                    if column_types[constraint_col] == "EqualityBased":
                        # Collect all unique constraint values
                        constraint_values = list(set(item[constraint_col] 
                                                  for item in selectValueList 
                                                  if item.get(constraint_col) is not None))
                        
                        logic_item = {
                            "conditionColumnValue": [{
                                condition_col: condition_values
                            }],
                            "constraintColumnValue": [{
                                constraint_col: constraint_values
                            }]
                        }
                    else:  # RangeBased constraint
                        constraint_values = [item[constraint_col] 
                                          for item in selectValueList 
                                          if item.get(constraint_col) is not None]
                        min_val = min(constraint_values)
                        max_val = max(constraint_values)
                        
                        logic_item = {
                            "conditionColumnValue": [{
                                condition_col: condition_values
                            }],
                            "constraintColumnValue": [{
                                constraint_col: {
                                    "start": min_val,
                                    "end": max_val,
                                    "startInclusive": True,
                                    "endInclusive": True
                                }
                            }]
                        }
                else:  # RangeBased condition
                    condition_values = [item[condition_col] 
                                     for item in selectValueList 
                                     if item.get(condition_col) is not None]
                    min_condition = min(condition_values)
                    max_condition = max(condition_values)
                    
                    if column_types[constraint_col] == "EqualityBased":
                        constraint_values = list(set(item[constraint_col] 
                                                  for item in selectValueList 
                                                  if item.get(constraint_col) is not None))
                        
                        logic_item = {
                            "conditionColumnValue": [{
                                condition_col: {
                                    "start": min_condition,
                                    "end": max_condition,
                                    "startInclusive": True,
                                    "endInclusive": True
                                }
                            }],
                            "constraintColumnValue": [{
                                constraint_col: constraint_values
                            }]
                        }
                    else:  # RangeBased constraint
                        constraint_values = [item[constraint_col] 
                                          for item in selectValueList 
                                          if item.get(constraint_col) is not None]
                        min_constraint = min(constraint_values)
                        max_constraint = max(constraint_values)
                        
                        logic_item = {
                            "conditionColumnValue": [{
                                condition_col: {
                                    "start": min_condition,
                                    "end": max_condition,
                                    "startInclusive": True,
                                    "endInclusive": True
                                }
                            }],
                            "constraintColumnValue": [{
                                constraint_col: {
                                    "start": min_constraint,
                                    "end": max_constraint,
                                    "startInclusive": True,
                                    "endInclusive": True
                                }
                            }]
                        }
                
                new_rule["conditionAndLogicList"].append(logic_item)
                result["refineConditionAndLogicList"].append(new_rule)
                
                # Create reverse rule
                reverse_rule = {
                    "conditionColumns": [constraint_col],
                    "constraintColumns": [condition_col],
                    "columnType": {
                        condition_col: column_types[condition_col],
                        constraint_col: column_types[constraint_col]
                    },
                    "conditionAndLogicList": [{
                        "conditionColumnValue": logic_item["constraintColumnValue"],
                        "constraintColumnValue": logic_item["conditionColumnValue"]
                    }]
                }
                result["refineConditionAndLogicList"].append(reverse_rule)
        
        result["refineStatus"] = True
        return result
    
    # Validate data
    valid_list, invalid_list, unmatched_list = validate_condition_logic_data(conditionLogicColumnDict, selectValueList)
    
    # Select working list based on validFlag
    if validFlag:
        if invalid_list:  # Records match rules but constraints don't satisfy
            working_list = invalid_list
        elif unmatched_list:  # No rules matched, add new rules
            condition_columns = conditionLogicColumnDict["conditionColumns"]
            constraint_columns = conditionLogicColumnDict["constraintColumns"]
            column_types = conditionLogicColumnDict["columnType"]

            new_logic_item = {"conditionColumnValue": [{}], "constraintColumnValue": [{}]}

            # Construct condition column values/ranges
            for condition_col in condition_columns:
                col_type = column_types[condition_col]
                values = [item.get(condition_col) for item in unmatched_list if item.get(condition_col) is not None]
                if not values:
                    continue
                if col_type == "EqualityBased":
                    new_logic_item["conditionColumnValue"][0][condition_col] = list(set(values))
                else:
                    new_logic_item["conditionColumnValue"][0][condition_col] = {
                        "start": min(values),
                        "end": max(values),
                        "startInclusive": True,
                        "endInclusive": True
                    }

            # Construct constraint column values/ranges
            for constraint_col in constraint_columns:
                col_type = column_types[constraint_col]
                values = [item.get(constraint_col) for item in unmatched_list if item.get(constraint_col) is not None]
                if not values:
                    continue
                if col_type == "EqualityBased":
                    new_logic_item["constraintColumnValue"][0][constraint_col] = list(set(values))
                else:
                    new_logic_item["constraintColumnValue"][0][constraint_col] = {
                        "start": min(values),
                        "end": max(values),
                        "startInclusive": True,
                        "endInclusive": True
                    }

            if new_logic_item["conditionColumnValue"][0] and new_logic_item["constraintColumnValue"][0]:
                result["refineStatus"] = True
                result["refineConditionAndLogicList"].append(new_logic_item)
            return result
        else:
            return result
    else:
        if not valid_list:  # If no valid data
            return result
        working_list = valid_list
    
    # Get all condition and constraint column names
    condition_columns = conditionLogicColumnDict["conditionColumns"]
    constraint_columns = conditionLogicColumnDict["constraintColumns"]
    
    # Get types of all columns
    column_types = conditionLogicColumnDict["columnType"]
    
    # Find matching conditions and constraints
    for logic_item in conditionLogicColumnDict["conditionAndLogicList"]:
        all_conditions_match = True
        
        # Check if all condition columns match
        for condition_col in condition_columns:
            column_match = False
            col_type = column_types[condition_col]
            
            # Get values of current column from working_list
            select_values = [item[condition_col] for item in working_list]
            
            if col_type == "EqualityBased":
                for item in logic_item["conditionColumnValue"]:
                    if condition_col in item.keys():
                        current_values = item[condition_col]
                        if any(val in current_values for val in select_values):
                            column_match = True
            else:  # RangeBased
                for item in logic_item["conditionColumnValue"]:
                    if condition_col in item.keys():
                        range_info = item[condition_col]
                        for val in select_values:
                            if (range_info["startInclusive"] and val >= range_info["start"] or
                                not range_info["startInclusive"] and val > range_info["start"]) and \
                            (range_info["endInclusive"] and val <= range_info["end"] or
                                not range_info["endInclusive"] and val < range_info["end"]):
                                column_match = True
                                break
            
            if not column_match:
                all_conditions_match = False
                break
        
        if all_conditions_match:
            # Save original logic item
            result["originalConditionAndLogicDict"] = copy.deepcopy(logic_item)
            
            # Create new logic item for modification
            new_logic_item = copy.deepcopy(logic_item)
            changes_made = False
            
            # Process modification for each constraint column
            for constraint_col in constraint_columns:
                col_type = column_types[constraint_col]
                constraint_values = [item[constraint_col] for item in working_list]
                
                if col_type == "EqualityBased":
                    current_values = new_logic_item["constraintColumnValue"][0][constraint_col]
                    if validFlag:
                        # Add new constraint values to list
                        new_values = list(set(current_values + constraint_values))
                        if len(new_values) != len(current_values):
                            changes_made = True
                        new_logic_item["constraintColumnValue"][0][constraint_col] = new_values
                    else:
                        # Remove current constraint values from list
                        new_values = [v for v in current_values if v not in constraint_values]
                        if len(new_values) != len(current_values):
                            changes_made = True
                        new_logic_item["constraintColumnValue"][0][constraint_col] = new_values
                
                else:  # RangeBased
                    current_range_list = [logic_item["constraintColumnValue"][0][constraint_col]]
                    dataType = 'datetime' if isinstance(constraint_values[0], str) and \
                              ('T' in constraint_values[0] or ':' in constraint_values[0]) else 'numeric'
                    
                    refine_result = refine_range(
                        rangeList=current_range_list,
                        dataType=dataType,
                        validFlag=validFlag,
                        selectValueList=constraint_values
                    )
                    
                    if refine_result["refineStatus"]:
                        changes_made = True
                        # Check if multi-segment ranges are needed
                        if len(refine_result["refineRangeList"]) > 1 and validFlag:
                            # For validFlag=True, we only need one expanded range
                            start = min(r["start"] if isinstance(r, dict) else r[0]["start"] 
                                      for r in refine_result["refineRangeList"])
                            end = max(r["end"] if isinstance(r, dict) else r[0]["end"] 
                                    for r in refine_result["refineRangeList"])
                            new_range = {
                                "start": start,
                                "end": end,
                                "startInclusive": True,
                                "endInclusive": True
                            }
                            new_logic_item["constraintColumnValue"][0][constraint_col] = new_range
                            if not result["refineConditionAndLogicList"]:
                                result["refineConditionAndLogicList"].append(new_logic_item)
                        else:
                            # Handle single range or validFlag=False case
                            for new_range in refine_result["refineRangeList"]:
                                temp_item = copy.deepcopy(new_logic_item)
                                if isinstance(new_range, list):
                                    temp_item["constraintColumnValue"][0][constraint_col] = new_range[0]
                                else:
                                    temp_item["constraintColumnValue"][0][constraint_col] = new_range
                                result["refineConditionAndLogicList"].append(temp_item)

            if changes_made and not result["refineConditionAndLogicList"]:
                result["refineConditionAndLogicList"].append(new_logic_item)
            
            result["refineStatus"] = changes_made
            break
                    
    return result