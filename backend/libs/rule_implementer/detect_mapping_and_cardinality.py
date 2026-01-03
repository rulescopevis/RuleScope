def detect_lookup(parentColumn, childColumn, lookupList):
    """
    Detect whether parent and child columns conform to lookup relationship
    
    Args:
        parentColumn: Parent column data, dataseries
        childColumn: Child column data, dataseries
        lookupList: List storing lookup relationships
    
    Returns:
        List of indices that do not conform to lookup relationship
    """
    # Convert both columns to string type, keeping indices unchanged
    # Using astype(str) will convert NaN to 'nan', None to 'None'
    parent_str = parentColumn.astype(str)
    child_str = childColumn.astype(str)
    
    # Build lookup dictionary for easy searching - also convert values in lookup relationship to strings
    lookup_dict = {}
    for item in lookupList:
        parent = str(item["parentValue"]) if item["parentValue"] is not None else 'None'
        for child in item["childValueList"]:
            child_str_val = str(child) if child is not None else 'None'
            if child_str_val not in lookup_dict:
                lookup_dict[child_str_val] = set()
            lookup_dict[child_str_val].add(parent)
    
    # Build set of all possible parent values - convert to strings
    valid_parents = {str(item["parentValue"]) if item["parentValue"] is not None else 'None' 
                    for item in lookupList}
    
    # Initialize result list
    invalid_index = []
    
    # Iterate through each row to check relationship
    for idx in parent_str.index:
        parent_val = parent_str[idx]
        child_val = child_str[idx]
        
        # Check if parent value exists in valid_parents
        if parent_val not in valid_parents:
            invalid_index.append(idx)
            continue
            
        # Check lookup relationship
        if child_val not in lookup_dict:
            invalid_index.append(idx)
            continue
            
        if parent_val not in lookup_dict[child_val]:
            invalid_index.append(idx)
            
    return invalid_index