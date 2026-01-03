from typing import Dict, List, Any

def refine_duplicate(validFlag: bool,
                     duplicateDetectFlag: bool,
                     selectValueList: List[Any]) -> Dict:
    
    # Check if there are duplicate values
    has_duplicates = len(selectValueList) != len(set(selectValueList))
    result = {
        "refineStatus": False,
        "refineDuplicateDetectFlag": duplicateDetectFlag
    }
    
    if has_duplicates:
        # Case with duplicate values
        if validFlag and duplicateDetectFlag:
            result["refineDuplicateDetectFlag"] = False
            result["refineStatus"] = True
        elif not validFlag and not duplicateDetectFlag:
            result["refineDuplicateDetectFlag"] = True
            result["refineStatus"] = True
    else:
        # Case without duplicate values
        if validFlag and not duplicateDetectFlag:
            result["refineDuplicateDetectFlag"] = True
            result["refineStatus"] = True
            
    return result