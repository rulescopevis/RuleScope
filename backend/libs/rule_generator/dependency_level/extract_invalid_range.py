import json

def extract_invalid_range(conditions_constraints):
    result = []

    for condition, constraint in conditions_constraints:
        if isinstance(condition, dict) and "conditionColumnValue" in condition:
            condition_column_value = condition["conditionColumnValue"][0]
            condition_key = list(condition_column_value.keys())[0]
            condition_content = condition_column_value[condition_key][0]
            
            constraint_column_value = condition["constraintColumnValue"][0]
            constraint_key = list(constraint_column_value.keys())[0]
            constraint_content = constraint_column_value[constraint_key]
            
            if isinstance(constraint_content, dict) and "start" in constraint_content:
                result.append({
                    'conditionContent': condition_content,
                    'start': constraint_content['start'],
                    'startInclusive': constraint_content['startInclusive'],
                    'end': constraint_content['end'],
                    'endInclusive': constraint_content['endInclusive']
                })
            else:
                result.append({
                    'conditionValue': condition_content,
                    'constraintValue': constraint_content
                })
        else:
            condition_type = condition[0]['conditionType']
            constraint_type = constraint['constraintType']
            
            if condition_type == 'EqualityBased' and constraint_type == 'EqualityBased':
                condition_content = condition[0]['conditionContent']
                condition_content_str = ', '.join(condition_content)
                
                constraint_content = constraint['constraintContent']
                if isinstance(constraint_content[0], list):
                    constraint_content = constraint_content[0]

                result.append({
                    'conditionValue': condition_content_str,
                    'constraintValue': constraint_content
                })
            
            elif condition_type == 'EqualityBased' and constraint_type == 'RangeBased':
                for item in condition:
                    condition_content = item['conditionContent'][0]
                    
                    for cons in constraint['constraintContent']:
                        start = cons['start']
                        end = cons['end']
                        startInclusive = cons['startInclusive']
                        endInclusive = cons['endInclusive']

                        result.append({
                            'conditionContent': condition_content,
                            'start': start,
                            'startInclusive': startInclusive,
                            'end': end,
                            'endInclusive': endInclusive
                        })
    return result

def sequence_invalid_range(sequence_rule):
    result = []
    for rule in sequence_rule:
        result.append({
            'conditionValue': rule['value'],
            'constraintValue': rule['allowed_next']
        })
    return result

def extract_lookup_area(json_file_path, column_names):
    """Extract lookup area information from a JSON file."""
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        
    lookup_list = json_data.get("lookupList", [])
    result = []
        
    for lookup_rule in lookup_list:
        if (lookup_rule.get("parentColumnName") == column_names[0] and 
            lookup_rule.get("childColumnName") == column_names[1]):
                
            for item in lookup_rule.get("lookupList", []):
                result.append({
                    "conditionValue": item.get("parentValue"),
                    "constraintValue": item.get("childValueList", [])
                })
            break
        
    return result

def load_condition_logic_json(condition_json_file, selectedColumns):
    with open(condition_json_file, 'r') as file:
        condition_logic_data = json.load(file)

    parsed_conditions = []

    for logic in condition_logic_data["conditionLogicColumnList"]:
        if all(col in logic["conditionColumns"] + logic["constraintColumns"] for col in selectedColumns):
            for logic_item in logic["conditionAndLogicList"]:
                condition_list = []
                for condition_col_val in logic_item["conditionColumnValue"]:
                    for col, values in condition_col_val.items():
                        condition_list.append({
                            "conditionColumn": col,
                            "conditionType": logic["columnType"][col],
                            "conditionContent": values
                        })
                
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
                
                for constraint_dict in constraint_dict_list:
                    parsed_conditions.append((condition_list, constraint_dict))

    return parsed_conditions
