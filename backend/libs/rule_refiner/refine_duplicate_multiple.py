from typing import Dict, List, Any

def refine_multiple_duplicate(validFlag: bool,
                            duplicateDetectFlag: bool,
                            selectValueList: List[Dict[str, Any]]) -> Dict:
    """
    Detect duplicate values in multi-column combinations
    
    Args:
        validFlag: Validation flag
        duplicateDetectFlag: Duplicate detection flag
        selectValueList: List of dictionaries containing multi-column values [{"columnName1": value, "columnName2": value,...},...]
    
    Returns:
        Dict: Dictionary containing duplicate detection results
    """
    result = {
        "refineStatus": False,
        "refineDuplicateDetectFlag": duplicateDetectFlag
    }
    
    # If list is empty, return directly
    if not selectValueList:
        return result
        
    # Convert each record to a tuple for comparison
    value_tuples = []
    for record in selectValueList:
        # Ensure all records use the same key order
        sorted_items = sorted(record.items())
        value_tuples.append(tuple(item[1] for item in sorted_items))
    
    # Check for duplicate values
    has_duplicates = len(value_tuples) != len(set(value_tuples))
    
    if has_duplicates:
        # Case with duplicate values
        if validFlag and duplicateDetectFlag:
            # Currently detecting duplicates and needing no duplicates, change flag to False
            result["refineDuplicateDetectFlag"] = False
            result["refineStatus"] = True
        elif not validFlag and not duplicateDetectFlag:
            # Currently not detecting duplicates and needing duplicates, change flag to True
            result["refineDuplicateDetectFlag"] = True
            result["refineStatus"] = True
    else:
        # Case without duplicate values
        if validFlag and not duplicateDetectFlag:
            # Currently not detecting duplicates and needing no duplicates, change flag to True
            result["refineDuplicateDetectFlag"] = True
            result["refineStatus"] = True
            
    return result