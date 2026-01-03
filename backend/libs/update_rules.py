import json
from rule_generator.cell_level.character_info import *


def compare_condition_values(original_condition, current_condition):
    """Check whether two condition value lists match."""
    if len(original_condition) != len(current_condition):
        return False
    
    for i in range(len(original_condition)):
        orig = original_condition[i]
        curr = current_condition[i]
        
        if set(orig.keys()) != set(curr.keys()):
            return False
        
        for key in orig:
            if set(orig[key]) != set(curr[key]):
                return False
    
    return True

def update_validation_rules(new_json_file_path, rules_data, dataframe):
    """
    Update validation_rules.json based on received rule changes.

    Args:
        rules_data (dict): Contains updateRules, addRules, deleteRules.
    """
    try:
        with open(new_json_file_path, 'r', encoding='utf-8') as f:
            validation_data = json.load(f)

        if 'updateRules' in rules_data and rules_data['updateRules']:
            for rule in rules_data['updateRules']:
                column = rule.get('column')
                rule_type = rule.get('type')
                refine_rule = rule.get('refineRule')
                refine_example = rule.get('refine_example')
                original_rule = rule.get('originalRule')
                
                if isinstance(column, list) and len(column) == 1:
                    column = column[0]
                
                if rule_type == 'Lookup' and refine_rule:
                    if 'lookupList' not in validation_data:
                        validation_data['lookupList'] = []

                    orig_lookup = original_rule[0] if isinstance(original_rule, list) else original_rule or {}
                    refined_lookup = refine_rule[0] if isinstance(refine_rule, list) else refine_rule or {}
                    match_lookup = orig_lookup if orig_lookup else refined_lookup

                    found = False
                    for i, lookup_rule in enumerate(validation_data.get('lookupList', [])):
                        if (
                            lookup_rule.get('parentColumnName') == match_lookup.get('parentColumnName') and
                            lookup_rule.get('childColumnName') == match_lookup.get('childColumnName')
                        ):
                            validation_data['lookupList'][i] = refined_lookup
                            found = True
                            break
                    if not found and refined_lookup:
                        validation_data['lookupList'].append(refined_lookup)

                if rule_type == 'Missing' and isinstance(column, str) and column in validation_data:
                    if refine_rule:
                        if 'missingDetectFlag' in refine_rule:
                            validation_data[column]['missingDetectFlag'] = refine_rule['missingDetectFlag']
                        if 'specialMissingValueList' in refine_rule:
                            validation_data[column]['specialMissingValueList'] = refine_rule['specialMissingValueList']
                        has_standard_missing = dataframe[column].isnull().any() or dataframe[column].isna().any()
                        
                        if has_standard_missing:
                            validation_data[column]['missingValueFlag'] = True
                            break
                        if 'specialMissingValueList' in refine_rule and refine_rule['specialMissingValueList']:
                            special_missing_values = refine_rule['specialMissingValueList']
                            has_special_missing = dataframe[column].isin(special_missing_values).any()
                        if has_standard_missing:
                            validation_data[column]['missingValueFlag'] = True
                        elif 'has_special_missing' in locals() and has_special_missing:
                            validation_data[column]['missingValueFlag'] = True
                        else:
                            validation_data[column]['missingValueFlag'] = False
                        
                if rule_type == 'Compare' and refine_rule:
                    rule_columns = rule.get('column', []) or []
                    first_column = rule_columns[0] if rule_columns else None
                    column_type = (
                        validation_data.get(first_column, {}).get('type')
                        if first_column in validation_data
                        else None
                    )

                    list_key = 'numericCompareList'
                    if column_type == 'datetime':
                        list_key = 'dateCompareList'

                    if list_key not in validation_data:
                        validation_data[list_key] = []

                    target_list = validation_data.get(list_key, [])

                    if original_rule:
                        found = False
                        original_columns = [
                            original_rule[0].get('column1'),
                            original_rule[0].get('column2'),
                        ] if isinstance(original_rule, list) and original_rule else []

                        for compare_rule in target_list:
                            same_order = (
                                compare_rule.get('column1') == original_columns[0]
                                and compare_rule.get('column2') == original_columns[1]
                            )
                            reverse_order = (
                                compare_rule.get('column1') == original_columns[1]
                                and compare_rule.get('column2') == original_columns[0]
                            )

                            if same_order or reverse_order:
                                compare_rule.update(refine_rule[0])
                                found = True
                                break

                        if not found:
                            target_list.append(refine_rule[0])
                    else:
                        target_list.append(refine_rule[0])
                
                elif rule_type == 'Logical and condition' and refine_rule:
                    if len(column) == 2:
                        if 'conditionLogicColumnList' not in validation_data:
                            validation_data['conditionLogicColumnList'] = []
                        
                        condition_column_names = []
                        constraint_column_names = []
                        for col_value in (rule.get('originalRule') or {}).get('conditionColumnValue', []):
                            condition_column_names.extend(col_value.keys())
                        for col_value in (rule.get('originalRule') or {}).get('constraintColumnValue', []):
                            constraint_column_names.extend(col_value.keys())
                        if not condition_column_names and not constraint_column_names:
                            for col_value in refine_rule[0].get('conditionColumnValue', []):
                                condition_column_names.extend(col_value.keys())
                            for col_value in refine_rule[0].get('constraintColumnValue', []):
                                constraint_column_names.extend(col_value.keys())

                        matched_group = None
                        for condition_logic in validation_data.get('conditionLogicColumnList', []):
                            if (set(condition_logic.get('conditionColumns', [])) == set(condition_column_names) and 
                                set(condition_logic.get('constraintColumns', [])) == set(constraint_column_names)):
                                matched_group = condition_logic
                                break

                        if matched_group:
                            updated = False
                            for i, logic_rule in enumerate(matched_group.get('conditionAndLogicList', [])):
                                original_condition = (rule.get('originalRule') or {}).get('conditionColumnValue', [])
                                current_condition = logic_rule.get('conditionColumnValue', [])
                                if compare_condition_values(original_condition, current_condition):
                                    matched_group['conditionAndLogicList'][i] = refine_rule[0]
                                    updated = True
                                    break
                            if not updated:
                                matched_group.setdefault('conditionAndLogicList', []).append(refine_rule[0])
                        else:
                            validation_data['conditionLogicColumnList'].append({
                                'conditionColumns': condition_column_names,
                                'constraintColumns': constraint_column_names,
                                'conditionAndLogicList': [refine_rule[0]]
                            })

                    elif len(column) > 2:
                        if 'multipleConditionLogicColumnList' not in validation_data:
                            validation_data['multipleConditionLogicColumnList'] = []
                        condition_column_names = []
                        constraint_column_names = []
                        for col_value in (rule.get('originalRule') or {}).get('conditionColumnValue', []):
                            condition_column_names.extend(col_value.keys())
                        for col_value in (rule.get('originalRule') or {}).get('constraintColumnValue', []):
                            constraint_column_names.extend(col_value.keys())
                        if not condition_column_names and not constraint_column_names:
                            for col_value in refine_rule[0].get('conditionColumnValue', []):
                                condition_column_names.extend(col_value.keys())
                            for col_value in refine_rule[0].get('constraintColumnValue', []):
                                constraint_column_names.extend(col_value.keys())

                        matched_group = None
                        for condition_logic in validation_data.get('multipleConditionLogicColumnList', []):
                            if (set(condition_logic.get('conditionColumns', [])) == set(condition_column_names) and 
                                set(condition_logic.get('constraintColumns', [])) == set(constraint_column_names)):
                                matched_group = condition_logic
                                break

                        if matched_group:
                            updated = False
                            for i, logic_rule in enumerate(matched_group.get('conditionAndLogicList', [])):
                                original_condition = (rule.get('originalRule') or {}).get('conditionColumnValue', [])
                                current_condition = logic_rule.get('conditionColumnValue', [])
                                if compare_condition_values(original_condition, current_condition):
                                    matched_group['conditionAndLogicList'][i] = refine_rule[0]
                                    updated = True
                                    break
                            if not updated:
                                matched_group.setdefault('conditionAndLogicList', []).append(refine_rule[0])
                        else:
                            validation_data['multipleConditionLogicColumnList'].append({
                                'conditionColumns': condition_column_names,
                                'constraintColumns': constraint_column_names,
                                'conditionAndLogicList': [refine_rule[0]]
                            })

                elif isinstance(column, str) and column in validation_data:
                    if rule_type == 'Range' and refine_rule:
                        selected_rule = None
                        if refine_example and isinstance(refine_rule[0], list):
                            import re
                            range_match = re.search(r'[(\[](.*?),\s*(.*?)[\])]', refine_example)
                            if range_match:
                                start_val, end_val = range_match.groups()
                                for r in refine_rule[0]:
                                    if (str(r['start']) == start_val.strip() and 
                                        str(r['end']) == end_val.strip()):
                                        selected_rule = [r]
                                        break

                        update_rule = selected_rule if selected_rule else refine_rule[0]

                        validation_data[column]['range'] = []
                        for new_range in (update_rule if isinstance(update_rule, list) else [update_rule]):
                            ordered_range = {}
                            ordered_range['start'] = new_range['start']
                            ordered_range['end'] = new_range['end']
                            ordered_range['startInclusive'] = new_range['startInclusive']
                            ordered_range['endInclusive'] = new_range['endInclusive']
                            validation_data[column]['range'].append(ordered_range)
                    elif rule_type == 'Format' and refine_rule:
                        validation_data[column]['format'] = refine_rule
                    elif rule_type == 'Decimal' and refine_rule:
                        validation_data[column]['decimal'] = refine_rule[0]
                    elif rule_type == 'Difference' and refine_rule:
                        if 'difference' not in validation_data[column]:
                            validation_data[column]['difference'] = {}
                        if isinstance(refine_rule, dict):
                            validation_data[column]['difference']['difference'] = refine_rule
                        else:
                            validation_data[column]['difference']['difference'] = refine_rule[0]
                    elif rule_type == 'relativeDifference' and refine_rule:
                        if 'difference' not in validation_data[column]:
                            validation_data[column]['difference'] = {}
                        if isinstance(refine_rule, dict):
                            validation_data[column]['difference']['relativeDifference'] = refine_rule
                        else:
                            validation_data[column]['difference']['relativeDifference'] = refine_rule[0]
                    elif rule_type == 'Outlier' and refine_rule:
                        validation_data[column]['outlierFunction'] = refine_rule[0]
                    elif rule_type == 'Sequence' and refine_rule:
                        original_rule = rule.get('originalRule')
                        if original_rule and 'value' in original_rule:
                            target_value = original_rule.get('value')
                            for seq_rule in validation_data[column]['sequenceRule']:
                                if seq_rule.get('value') == target_value:
                                    refine_dict = refine_rule
                                    if isinstance(refine_rule, list) and len(refine_rule) > 0:
                                        refine_dict = refine_rule[0]
                                    for key in seq_rule.keys():
                                        if key in refine_dict:
                                            seq_rule[key] = refine_dict[key]
                                    break
                        else:
                            validation_data[column]['sequenceRule'] = refine_rule

                    else:
                        print(f"Unhandled rule type: {rule_type}, column: {column}")
                        print(f"refine_rule: {refine_rule}")
                        print(f"Column {column} does not exist in validation_data")

        if 'addRules' in rules_data and rules_data['addRules']:
            for rule in rules_data['addRules']:
                if rule.get('type') == 'MultipleDuplicate' and 'refineRule' in rule:
                    if 'multipleDuplicateColumnsList' not in validation_data:
                        validation_data['multipleDuplicateColumnsList'] = []
                    refine_rule = rule.get('refineRule')
                    if refine_rule and refine_rule not in validation_data['multipleDuplicateColumnsList']:
                        validation_data['multipleDuplicateColumnsList'].append(refine_rule)

        if 'deleteRules' in rules_data and rules_data['deleteRules']:
            for rule in rules_data['deleteRules']:
                column_name = rule.get('column')
                rule_type = rule.get('type')
                original_rule = rule.get('originalRule')
                if rule_type == 'MultipleDuplicate' and 'multipleDuplicateColumnsList' in validation_data:
                    if isinstance(original_rule, list) and original_rule in validation_data['multipleDuplicateColumnsList']:
                        validation_data['multipleDuplicateColumnsList'].remove(original_rule)
                    elif isinstance(column_name, list) and column_name in validation_data['multipleDuplicateColumnsList']:
                        validation_data['multipleDuplicateColumnsList'].remove(column_name)
                
                elif rule_type == 'Sequence' and 'sequenceRule' in validation_data[column_name]:
                    new_sequence_rules = []
                    for existing_rule in validation_data[column_name]['sequenceRule']:
                        should_keep = True
                        for rule_to_delete in original_rule:
                            if all(item in existing_rule.items() for item in rule_to_delete.items()):
                                should_keep = False
                                break
                        if should_keep:
                            new_sequence_rules.append(existing_rule)
                        
                    validation_data[column_name]['sequenceRule'] = new_sequence_rules
                elif rule_type == 'Range' and 'range' in validation_data[column_name]:
                    new_range_rules = []
                    for existing_rule in validation_data[column_name]['range']:
                        if existing_rule not in original_rule:
                            new_range_rules.append(existing_rule)
                    validation_data[column_name]['range'] = new_range_rules
                elif rule_type == 'Logical and condition':
                    if 'conditionLogicColumnList' not in validation_data:
                        validation_data['conditionLogicColumnList'] = []

                    rule_columns = rule.get('column', [])
                    condition_column_names = []
                    constraint_column_names = []
                        
                    for col_value in rule.get('originalRule', {}).get('conditionColumnValue', []):
                        condition_column_names.extend(col_value.keys())
                        
                    for col_value in rule.get('originalRule', {}).get('constraintColumnValue', []):
                        constraint_column_names.extend(col_value.keys())
                        
                    for condition_logic in validation_data.get('conditionLogicColumnList', []):
                        if (set(condition_logic.get('conditionColumns', [])) == set(condition_column_names) and 
                            set(condition_logic.get('constraintColumns', [])) == set(constraint_column_names)):
                            new_logic_rules = []
                            for i, logic_rule in enumerate(condition_logic.get('conditionAndLogicList', [])):
                                original_condition = rule.get('originalRule', {}).get('conditionColumnValue', [])
                                current_condition = logic_rule.get('conditionColumnValue', [])
                                    
                                if not compare_condition_values(original_condition, current_condition):
                                    new_logic_rules.append(logic_rule)
                                
                            condition_logic['conditionAndLogicList'] = new_logic_rules
                            if len(new_logic_rules) == 0:
                                validation_data['conditionLogicColumnList'].remove(condition_logic)
                                
                            break
                elif rule_type == 'Format' and 'format' in validation_data[column_name]:
                    if validation_data[column_name]['format'] == original_rule:
                        validation_data[column_name].pop('format', None)
                elif rule_type == 'Decimal' and 'decimal' in validation_data[column_name]:
                    if validation_data[column_name]['decimal'] == original_rule[0]:
                        validation_data[column_name].pop('decimal', None)
                elif rule_type == 'Difference' and 'difference' in validation_data[column_name]:
                    validation_data[column_name].pop('difference', None)
                elif rule_type == 'relativeDifference' and 'relativeDifference' in validation_data[column_name]:
                    validation_data[column_name].pop('relativeDifference', None)
        with open(new_json_file_path, 'w', encoding='utf-8') as f:
            json.dump(validation_data, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        print(f"Error while updating rules: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
