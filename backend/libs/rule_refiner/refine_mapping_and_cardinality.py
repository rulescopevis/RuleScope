import copy

def validate_lookup_data(lookupDict, selectValueList):
    """Validate if data conforms to lookup relationships, return valid and invalid lists"""
    valid_list = []
    invalid_list = []
    
    for selectValue in selectValueList:
        is_valid = False
        # Iterate through each lookup rule
        for lookup in lookupDict:
            parentColumnName = lookup["parentColumnName"]
            childColumnName = lookup["childColumnName"]
            
            # Check if necessary columns are present
            if parentColumnName not in selectValue or childColumnName not in selectValue:
                continue
                
            parentValue = selectValue[parentColumnName]
            childValue = selectValue[childColumnName]
            
            # Check if exists in lookup relationship
            for item in lookup["lookupList"]:
                if item["parentValue"] == parentValue and childValue in item["childValueList"]:
                    is_valid = True
                    break
            
            if is_valid:
                break
                
        if is_valid:
            valid_list.append(selectValue)
        else:
            invalid_list.append(selectValue)
            
    return valid_list, invalid_list

def refine_derived_relation(lookupDict, validFlag, selectValueList):
    result = {
        "refineStatus": False,
        "refineDerivedRelationList": []
    }
    
    # Handle empty lookupDict case
    if not lookupDict:
        if not validFlag:
            return result
            
        # When validFlag is True, generate new lookup relationships from data
        if len(selectValueList) < 1:
            return result
            
        # Get column names from first data entry
        first_data = selectValueList[0]
        if len(first_data.keys()) < 2:
            return result
            
        # Get all column names
        columns = list(first_data.keys())
        
        # Create lookup relationships for each column pair
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                parent_col = columns[i]
                child_col = columns[j]
                
                # Collect all unique parent-child value pairs
                relation_map = {}
                for value in selectValueList:
                    parent_value = value[parent_col]
                    child_value = value[child_col]
                    
                    if parent_value not in relation_map:
                        relation_map[parent_value] = set()
                    relation_map[parent_value].add(child_value)
                
                # Create new lookup rule
                new_lookup = {
                    "parentColumnName": parent_col,
                    "childColumnName": child_col,
                    "lookupList": [
                        {
                            "parentValue": parent,
                            "childValueList": list(children)
                        }
                        for parent, children in relation_map.items()
                    ]
                }
                
                result["refineDerivedRelationList"].append(new_lookup)
                
                # Create reverse lookup relationship
                reverse_relation_map = {}
                for value in selectValueList:
                    parent_value = value[child_col]
                    child_value = value[parent_col]
                    
                    if parent_value not in reverse_relation_map:
                        reverse_relation_map[parent_value] = set()
                    reverse_relation_map[parent_value].add(child_value)
                
                reverse_lookup = {
                    "parentColumnName": child_col,
                    "childColumnName": parent_col,
                    "lookupList": [
                        {
                            "parentValue": parent,
                            "childValueList": list(children)
                        }
                        for parent, children in reverse_relation_map.items()
                    ]
                }
                
                result["refineDerivedRelationList"].append(reverse_lookup)
        
        result["refineStatus"] = True
        return result
    
    # Validate data
    valid_list, invalid_list = validate_lookup_data(lookupDict, selectValueList)
    
    # Select working list based on validFlag
    if validFlag:
        if not invalid_list:  # If no invalid data
            return result
        working_list = invalid_list
    else:
        if not valid_list:  # If no valid data
            return result
        working_list = valid_list
    
    # Iterate through each select value
    for selectValue in working_list:
        # Iterate through each lookup rule
        for lookup in lookupDict:
            parentColumnName = lookup["parentColumnName"] 
            childColumnName = lookup["childColumnName"]
            
            # Check if select value contains required parent and child columns
            if parentColumnName not in selectValue or childColumnName not in selectValue:
                continue
                
            parentValue = selectValue[parentColumnName]
            childValue = selectValue[childColumnName]
            
            # Deep copy original lookupDict for modification
            new_lookup = copy.deepcopy(lookup)
            
            if validFlag:  # Handle positive examples
                # Find corresponding parent value
                parent_found = False
                child_exists_in_other = False
                original_parent = None
                
                for item in new_lookup["lookupList"]:
                    # Check if child value exists under other parent values
                    if childValue in item["childValueList"] and item["parentValue"] != parentValue:
                        child_exists_in_other = True
                        original_parent = item["parentValue"]
                    
                    if item["parentValue"] == parentValue:
                        parent_found = True
                        if childValue not in item["childValueList"]:
                            item["childValueList"].append(childValue)
                
                # If parent value not found, create new one
                if not parent_found:
                    new_lookup["lookupList"].append({
                        "parentValue": parentValue,
                        "childValueList": [childValue]
                    })
                
                # If child value exists under other parent values
                if child_exists_in_other:
                    # Add version without removing existing relationships
                    result["refineDerivedRelationList"].append(new_lookup)
                    
                    # Create version with existing relationships removed
                    removed_lookup = copy.deepcopy(new_lookup)
                    for item in removed_lookup["lookupList"]:
                        if item["parentValue"] == original_parent:
                            item["childValueList"].remove(childValue)
                    result["refineDerivedRelationList"].append(removed_lookup)
                else:
                    result["refineDerivedRelationList"].append(new_lookup)
                    
                result["refineStatus"] = True
                    
            else:  # Handle negative examples
                # Find corresponding parent value and remove child value
                found_and_removed = False
                for item in new_lookup["lookupList"]:
                    if item["parentValue"] == parentValue and childValue in item["childValueList"]:
                        item["childValueList"].remove(childValue)
                        result["refineDerivedRelationList"].append(new_lookup)
                        found_and_removed = True
                        break
                
                result["refineStatus"] = found_and_removed
            
    return result