import copy
from typing import Dict, List

def refine_order_sequence(sequenceList: List[Dict],
                         validFlag: bool,
                         selectValueList: List[str]) -> Dict:
    # Initialize return result
    result = {
        "refineStatus": False,
        "refineSequenceList": [],
        "originalRuleList": []
    }
    
    # If sequence has fewer than 2 values, return directly
    if len(selectValueList) < 2:
        return result

    # Validate selection order
    validList = []
    invalidList = []
    
    # Iterate through adjacent value pairs for validation
    current_valid_sequence = []
    current_invalid_sequence = []
    
    for i in range(len(selectValueList) - 1):
        current_value = selectValueList[i]
        next_value = selectValueList[i + 1]
        is_valid_pair = False
        
        # Check if conforms to existing rules
        for sequence in sequenceList:
            if sequence["value"] == current_value and next_value in sequence["allowed_next"]:
                is_valid_pair = True
                break
        
        # Process continuous sequences
        if is_valid_pair:
            if not current_valid_sequence or current_valid_sequence[-1] == current_value:
                if not current_valid_sequence:
                    current_valid_sequence.append(current_value)
                current_valid_sequence.append(next_value)
            else:
                if current_valid_sequence:
                    validList.append(current_valid_sequence[:])
                current_valid_sequence = [current_value, next_value]
        else:
            if not current_invalid_sequence or current_invalid_sequence[-1] == current_value:
                if not current_invalid_sequence:
                    current_invalid_sequence.append(current_value)
                current_invalid_sequence.append(next_value)
            else:
                if current_invalid_sequence:
                    invalidList.append(current_invalid_sequence[:])
                current_invalid_sequence = [current_value, next_value]
    
    # Add final sequences
    if current_valid_sequence:
        validList.append(current_valid_sequence)
    if current_invalid_sequence:
        invalidList.append(current_invalid_sequence)
    
    # Select sequence list to process based on validFlag
    process_sequences = invalidList if validFlag else validList
    
    # If no continuous sequences to process, return False
    if not process_sequences:
        result["refineSequenceList"] = sequenceList
        return result
    
    # Use the longest continuous sequence for processing
    longest_sequence = max(process_sequences, key=len)
    
    # Continue with original refinement logic using selected sequence
    new_sequence_list = copy.deepcopy(sequenceList)
    modified_rules = []
    original_rules = []

    # Iterate through adjacent value pairs
    for i in range(len(longest_sequence) - 1):
        current_value = longest_sequence[i]
        next_value = longest_sequence[i + 1]
        
        # Find rules corresponding to current value in sequenceList
        for sequence in new_sequence_list:
            if sequence["value"] == current_value:
                # Save original rule before modification
                original_rule = next(
                    (rule for rule in sequenceList if rule["value"] == current_value),
                    None
                )
                if original_rule and original_rule not in original_rules:
                    original_rules.append(copy.deepcopy(original_rule))

                if validFlag:
                    if next_value not in sequence["allowed_next"]:
                        sequence["allowed_next"].append(next_value)
                        if sequence not in modified_rules:
                            modified_rules.append(copy.deepcopy(sequence))
                else:
                    if next_value in sequence["allowed_next"]:
                        sequence["allowed_next"].remove(next_value)
                        if sequence not in modified_rules:
                            modified_rules.append(copy.deepcopy(sequence))
                break
        else:
            if validFlag:
                new_rule = {
                    "value": current_value,
                    "allowed_next": [next_value]
                }
                modified_rules.append(new_rule)
                original_rules.append({
                    "value": current_value,
                    "allowed_next": []
                })

    result["refineStatus"] = bool(modified_rules)
    result["refineSequenceList"] = modified_rules
    result["originalRuleList"] = original_rules
    return result