from json_parser import *

def generate_original_rule(json_path, column_names: list[str], rule_type: str, rule_value: str) -> dict:
    """
    Build an original_rule object from the given parameters.

    Args:
        column_names: List of column names.
        rule_type: Rule type (Sequence/Difference/relativeDifference/Compare/Logical and condition).
        rule_value: Rule value.

    Returns:
        dict: Generated original_rule dictionary.
    """
    original_rule = {
        "ruleType": rule_type,
        "columnsList": column_names,
        "validationRule": {}
    }
    
    if rule_type == "Sequence":
        # Load sequence rules
        sequence_rules = load_sequence_rule_json(json_path, column_names[0])
        # Find the rule matching rule_value
        for rule in sequence_rules:
            if rule["value"] == rule_value:
                original_rule["validationRule"] = rule
                break
                
    elif rule_type == "Difference":
        # Load absolute difference rule
        difference = load_absolute_difference_json(json_path, column_names[0])
        original_rule["validationRule"] = difference
        
    elif rule_type == "relativeDifference":
        # Load relative difference rule
        relative_difference = load_relative_difference_json(json_path, column_names[0])
        original_rule["validationRule"] = relative_difference
        
    elif rule_type == "Compare":
        # Load compare rule
        compare_relation = load_compare_relation(json_path, column_names)
        if compare_relation:
            original_rule["validationRule"] = {
                "compareRelation": compare_relation
            }
        
    elif rule_type == "Logical and condition":
        # Load logical condition rules
        conditions_constraints = load_condition_logic_json(json_path, column_names)

        # Find the rule that matches rule_value
        for condition_tuple in conditions_constraints:
            condition_list, constraint_dict = condition_tuple
            # Check whether condition list contains rule_value
            for condition in condition_list:
                if rule_value in condition["conditionContent"]:
                    original_rule["validationRule"] = {
                        "conditionColumnValue": [
                            {condition["conditionColumn"]: condition["conditionContent"]}
                        ],
                        "constraintColumnValue": [
                            {constraint_dict["constraintColumn"]: constraint_dict["constraintContent"][0]}
                        ]
                    }
                    break
    
    elif rule_type == "Lookup":
        # Load lookup rules
        lookup_rules = load_lookup_list(json_path, column_names)
        if lookup_rules:
            original_rule["validationRule"] = {
                "parentColumnName": column_names[0],
                "childColumnName": column_names[1],
                "lookupList": lookup_rules
            }
    
    return original_rule
