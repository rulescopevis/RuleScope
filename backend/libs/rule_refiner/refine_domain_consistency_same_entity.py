import copy

def refine_domain_consistency_sameEntity(EntityList, validFlag, selectValueList):
    result = {
        "refineStatus": False,
        "refineSameEntityList": []
    }
    
    # If selectValueList is empty, return directly
    if not selectValueList:
        return result

    # Initialize valid and invalid value lists
    validList = []
    invalidList = []
    
    # Check if each value is in any entity's sameEntityList
    for value in selectValueList:
        value_in_same_entity = False
        for entity in EntityList:
            if value in entity["sameEntityList"]:
                value_in_same_entity = True
                break
        
        if value_in_same_entity:
            invalidList.append(value)  # Values in sameEntityList are invalid
        else:
            validList.append(value)    # Values not in sameEntityList are valid
    
    # Select value list to process based on validFlag
    if validFlag:
        processValueList = invalidList
        if not invalidList:  # If no invalid values
            return result
    else:
        processValueList = validList
        if not validList:    # If no valid values
            return result

    if validFlag:  # True means selected data was originally in sameEntityList and needs to be removed
        target_idx = None
        # Find dict containing values in processValueList
        for idx, entity_dict in enumerate(EntityList):
            if any(value in entity_dict["sameEntityList"] for value in processValueList):
                target_idx = idx
                break
                
        if target_idx is not None:
            new_entity_list = copy.deepcopy(EntityList)
            # Remove selected values from sameEntityList
            new_entity_list[target_idx]["sameEntityList"] = [
                v for v in new_entity_list[target_idx]["sameEntityList"] 
                if v not in processValueList
            ]
            
            # If sameEntityList is empty, remove entire dict
            if not new_entity_list[target_idx]["sameEntityList"]:
                new_entity_list.pop(target_idx)
                
            result["refineSameEntityList"] = new_entity_list
            result["refineStatus"] = True
            
    else:  # False means selected data was originally not in sameEntityList and needs to be added
        target_idx = None
        # Find dict containing mainEntity
        for idx, entity_dict in enumerate(EntityList):
            if any(value == entity_dict["mainEntity"] for value in processValueList):
                target_idx = idx
                break
                
        if target_idx is not None:
            new_entity_list = copy.deepcopy(EntityList)
            # Add selected values to sameEntityList (excluding mainEntity)
            values_to_add = [v for v in processValueList 
                           if v != new_entity_list[target_idx]["mainEntity"] and 
                           v not in new_entity_list[target_idx]["sameEntityList"]]
            new_entity_list[target_idx]["sameEntityList"].extend(values_to_add)
            result["refineSameEntityList"] = new_entity_list
            result["refineStatus"] = True
            
    return result