import math
import copy
from typing import Dict, List, Any
import sys
import os

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from rule_refiner.refine_range import refine_range

def validate_difference_data(differenceDict: Dict, selectValueList: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """Validate if data conforms to difference rules, return valid and invalid lists"""
    valid_list = []
    invalid_list = []
    
    # If list has fewer than 2 elements, cannot calculate difference
    if len(selectValueList) < 2:
        return valid_list, selectValueList
    
    difference_range = differenceDict["difference"]
    
    # Iterate through adjacent value pairs
    for i in range(len(selectValueList) - 1):
        record1, record2 = selectValueList[i], selectValueList[i + 1]
        
        # Calculate Euclidean distance between multiple columns
        squared_diff_sum = 0
        for column in record1.keys():
            if column in record2:
                diff = record2[column] - record1[column]
                squared_diff_sum += diff * diff
        euclidean_distance = math.sqrt(squared_diff_sum)
        
        # Check if difference is within specified range
        is_valid = (difference_range["startInclusive"] and euclidean_distance >= difference_range["start"] or
                   not difference_range["startInclusive"] and euclidean_distance > difference_range["start"]) and \
                  (difference_range["endInclusive"] and euclidean_distance <= difference_range["end"] or
                   not difference_range["endInclusive"] and euclidean_distance < difference_range["end"])
        
        # If current difference is valid, add both records to valid_list
        if is_valid:
            if record1 not in valid_list:
                valid_list.append(record1)
            if record2 not in valid_list:
                valid_list.append(record2)
        else:
            # If current difference is invalid, add both records to invalid_list
            if record1 not in invalid_list:
                invalid_list.append(record1)
            if record2 not in invalid_list:
                invalid_list.append(record2)
    
    return valid_list, invalid_list

def refine_multiple_difference(differenceDict: Dict,
                             validFlag: bool,
                             selectValueList: List[Dict[str, Any]]) -> Dict:
    # Initialize return result
    result = {
        "refineStatus": False,
        "refineDifferenceDictList": []
    }
    
    # If selectValueList is empty, return directly
    if not selectValueList:
        return result
        
    # Handle empty differenceDict case
    if not differenceDict:
        if len(selectValueList) < 2:  # Need at least two records to calculate difference
            return result
            
        # Calculate Euclidean distances between all adjacent data pairs
        differences = []
        for i in range(len(selectValueList) - 1):
            record1, record2 = selectValueList[i], selectValueList[i + 1]
            # Calculate Euclidean distance between multiple columns
            squared_diff_sum = 0
            for column in record1.keys():
                if column in record2:
                    try:
                        diff = float(record2[column]) - float(record1[column])
                        squared_diff_sum += diff * diff
                    except (ValueError, TypeError):
                        continue
            if squared_diff_sum > 0:
                euclidean_distance = math.sqrt(squared_diff_sum)
                differences.append(euclidean_distance)
        
        if not differences:  # If no valid differences
            return result
            
        # Create different rules based on validFlag
        if validFlag:
            # validFlag is True: use maximum value as upper boundary (closed interval), 0 as lower boundary (closed interval)
            new_difference = {
                "difference": {
                    "start": 0,
                    "end": max(differences),
                    "startInclusive": True,
                    "endInclusive": True
                }
            }
        else:
            # validFlag is False: use minimum value as upper boundary (open interval), 0 as lower boundary (closed interval)
            new_difference = {
                "difference": {
                    "start": 0,
                    "end": min(differences),
                    "startInclusive": True,
                    "endInclusive": False
                }
            }
        
        result["refineStatus"] = True
        result["refineDifferenceDictList"].append(new_difference)
        return result
    
    # Validate data
    valid_list, invalid_list = validate_difference_data(differenceDict, selectValueList)
    
    # Select data list based on validFlag
    if validFlag:
        if not invalid_list:  # If no invalid data
            return result
        working_list = invalid_list
    else:
        if not valid_list:  # If no valid data
            return result
        working_list = valid_list
    
    # Calculate Euclidean distances between adjacent values
    differences = []
    for i in range(len(working_list) - 1):
        record1, record2 = working_list[i], working_list[i + 1]
        # Calculate Euclidean distance between multiple columns
        squared_diff_sum = 0
        for column in record1.keys():
            if column in record2:
                diff = record2[column] - record1[column]
                squared_diff_sum += diff * diff
        euclidean_distance = math.sqrt(squared_diff_sum)
        differences.append(euclidean_distance)
    
    # If no valid differences, return directly
    if not differences:
        return result
    
    # Prepare data for calling refine_range
    difference_range = [differenceDict["difference"]]
    
    # Call refine_range to process difference range
    difference_result = refine_range(
        rangeList=difference_range,
        dataType="number",
        validFlag=validFlag,
        selectValueList=sorted(list(set(differences)))  # Deduplicate and sort
    )
    
    # If refine operation is successful
    if difference_result["refineStatus"]:
        result["refineStatus"] = True
        
        if validFlag:
            # For validFlag=True, keep original start, extend end to maximum required value
            max_diff = max(differences)
            if max_diff > differenceDict["difference"]["end"]:
                new_diff_range = copy.deepcopy(differenceDict["difference"])
                new_diff_range["end"] = max_diff
                new_diff_range["endInclusive"] = True
                
                result["refineDifferenceDictList"].append({
                    "difference": new_diff_range
                })
        else:
            # Use set to deduplicate
            seen_ranges = set()
            for diff_range in difference_result["refineRangeList"]:
                # Only process single segment ranges
                if len(diff_range) == 1:
                    # Create tuple for comparison
                    range_tuple = (
                        diff_range[0]["start"],
                        diff_range[0]["end"],
                        diff_range[0]["startInclusive"],
                        diff_range[0]["endInclusive"]
                    )
                    # If this range hasn't been seen, add it
                    if range_tuple not in seen_ranges:
                        seen_ranges.add(range_tuple)
                        new_difference_dict = {
                            "difference": diff_range[0]
                        }
                        result["refineDifferenceDictList"].append(new_difference_dict)
    
    return result