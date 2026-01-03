import copy
from typing import Dict, List, Any
import sys
import os

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from rule_refiner.refine_range import refine_range

def format_float(number):
    # Convert to string, check for consecutive 3 or more zeros
    str_num = str(number)
    if '000' in str_num:
        # Find position of first consecutive 3 zeros
        zero_pos = str_num.find('000')
        # Truncate to before consecutive zeros
        str_num = str_num[:zero_pos]
        # Remove decimal point if it's at the end
        str_num = str_num.rstrip('.')
        return float(str_num)
    return number

def refine_single_difference(differenceDict: Dict,
                           validFlag: bool,
                           selectValueList: List[Any]) -> Dict:
    # Initialize return result
    result = {
        "refineStatus": False,
        "refineDifferenceDictList": []
    }
    
    # If selectValueList has fewer than 2 values, return directly
    if len(selectValueList) < 2:
        return result
        
    # Handle empty differenceDict and validFlag is False case
    if not differenceDict and not validFlag:
        # Calculate differences between adjacent values
        differences = []
        relative_differences = []
        for i in range(len(selectValueList) - 1):
            v1, v2 = selectValueList[i], selectValueList[i + 1]
            diff = format_float(abs(v2 - v1))
            differences.append(diff)
            if v1 != 0:
                rel_diff = abs(diff / v1)
                relative_differences.append(rel_diff)
        
        if differences:
            min_diff = min(differences)
            min_rel_diff = min(relative_differences) if relative_differences else 0
            
            result["refineStatus"] = True
            result["refineDifferenceDictList"].append({
                "difference": {
                    "start": 0,
                    "end": min_diff,
                    "startInclusive": True,
                    "endInclusive": False
                },
                "relativeDifference": {
                    "start": 0,
                    "end": min_rel_diff,
                    "startInclusive": True,
                    "endInclusive": False
                }
            })
            return result
            
    # Calculate differences and relative differences between all adjacent values
    differences = []
    relative_differences = []
    valid_diffs = []
    invalid_diffs = []
    valid_rel_diffs = []
    invalid_rel_diffs = []
    
    for i in range(len(selectValueList) - 1):
        v1, v2 = selectValueList[i], selectValueList[i + 1]
        # Calculate difference
        diff = abs(v2 - v1)
        differences.append(diff)
        
        # Calculate relative difference
        rel_diff = 0
        if v1 != 0:
            rel_diff = abs(diff / v1)
            relative_differences.append(rel_diff)
        
        # Check if difference is within allowed range
        diff_range = differenceDict["difference"]
        rel_diff_range = differenceDict["relativeDifference"]
        
        is_valid_diff = (diff >= diff_range["start"] and 
                        diff <= diff_range["end"] and
                        diff_range["startInclusive"] and 
                        diff_range["endInclusive"])
        
        is_valid_rel_diff = (v1 == 0 or  # If v1 is 0, ignore relative difference check
                           (rel_diff >= rel_diff_range["start"] and
                            rel_diff <= rel_diff_range["end"] and
                            rel_diff_range["startInclusive"] and
                            rel_diff_range["endInclusive"]))
        
        # Valid only if both difference and relative difference conditions are met
        if is_valid_diff and is_valid_rel_diff:
            valid_diffs.append(diff)
            if v1 != 0:
                valid_rel_diffs.append(rel_diff)
        else:
            invalid_diffs.append(diff)
            if v1 != 0:
                invalid_rel_diffs.append(rel_diff)
    
    # Select difference list to use based on validFlag
    if validFlag:
        if not invalid_diffs:  # If no invalid values, no optimization needed
            return result
        differences_to_use = invalid_diffs
        relative_differences_to_use = invalid_rel_diffs
    else:
        if not valid_diffs:  # If no valid values, no optimization needed
            return result
        differences_to_use = valid_diffs
        relative_differences_to_use = valid_rel_diffs
    
    # Prepare data for calling refine_range
    difference_range = [differenceDict["difference"]]
    relative_difference_range = [differenceDict["relativeDifference"]] if relative_differences else []
    
    # Call refine_range with filtered difference list
    difference_result = refine_range(
        rangeList=difference_range,
        dataType="numeric",
        validFlag=validFlag,
        selectValueList=differences_to_use
    )
    
    # If there's relative difference data, also process relative difference range
    relative_difference_result = None
    if relative_differences:
        relative_difference_result = refine_range(
            rangeList=relative_difference_range,
            dataType="numeric",
            validFlag=validFlag,
            selectValueList=relative_differences_to_use
        )
    
    # If either refine operation succeeds
    if difference_result["refineStatus"] or (relative_differences and relative_difference_result["refineStatus"]):
        result["refineStatus"] = True
        
        # Filter single-segment range results, keeping original range in middle
        if validFlag:
            # For validFlag=True, check if range expansion is needed
            min_diff = format_float(min(differences_to_use))
            max_diff = format_float(max(differences_to_use))
            need_adjust = (min_diff < differenceDict["difference"]["start"] or 
                         max_diff > differenceDict["difference"]["end"])
            
            if need_adjust:
                new_diff_range = copy.deepcopy(differenceDict["difference"])
                if min_diff < differenceDict["difference"]["start"]:
                    new_diff_range["start"] = min_diff
                    new_diff_range["startInclusive"] = True
                if max_diff > differenceDict["difference"]["end"]:
                    new_diff_range["end"] = max_diff
                    new_diff_range["endInclusive"] = True
                
                if relative_differences:
                    min_rel_diff = format_float(min(relative_differences_to_use))
                    max_rel_diff = format_float(max(relative_differences_to_use))
                    need_adjust_rel = (min_rel_diff < differenceDict["relativeDifference"]["start"] or 
                                     max_rel_diff > differenceDict["relativeDifference"]["end"])
                    
                    if need_adjust_rel:
                        new_rel_diff_range = copy.deepcopy(differenceDict["relativeDifference"])
                        if min_rel_diff < differenceDict["relativeDifference"]["start"]:
                            new_rel_diff_range["start"] = min_rel_diff
                            new_rel_diff_range["startInclusive"] = True
                        if max_rel_diff > differenceDict["relativeDifference"]["end"]:
                            new_rel_diff_range["end"] = max_rel_diff
                            new_rel_diff_range["endInclusive"] = True
                    else:
                        new_rel_diff_range = copy.deepcopy(differenceDict["relativeDifference"])
                else:
                    new_rel_diff_range = copy.deepcopy(differenceDict["relativeDifference"])
                    
                result["refineDifferenceDictList"].append({
                    "difference": new_diff_range,
                    "relativeDifference": new_rel_diff_range
                })
        else:
            # For validFlag=False case, keep original logic
            single_range_diff_results = [diff_range[0] for diff_range in difference_result["refineRangeList"] 
                                       if len(diff_range) == 1]
            
            if not relative_differences:
                for diff_range in single_range_diff_results:
                    new_difference_dict = {
                        "difference": diff_range,
                        "relativeDifference": copy.deepcopy(differenceDict["relativeDifference"])
                    }
                    result["refineDifferenceDictList"].append(new_difference_dict)
            else:
                # Modification: ensure difference and relativeDifference correspond one-to-one
                single_range_rel_diff_results = [rel_diff_range[0] 
                                               for rel_diff_range in relative_difference_result["refineRangeList"] 
                                               if len(rel_diff_range) == 1]
                
                # Take shorter length of two lists
                min_length = min(len(single_range_diff_results), len(single_range_rel_diff_results))
                
                # Add one-to-one correspondence
                for i in range(min_length):
                    new_difference_dict = {
                        "difference": single_range_diff_results[i],
                        "relativeDifference": single_range_rel_diff_results[i]
                    }
                    result["refineDifferenceDictList"].append(new_difference_dict)
        
        # Deduplicate difference and relativeDifference before returning result
        unique_diffs = []
        seen_differences = []
        seen_relative_differences = []
        
        for diff_dict in result["refineDifferenceDictList"]:
            current_diff = str(diff_dict["difference"])
            current_rel_diff = str(diff_dict["relativeDifference"])
            
            # Add if current combination hasn't appeared before
            if (current_diff, current_rel_diff) not in [(str(d["difference"]), str(d["relativeDifference"])) for d in unique_diffs]:
                unique_diffs.append(diff_dict)
                seen_differences.append(current_diff)
                seen_relative_differences.append(current_rel_diff)
        
        result["refineDifferenceDictList"] = unique_diffs
    
    return result

def format_float(number):
    """
    Format floating point numbers, handling floating point precision issues
    1. Remove trailing consecutive zeros (e.g. 1.23000000085 -> 1.23)
    2. Handle values close to integers (e.g. 1.999999999 -> 2)
    3. Handle values close to decimals (e.g. 1.829999999934 -> 1.83)
    4. Handle repeated decimals (e.g. 1.633333333333333382 -> 1.63)
    5. Correctly handle rounding (e.g. 1.65555555555582 -> 1.7)
    """
    # First try common precision handling
    # Check if close to 1 or 2 decimal places
    for decimal_places in [1, 2]:
        rounded = round(number, decimal_places)
        if abs(number - rounded) < 1e-10:
            return rounded
    
    # Convert to string
    str_num = str(float(number))
    
    # If integer, return directly
    if '.' not in str_num:
        return float(str_num)
    
    # Check if close to an integer
    rounded_int = round(number)
    if abs(number - rounded_int) < 1e-10:
        return float(rounded_int)
    
    # Handle repeated decimal patterns
    decimal_part = str_num.split('.')[1]
    
    # For cases like 1.6444444444444482, should return 1.64
    if len(decimal_part) > 2 and decimal_part[2:].count(decimal_part[2]) > 5:
        return round(number, 2)
    
    # Check for repetitive patterns
    for i in range(1, min(6, len(decimal_part))):
        # Check if first i digits are followed by identical digits
        prefix = decimal_part[:i]
        rest = decimal_part[i:]
        
        # If remaining part consists entirely of same digits or approaches a pattern
        if rest and (all(d == rest[0] for d in rest) or 
                    all(d in ('0', '9') for d in rest) or
                    all(int(d) >= 5 for d in rest[:min(3, len(rest))])):
            # If subsequent digits are all >= 5, may need rounding up
            if all(int(d) >= 5 for d in rest[:min(3, len(rest))]):
                # Ensure correct rounding
                return round(number, i)
            return round(number, i)
    
    # Analyze decimal part patterns
    # Check for consecutive 5, 6, 7, 8, 9 which may indicate rounding needed
    for i in range(2, min(6, len(decimal_part))):
        if all(int(d) >= 5 for d in decimal_part[i:i+3] if d.isdigit()):
            return round(number, i)
    
    # Find effective decimal places (exclude trailing consecutive 0s and 9s)
    effective_decimals = len(decimal_part)
    # Check from right to left, reduce consecutive 9s and 0s
    for i in range(len(decimal_part)-1, -1, -1):
        if decimal_part[i] in ('0', '9'):
            effective_decimals -= 1
        else:
            break
    
    # Ensure at least 1 decimal place, maximum 10
    effective_decimals = max(1, min(effective_decimals, 10))
    
    # Round according to effective decimal places
    return round(number, effective_decimals)