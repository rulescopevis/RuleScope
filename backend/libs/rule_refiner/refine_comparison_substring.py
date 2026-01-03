from typing import List, Dict, Optional

def refine_comparison_character(substringDict: Optional[Dict[str, str]], 
                              validFlag: bool,
                              selectValueList: List[Dict]) -> Dict:
    
    def is_substring(str1: str, str2: str) -> bool:
        """Check if str1 is a substring of str2"""
        if str1 is None or str2 is None:
            return False
        return str(str1) in str(str2)
    
    def check_all_substring_relation(value_list: List[Dict], col1: str, col2: str) -> bool:
        """Check if all data satisfies substring relationship"""
        return all(is_substring(str(item[col1]), str(item[col2])) for item in value_list)

    def validate_data(data_list: List[Dict], col1: str, col2: str) -> tuple[List[Dict], List[Dict]]:
        """Validate data and classify into valid and invalid lists"""
        valid_list = []
        invalid_list = []
        
        for item in data_list:
            # Check for null values
            if item.get(col1) is None or item.get(col2) is None:
                invalid_list.append(item)
            # Check substring relationship
            elif is_substring(str(item[col1]), str(item[col2])):
                valid_list.append(item)
            else:
                invalid_list.append(item)
                
        return valid_list, invalid_list

    try:
        result = {
            "refineStatus": False,
            "refineSubstringList": []
        }

        # If no data, return directly
        if not selectValueList:
            return result

        # If no original substringDict
        if substringDict is None:
            columns = list(selectValueList[0].keys())
            # Check all possible column pairs
            for col1 in columns:
                for col2 in columns:
                    if col1 != col2:
                        if check_all_substring_relation(selectValueList, col1, col2):
                            result["refineStatus"] = True
                            result["refineSubstringList"].append({"column1": col1, "column2": col2})
        elif isinstance(substringDict, list) and len(substringDict) == 0:
            # Handle empty list case
            columns = list(selectValueList[0].keys())
            for col1 in columns:
                for col2 in columns:
                    if col1 != col2:
                        is_substring_relation = check_all_substring_relation(selectValueList, col1, col2)
                        if is_substring_relation:
                            if validFlag:
                                # When validFlag is true, only add the first found substring relationship
                                result["refineStatus"] = True
                                result["refineSubstringList"] = [{"column1": col1, "column2": col2}]
                                return result
                            else:
                                # When validFlag is false, check for mutual substring relationship
                                reverse_relation = check_all_substring_relation(selectValueList, col2, col1)
                                if not reverse_relation:
                                    # If no reverse relationship, only add one-way relationship
                                    result["refineStatus"] = True
                                    result["refineSubstringList"] = [{"column1": col1, "column2": col2}]
                                    return result
                                else:
                                    # If bidirectional relationship exists, add both directions
                                    result["refineStatus"] = True
                                    result["refineSubstringList"] = [
                                        {"column1": col1, "column2": col2},
                                        {"column1": col2, "column2": col1}
                                    ]
                                    return result
        else:
            # Original logic for processing substringDict dictionary
            col1, col2 = substringDict["column1"], substringDict["column2"]
            valid_list, invalid_list = validate_data(selectValueList, col1, col2)
            
            if validFlag:
                if not invalid_list:
                    return result
                working_list = invalid_list
                
                if check_all_substring_relation(working_list, col2, col1):
                    result["refineStatus"] = True
                    result["refineSubstringList"] = [{"column1": col2, "column2": col1}]
            else:
                if not valid_list:
                    return result
                working_list = valid_list
                result["refineStatus"] = True
                result["refineSubstringList"] = [{"column1": col2, "column2": col1}]

        return result

    except Exception as e:
        return {
            "refineStatus": False,
            "refineSubstringList": [],
            "error": str(e)
        }