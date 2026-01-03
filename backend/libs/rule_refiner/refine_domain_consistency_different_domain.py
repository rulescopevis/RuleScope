def refine_domain_consistency_differentDomain(differentDomainList, validFlag, selectValueList):
    result = {
        "refineStatus": False,
        "refineDifferentDomainList": []
    }
    
    # If selectValueList is empty, return directly
    if not selectValueList:
        return result
    
    # Initialize valid and invalid value lists
    validList = []
    invalidList = []
    
    # Check if each value is in differentDomainList
    for value in selectValueList:
        if value in differentDomainList:
            invalidList.append(value)  # Values in list are invalid
        else:
            validList.append(value)    # Values not in list are valid
    
    # Select value list to process based on validFlag
    if validFlag:
        processValueList = invalidList
        if not invalidList:  # If no invalid values
            return result
    else:
        processValueList = validList
        if not validList:    # If no valid values
            return result
    
    # Create a copy of differentDomainList for modification
    new_different_domain_list = differentDomainList.copy()
    
    if validFlag:  # True means remove values from differentDomainList
        # Check if all values to remove are in differentDomainList
        values_to_remove = [v for v in processValueList if v in new_different_domain_list]
        if values_to_remove:
            # Remove these values
            new_different_domain_list = [v for v in new_different_domain_list if v not in values_to_remove]
            result["refineDifferentDomainList"] = new_different_domain_list
            result["refineStatus"] = True
            
    else:  # False means add values to differentDomainList
        # Check if there are new values to add
        values_to_add = [v for v in processValueList if v not in new_different_domain_list]
        if values_to_add:
            # Add these values
            new_different_domain_list.extend(values_to_add)
            result["refineDifferentDomainList"] = new_different_domain_list
            result["refineStatus"] = True
            
    return result