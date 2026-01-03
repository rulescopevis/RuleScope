import os
import re
import sys
import json

# Get the parent directory of the current file's parent directory
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from read_table import read_table
from rule_refiner.refine_format_character import refine_format_character
from rule_refiner.refine_format_date import refine_format_date
from rule_refiner.refine_range import refine_range
from rule_refiner.refine_integrity import refine_missing_value
from rule_refiner.refine_domain_consistency_different_domain import refine_domain_consistency_differentDomain
from rule_refiner.refine_domain_consistency_same_entity import refine_domain_consistency_sameEntity
from rule_refiner.refine_difference import refine_single_difference
from rule_refiner.refine_duplicate import refine_duplicate
from rule_refiner.refine_sequence import refine_order_sequence
from rule_refiner.refine_comparison_numeric_date import refine_comparison_numeric_date
from rule_refiner.refine_comparison_substring import refine_comparison_character
from rule_refiner.refine_mapping_and_cardinality import refine_derived_relation
from rule_refiner.refine_logical_and_condition import refine_condition_and_logic
from rule_refiner.refine_difference_multiple import refine_multiple_difference
from rule_refiner.refine_duplicate_multiple import refine_multiple_duplicate

def merge_dicts_with_same_value(dict_list):
    # Create a temporary dictionary to classify dictionaries with the same value by value
    temp_dict = {}
    
    for d in dict_list:
        value = d['value']  # Get the value
        if value in temp_dict:
            # If the value exists, merge allowed_next and remove duplicates
            temp_dict[value]['allowed_next'].extend(d['allowed_next'])
            temp_dict[value]['allowed_next'] = list(set(temp_dict[value]['allowed_next']))
        else:
            # If the value does not exist, create a new entry
            temp_dict[value] = {
                'value': value,
                'allowed_next': d['allowed_next']
            }
    
    # Convert the temporary dictionary back to a list
    return list(temp_dict.values())

def merge_ranges(ranges, is_valid):
    result = []
    if not ranges:
        return result
        
    # Sort by start
    sorted_ranges = sorted(ranges, key=lambda x: x['start'])
    current = sorted_ranges[0]
    
    for next_range in sorted_ranges[1:]:
        # Check for intersection
        if current['end'] > next_range['start'] or (current['end'] == next_range['start'] and current['endInclusive'] and next_range['startInclusive']):
            if is_valid:
                # When validFlag is True, take the union
                current['start'] = min(current['start'], next_range['start'])
                current['end'] = max(current['end'], next_range['end'])
                current['startInclusive'] = current['start'] == next_range['start'] and current['startInclusive'] or next_range['startInclusive']
                current['endInclusive'] = current['end'] == next_range['end'] and current['endInclusive'] or next_range['endInclusive']
            else:
                # When validFlag is False, take the intersection
                new_start = max(current['start'], next_range['start'])
                new_end = min(current['end'], next_range['end'])
                
                # Only keep it when the intersection exists and is not a single point
                if new_start < new_end:
                    current['start'] = new_start
                    current['end'] = new_end
                    # When start is the same, both intervals must contain this point to keep the inclusion
                    current['startInclusive'] = (current['start'] == next_range['start'] and 
                                               current['startInclusive'] and next_range['startInclusive'])
                    # When end is the same, both intervals must contain this point to keep the inclusion
                    current['endInclusive'] = (current['end'] == next_range['end'] and 
                                             current['endInclusive'] and next_range['endInclusive'])
                else:
                    # If the intersection does not exist or is a single point, skip the current interval
                    current = next_range
                    continue
        else:
            result.append(current)
            current = next_range
    result.append(current)
    return result

def merge_sequence_rules(temp_sequence_list, temp_original_list, valid_flag):
    """
    Merge sequence rules.
    
    Args:
        temp_sequence_list (list): Temporary list of sequence rules.
        temp_original_list (list): Temporary list of original rules.
        valid_flag (bool): Validation flag.
        
    Returns:
        list: Merged rules list, format: [{"originalRule": {...}, "refineSequenceRule": {...}}, ...]
    """
    # Process tempOriginalRuleList, remove duplicates by value
    seen_values = {}
    unique_original_rules = []
    for rule in temp_original_list:
        if rule['value'] not in seen_values:
            seen_values[rule['value']] = rule
            unique_original_rules.append(rule)
    
    # Process tempSequenceList, merge rules with the same value based on validFlag
    merged_sequence_rules = {}
    for rule in temp_sequence_list:
        value = rule['value']
        if value in merged_sequence_rules:
            if valid_flag:
                # Take the union
                merged_sequence_rules[value]['allowed_next'] = list(set(
                    merged_sequence_rules[value]['allowed_next'] + rule['allowed_next']
                ))
            else:
                # Take the intersection
                if not merged_sequence_rules[value].get('first_rule'):
                    merged_sequence_rules[value]['first_rule'] = True
                    merged_sequence_rules[value]['allowed_next'] = rule['allowed_next']
                else:
                    merged_sequence_rules[value]['allowed_next'] = list(set(
                        merged_sequence_rules[value]['allowed_next']
                    ).intersection(set(rule['allowed_next'])))
        else:
            merged_sequence_rules[value] = {
                'value': value,
                'allowed_next': rule['allowed_next']
            }
    
    # Reorganize the result structure
    final_sequence_list = []
    for value, refined_rule in merged_sequence_rules.items():
        # Find the corresponding original rule
        original_rule = next(
            (rule for rule in unique_original_rules if rule['value'] == value),
            {'value': value, 'allowed_next': []}  # If no corresponding original rule is found, use an empty rule
        )
        final_sequence_list.append({
            'originalRule': original_rule,
            'refineSequenceRule': refined_rule
        })
    
    return final_sequence_list

def refine_validation_rules(validationPath, validFlag, dataPath, selectInfo, model):
    result = {
        "refineResultStatus": False,
        "refineDict": {
            "addRules": [],
            "deleteRules": [],
            "updateRules": []
        }
    }
    
    df = read_table(dataPath)
    validationDict = json.load(open(validationPath, 'r'))

    selectValueList = []

    columnList = selectInfo["columnList"]
    if len(columnList) == 1:
        for index in selectInfo["indexList"]:
            selectValueList.append(df.iloc[index][columnList[0]])

        missingRefineResult = refine_missing_value(validationDict[columnList[0]]["missingDetectFlag"], validationDict[columnList[0]]["specialMissingValueList"], validFlag, selectValueList)
        if missingRefineResult["refineStatus"]:
            result["refineResultStatus"] = True
            result["refineDict"]["updateRules"].append({
                "type": "Missing",
                "column": columnList[0],
                "originalRule": {
                    "missingDetectFlag": validationDict[columnList[0]]["missingDetectFlag"],
                    "specialMissingValueList": validationDict[columnList[0]]["specialMissingValueList"]
                },
                "refineRule": {
                    "missingDetectFlag": missingRefineResult["missingDetectFlag"],
                    "specialMissingValueList": missingRefineResult["specialMissingValueList"]
                }
            })

        if len(selectInfo["indexList"]) > 1:
            refineDuplicateResult = refine_duplicate(validationDict[columnList[0]]["duplicateDetectFlag"], validFlag, selectValueList)
            if refineDuplicateResult["refineStatus"]:
                result["refineResultStatus"] = True
                result["refineDict"]["updateRules"].append({
                    "type": "Duplicate",
                    "column": columnList[0],
                    "originalRule": validationDict[columnList[0]]["duplicateDetectFlag"],
                    "refineRule": refineDuplicateResult["refineDuplicateDetectFlag"]
                })

        if validationDict[columnList[0]]["type"] == "character":
            # refine format(LLMs)
            # if "format" in validationDict[columnList[0]]:
            #     formatRefineResult = refine_format_character(validationDict[columnList[0]]["format"], validFlag, selectValueList, model)
            #     if formatRefineResult["refineStatus"]:
            #         result["refineResultStatus"] = True
            #         result["refineDict"]["updateRules"].append({
            #             "type": "format",
            #             "column": columnList[0],
            #             "originalRule": validationDict[columnList[0]]["format"],
            #             "refineRule": [formatRefineResult['refineFormat']]
            #         })
            #         if validFlag:
            #         result["refineResultStatus"] = True
            #             result["refineDict"]["deleteRules"].append({
            #                 "type": "format",
            #                 "column": columnList[0],
            #                 "originalRule": validationDict[columnList[0]]["format"]
            #             })
            # else:
            #     if validFlag == False:
            #     # need to add new format rules
            #     result["refineResultStatus"] = True
            #     # result["refineDict"]["addRules"].append({
            #     #     "type": "format",
            #     #     "column": columnList[0],
            #     #     "originalRule": validationDict[columnList[0]]["format"],
            #     #     "refineRule": [formatRefineResult]
            #     # })
            #         print("add format rules")
            if len(selectInfo["indexList"]) > 1:
                if "conditionIndexList" in selectInfo:
                    continuous_indices = []
                    current_sequence = []
                    detectList = []
                    
                    for i in range(len(selectInfo["conditionIndexList"])-1):
                        if not current_sequence:
                            current_sequence.append(selectInfo["conditionIndexList"][i])
                            
                        if selectInfo["conditionIndexList"][i+1] == selectInfo["conditionIndexList"][i] + 1:
                            current_sequence.append(selectInfo["conditionIndexList"][i+1])
                        else:
                            if len(current_sequence) >= 2:
                                continuous_indices.append(current_sequence[:])
                            current_sequence = [selectInfo["conditionIndexList"][i+1]]
                    
                    if len(current_sequence) >= 2:
                        continuous_indices.append(current_sequence)
                    
                    for sequence in continuous_indices:
                        values = []
                        for idx in sequence:
                            original_position = selectInfo["conditionIndexList"].index(idx)
                            values.append(selectValueList[original_position])
                        if values:
                            detectList.append(values)

                if validationDict[columnList[0]]["differentDomainList"] != []:
                    differentDomainRefineResult = refine_domain_consistency_differentDomain(validationDict[columnList[0]]["differentDomainList"], validFlag, selectValueList)
                    if differentDomainRefineResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["updateRules"].append({
                            "type": "DifferentDomain",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["differentDomainList"],
                            "refineRule": differentDomainRefineResult["refineDifferentDomainList"]
                        })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "DifferentDomain",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["differentDomainList"]
                        })
                else:
                    differentDomainRefineResult = refine_domain_consistency_differentDomain([], validFlag, selectValueList)
                    if differentDomainRefineResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "DifferentDomain",
                            "column": columnList[0],
                            "refineRule": differentDomainRefineResult["refineDifferentDomainList"]
                        })

                if validationDict[columnList[0]]["sameEntityList"] != []:
                    sameEntityRefineResult = refine_domain_consistency_sameEntity(validationDict[columnList[0]]["sameEntityList"], validFlag, selectValueList)
                    if sameEntityRefineResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["updateRules"].append({
                            "type": "SameEntity",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["sameEntityList"],
                            "refineRule": sameEntityRefineResult["refineSameEntityList"]
                        })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "SameEntity",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["sameEntityList"]
                        })
                else:
                    sameEntityRefineResult = refine_domain_consistency_sameEntity([], validFlag, selectValueList)
                    if sameEntityRefineResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "SameEntity",
                            "column": columnList[0],
                            "refineRule": sameEntityRefineResult["refineSameEntityList"]
                        })

                if "sequenceRule" in validationDict[columnList[0]]:
                    tempSequenceList = []
                    tempOriginalRuleList = []
                    for detectValues in detectList:
                        sequenceRefineResult = refine_order_sequence(validationDict[columnList[0]]["sequenceRule"], validFlag, detectValues)
                        if sequenceRefineResult["refineStatus"]:
                            tempSequenceList.extend(sequenceRefineResult["refineSequenceList"])
                            tempOriginalRuleList.extend(sequenceRefineResult["originalRuleList"])
                    if tempSequenceList != []:
                        final_sequence_list = merge_sequence_rules(tempSequenceList, tempOriginalRuleList, validFlag)
                        for rule in final_sequence_list:
                            result["refineResultStatus"] = True
                            result["refineDict"]["updateRules"].append({
                                "type": "Sequence",
                                "column": columnList[0],
                                "originalRule": rule["originalRule"],
                                "refineRule": rule["refineSequenceRule"]
                            })
                    if validFlag:
                        deleteSequenceList = []
                        for detectValues in detectList:
                            for index in range(0, len(detectValues)-1):
                                for sequenceDict in validationDict[columnList[0]]["sequenceRule"]:
                                    if detectValues[index] == sequenceDict["value"] and detectValues[index+1] not in sequenceDict["allowed_next"]:
                                        deleteSequenceList.append(sequenceDict)
                        # deleteSequenceList = list(set(deleteSequenceList))
                        tempValueList = []
                        for deleteSequence in deleteSequenceList:
                            value = deleteSequence["value"]
                            if value not in tempValueList:
                                tempValueList.append(value)
                            else:
                                deleteSequenceList.remove(deleteSequence)
                        if deleteSequenceList != []:
                            result["refineResultStatus"] = True
                            result["refineDict"]["deleteRules"].append({
                                "type": "Sequence",
                                "column": columnList[0],
                                "originalRule": deleteSequenceList
                            })
                else:
                    if validFlag == True:
                        tempAddSequenceList = []
                        for detectValues in detectList:
                            for index in range(0, len(detectValues)-1):
                                tempAddSequenceList.append({"value": detectValues[index], "allowed_next": [detectValues[index+1]]})
                        refineAddSequenceList = merge_dicts_with_same_value(tempAddSequenceList)
                        if refineAddSequenceList != []:
                            result["refineResultStatus"] = True
                            result["refineDict"]["addRules"].append({
                                "type": "Sequence",
                                "column": columnList[0],
                                "refineRule": refineAddSequenceList
                            })
        elif validationDict[columnList[0]]["type"] == "numeric":
            if validationDict[columnList[0]]["range"] != []:
                refineRangeResult = refine_range(validationDict[columnList[0]]["range"], "numeric", validFlag, selectValueList)
                if refineRangeResult["refineStatus"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["updateRules"].append({
                        "type": "Range",
                        "column": columnList[0],
                        "originalRule": validationDict[columnList[0]]["range"],
                        "refineRule": refineRangeResult['refineRangeList']
                    })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "Range",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["range"]
                        })
            else:
                minValue = min(selectValueList)
                maxValue = max(selectValueList)
                if minValue != maxValue:
                    if validFlag == True:
                        addRangeList = [{"start": minValue, "end": maxValue, "startInclusive": True, "endInclusive": True}]
                    if validFlag == False:
                        addRangeList = [{"start": minValue, "end": maxValue, "startInclusive": False, "endInclusive": False}]
                        addRangeList.append({"start": None, "end": minValue, "startInclusive": True, "endInclusive": False})
                        addRangeList.append({"start": maxValue, "end": None, "startInclusive": False, "endInclusive": True})
                    result["refineResultStatus"] = True
                    result["refineDict"]["addRules"].append({
                        "type": "Range",
                        "column": columnList[0],
                        "originalRule": validationDict[columnList[0]]["range"],
                        "refineRule": addRangeList
                    })

            if len(selectInfo["indexList"]) > 1:
                if "conditionIndexList" in selectInfo:
                    continuous_indices = []
                    current_sequence = []
                    detectList = []
                    
                    for i in range(len(selectInfo["conditionIndexList"])-1):
                        if not current_sequence:
                            current_sequence.append(selectInfo["conditionIndexList"][i])
                            
                        if selectInfo["conditionIndexList"][i+1] == selectInfo["conditionIndexList"][i] + 1:
                            current_sequence.append(selectInfo["conditionIndexList"][i+1])
                        else:
                            if len(current_sequence) >= 2:
                                continuous_indices.append(current_sequence[:])
                            current_sequence = [selectInfo["conditionIndexList"][i+1]]
                    
                    if len(current_sequence) >= 2:
                        continuous_indices.append(current_sequence)
                    
                    for sequence in continuous_indices:
                        values = []
                        for idx in sequence:
                            original_position = selectInfo["conditionIndexList"].index(idx)
                            values.append(selectValueList[original_position])
                        if values:
                            detectList.append(values)
                
                
                if validationDict[columnList[0]]["difference"] != []:
                    tempDifference = []
                    for detectValues in detectList:
                        refineSingleDifferenceResult = refine_single_difference(validationDict[columnList[0]]["difference"], validFlag, detectValues)
                        if refineSingleDifferenceResult["refineStatus"]:
                            tempDifference.extend(refineSingleDifferenceResult["refineDifferenceDictList"])
                    
                    # 分别获取difference和relativeDifference的列表
                    diff_ranges = [d['difference'] for d in tempDifference]
                    rel_diff_ranges = [d['relativeDifference'] for d in tempDifference]

                    # 分别合并
                    merged_diff = merge_ranges(diff_ranges, validFlag)
                    merged_rel_diff = merge_ranges(rel_diff_ranges, validFlag)

                    # 重新组合结果
                    tempDifference = [
                        {
                            'difference': diff,
                            'relativeDifference': rel_diff
                        }
                        for diff, rel_diff in zip(merged_diff, merged_rel_diff)
                    ]
                    
                    if tempDifference != []:
                        for item in tempDifference:
                            result["refineResultStatus"] = True
                            result["refineDict"]["updateRules"].append({
                                "type": "Difference",
                                "column": columnList[0],
                                "originalRule": validationDict[columnList[0]]["difference"]["difference"],
                                "refineRule": item["difference"]
                            })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "Difference",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["difference"]["difference"]
                        })
                else:
                    if validFlag == False:
                        refineSingleDifferenceResult = refine_single_difference({}, validFlag, selectValueList)
                        if refineSingleDifferenceResult["refineStatus"]:
                            result["refineResultStatus"] = True
                            result["refineDict"]["addRules"].append({
                                "type": "Difference",
                                "column": columnList[0],
                                "refineRule": refineSingleDifferenceResult["refineDifferenceDictList"][0]["difference"]
                            })
        elif validationDict[columnList[0]]["type"] == "datetime":
            # if "dateFormat" in validationDict[columnList[0]]:
            #     dateFormatRefineResult = refine_format_date(validationDict[columnList[0]]["dateFormat"], validFlag, selectValueList)
            #     if dateFormatRefineResult["refineStatus"]:
            #         result["refineDict"]["updateRules"].append({
            #             "type": "dateFormat",
            #             "column": columnList[0],
            #             "originalRule": validationDict[columnList[0]]["dateFormat"],
            #             "refineRule": [dateFormatRefineResult]
            #         })
            #         if validFlag:
            #             result["refineDict"]["deleteRules"].append({
            #                 "type": "dateFormat",
            #                 "column": columnList[0],
            #                 "originalRule": validationDict[columnList[0]]["dateFormat"]
            #             })
            # else:
            #     if validFlag == False:
            #         print("add dateFormat rules")
            if validationDict[columnList[0]]["range"] != []:
                refineRangeResult = refine_range(validationDict[columnList[0]]["range"], "datetime", validFlag, selectValueList, validationDict[columnList[0]]["dateFormat"])
                if refineRangeResult["status"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["updateRules"].append({
                        "type": "Range",
                        "column": columnList[0],
                        "originalRule": validationDict[columnList[0]]["range"],
                        "refineRule": refineRangeResult['refineRangeList']
                    })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "Range",
                            "column": columnList[0],
                            "originalRule": validationDict[columnList[0]]["range"]
                        })
            else:
                minValue = min(selectValueList)
                maxValue = max(selectValueList)
                if minValue != maxValue:
                    if validFlag == True:
                        addRangeList = [{"start": minValue, "end": maxValue, "startInclusive": True, "endInclusive": True}]
                    if validFlag == False:
                        addRangeList = [{"start": minValue, "end": maxValue, "startInclusive": False, "endInclusive": False}]
                        addRangeList.append({"start": None, "end": minValue, "startInclusive": True, "endInclusive": False})
                        addRangeList.append({"start": maxValue, "end": None, "startInclusive": False, "endInclusive": True})
                    result["refineResultStatus"] = True
                    result["refineDict"]["addRules"].append({
                        "type": "Range",
                        "column": columnList[0],
                        "originalRule": validationDict[columnList[0]]["range"],
                        "refineRule": addRangeList
                    })

    else:
        for index in selectInfo["indexList"]:
            valueDict = {}
            for column in columnList:
                valueDict[column] = df.iloc[index][column]
            selectValueList.append(valueDict)
        if len(columnList) == 2:
            if validationDict[columnList[0]]["type"] == "numeric" and validationDict[columnList[1]]["type"] == "numeric":
                compareRule = []
                for item in validationDict["numericCompareList"]:
                    if item["column1"] == columnList[0] and item["column2"] == columnList[1]:
                        compareRule.append(item)
                        break
                    if item["column1"] == columnList[1] and item["column2"] == columnList[0]:
                        compareRule.append(item)
                        break
                if compareRule != []:
                    refineComparisonNumericResult = refine_comparison_numeric_date(compareRule, "numeric", validFlag, selectValueList)
                    if refineComparisonNumericResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["updateRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "originalRule": compareRule,
                            "refineRule": refineComparisonNumericResult["refineCompareRelationList"]
                        })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "originalRule": compareRule
                        })
                else:
                    refineComparisonNumericResult = refine_comparison_numeric_date([], "numeric", validFlag, selectValueList)
                    if refineComparisonNumericResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "refineRule": refineComparisonNumericResult["refineCompareRelationList"]
                        })
            elif validationDict[columnList[0]]["type"] == "datetime" and validationDict[columnList[1]]["type"] == "datetime":
                compareRule = []
                for item in validationDict["datetimeCompareList"]:
                    if item["column1"] == columnList[0] and item["column2"] == columnList[1]:
                        compareRule.append(item)
                        break
                    if item["column1"] == columnList[1] and item["column2"] == columnList[0]:
                        compareRule.append(item)
                        break
                if compareRule != []:
                    dateFormatList = []
                    dateFormatList.append(validationDict[columnList[0]]["dateFormat"])
                    dateFormatList.append(validationDict[columnList[1]]["dateFormat"])
                    refineComparisonDateResult = refine_comparison_numeric_date(compareRule, "datetime", validFlag, selectValueList, dateFormatList)
                    if refineComparisonDateResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["updateRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "originalRule": compareRule,
                            "refineRule": refineComparisonDateResult["refineCompareRelationList"]
                        })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "originalRule": compareRule
                        })
                else:
                    refineComparisonDateResult = refine_comparison_numeric_date([], "datetime", validFlag, selectValueList, dateFormatList)
                    if refineComparisonDateResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "Compare",
                            "column": columnList,
                            "refineRule": refineComparisonDateResult["refineCompareRelationList"]
                        })
            elif validationDict[columnList[0]]["type"] == "character" and validationDict[columnList[1]]["type"] == "character":
                compareRule = []
                if validationDict["substringList"] != []:
                    for item in validationDict["substringList"]:
                        if item["column1"] == columnList[0] and item["column2"] == columnList[1]:
                            compareRule.append(item)
                            break
                        if item["column1"] == columnList[1] and item["column2"] == columnList[0]:
                            compareRule.append(item)
                            break
                    if compareRule != []:
                        refineComparisonCharacterResult = refine_comparison_character(compareRule, validFlag, selectValueList)
                        if refineComparisonCharacterResult["refineStatus"]:
                            result["refineResultStatus"] = True
                            result["refineDict"]["updateRules"].append({
                                "type": "Substring",
                                "column": columnList,
                                "originalRule": compareRule,
                                "refineRule": refineComparisonCharacterResult["refineSubstringList"]
                            })
                        if validFlag:
                            result["refineResultStatus"] = True
                            result["refineDict"]["deleteRules"].append({
                                "type": "Substring",
                                "column": columnList,
                                "originalRule": compareRule
                            })
                    else:
                        refineComparisonCharacterResult = refine_comparison_character([], validFlag, selectValueList)
                        if refineComparisonCharacterResult["refineStatus"]:
                            result["refineResultStatus"] = True
                            result["refineDict"]["addRules"].append({
                                "type": "Substring",
                                "column": columnList,
                                "refineRule": refineComparisonCharacterResult["refineSubstringList"]
                            })
                
                lookupRule = []
                if validationDict["lookupList"] != []:
                    for item in validationDict["lookupList"]:
                        if item["parentColumnName"] == columnList[0] and item["childColumnName"] == columnList[1]:
                            lookupRule.append(item)
                            break
                        if item["parentColumnName"] == columnList[1] and item["childColumnName"] == columnList[0]:
                            lookupRule.append(item)
                            break
                    if lookupRule != []:
                        refineLookupResult = refine_derived_relation(lookupRule, validFlag, selectValueList)
                        if refineLookupResult["refineStatus"]:
                            result["refineResultStatus"] = True
                            result["refineDict"]["updateRules"].append({
                                "type": "Lookup",
                                "column": columnList,
                                "originalRule": lookupRule,
                                "refineRule": refineLookupResult["refineDerivedRelationList"]
                            })
                        if validFlag:
                            result["refineResultStatus"] = True
                            result["refineDict"]["deleteRules"].append({
                                "type": "Lookup",
                                "column": columnList,
                                "originalRule": lookupRule
                            })
                    else:
                        refineLookupResult = refine_derived_relation([], validFlag, selectValueList)    
                        if refineLookupResult["refineStatus"]:
                            result["refineResultStatus"] = True
                            result["refineDict"]["addRules"].append({
                                "type": "Lookup",
                                "column": columnList,
                                "refineRule": refineLookupResult["refineDerivedRelationList"]
                            })

        for item in validationDict["conditionLogicColumnList"]:
            ruleColumns = []
            for column in item["conditionColumns"]:
                ruleColumns.append(column)
            for column in item["constraintColumns"]:
                ruleColumns.append(column)
            if set(columnList) == set(ruleColumns):
                refineConditionAndLogicResult = refine_condition_and_logic(item, validFlag, selectValueList)
                if refineConditionAndLogicResult["refineStatus"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["updateRules"].append({
                        "type": "Logical and condition",
                        "column": columnList,
                        "originalRule": refineConditionAndLogicResult["originalConditionAndLogicDict"],
                        "refineRule": refineConditionAndLogicResult["refineConditionAndLogicList"]
                    })
                if validFlag and refineConditionAndLogicResult["originalConditionAndLogicDict"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["deleteRules"].append({
                        "type": "Logical and condition",
                        "column": columnList,
                        "originalRule": refineConditionAndLogicResult["originalConditionAndLogicDict"]
                    })
                else:
                    refineConditionAndLogicResult = refine_condition_and_logic([], validFlag, selectValueList)
                    if refineConditionAndLogicResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "Logical and condition",
                            "column": columnList,
                            "refineRule": refineConditionAndLogicResult["refineConditionAndLogicList"]
                        })

        for item in validationDict["multipleConditionLogicColumnList"]:
            ruleColumns = []
            for column in item["conditionColumns"]:
                ruleColumns.append(column)
            for column in item["constraintColumns"]:
                ruleColumns.append(column)
            if set(columnList) == set(ruleColumns):
                refineConditionAndLogicResult = refine_condition_and_logic(item, validFlag, selectValueList)
                if refineConditionAndLogicResult["refineStatus"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["updateRules"].append({
                        "type": "Logical and condition",
                        "column": columnList,
                        "originalRule": refineConditionAndLogicResult["originalConditionAndLogicDict"],
                        "refineRule": refineConditionAndLogicResult["refineConditionAndLogicList"]
                    })
                if validFlag and refineConditionAndLogicResult["originalConditionAndLogicDict"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["deleteRules"].append({
                        "type": "Logical and condition",
                        "column": columnList,
                        "originalRule": refineConditionAndLogicResult["originalConditionAndLogicDict"]
                    })
                else:
                    refineConditionAndLogicResult = refine_condition_and_logic([], validFlag, selectValueList)
                    if refineConditionAndLogicResult["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["addRules"].append({
                            "type": "Logical and condition",
                            "column": columnList,
                            "refineRule": refineConditionAndLogicResult["refineConditionAndLogicList"]
                        })
        
        multipleDifferenceDetectFlag = True
        for column in columnList:
            if validationDict[column]["type"] == "numeric":
                continue
            else:
                multipleDifferenceDetectFlag = False
                break
        if multipleDifferenceDetectFlag:
            multipleDifferenceDict = {}
            for item in validationDict["multiDifference"]:
                if columnList == item["columns"]:
                    multipleDifferenceDict = item["differenceDict"]
                    break
            if multipleDifferenceDict != {}:
                refineMultipleDifference = refine_multiple_difference(multipleDifferenceDict, validFlag, selectValueList)
                if refineMultipleDifference["refineStatus"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["updateRules"].append({
                        "type": "MultiDifference",
                        "column": columnList,
                        "originalRule": multipleDifferenceDict,
                        "refineRule": refineMultipleDifference["refineMultipleDifferenceList"]
                    })
                if validFlag:
                    result["refineResultStatus"] = True
                    result["refineDict"]["deleteRules"].append({
                        "type": "MultiDifference",
                        "column": columnList,
                        "originalRule": multipleDifferenceDict
                    })
            else:
                refineMultipleDifference = refine_multiple_difference([], validFlag, selectValueList)
                if refineMultipleDifference["refineStatus"]:
                    result["refineResultStatus"] = True
                    result["refineDict"]["addRules"].append({
                        "type": "MultiDifference",
                        "column": columnList,
                        "refineRule": refineMultipleDifference["refineMultipleDifferenceList"]
                    })

        if validationDict["multipleDuplicateColumnsList"] != []:
            for item in validationDict["multipleDuplicateColumnsList"]:
                if columnList == item:
                    refineMultipleDuplicate = refine_multiple_duplicate(item, validFlag, selectValueList)
                    if refineMultipleDuplicate["refineStatus"]:
                        result["refineResultStatus"] = True
                        result["refineDict"]["updateRules"].append({
                            "type": "MultipleDuplicate",
                            "column": columnList,
                            "originalRule": item,
                            "refineRule": refineMultipleDuplicate["multipleDuplicateColumnsList"]
                        })
                    if validFlag:
                        result["refineResultStatus"] = True
                        result["refineDict"]["deleteRules"].append({
                            "type": "MultipleDuplicate",
                            "column": columnList,
                            "originalRule": item
                        })
        else:
            if validFlag == False:
                result["refineResultStatus"] = True
                result["refineDict"]["addRules"].append({
                    "type": "MultipleDuplicate",
                    "column": columnList,
                    "refineRule": columnList
                })
    return result

def generate_example(result):
    # Process updateRules, generate examples first
    update_examples = {}  # Used to store examples for each column
    for rule in result["refineDict"]["updateRules"]:
        # Add column processing logic
        column = rule["column"]
        column_str = column[0] if isinstance(column, list) else column
        
        if rule["type"] == "Missing":
            # Process the change of missingDetectFlag
            original_flag = rule["originalRule"]["missingDetectFlag"]
            refine_flag = rule["refineRule"]["missingDetectFlag"]
            
            if original_flag != refine_flag:
                rule["original_example"] = "No need to detect missing" if not original_flag else "Need to detect missing"
                rule["refine_example"] = "Need to detect missing" if refine_flag else "No need to detect missing"
            
            # Process the change of specialMissingValueList
            original_list = set(rule["originalRule"]["specialMissingValueList"])
            refine_list = set(rule["refineRule"]["specialMissingValueList"])
            
            added_values = refine_list - original_list
            removed_values = original_list - refine_list
            
            # Format original_example
            if not original_list:
                if "original_example" not in rule:
                    rule["original_example"] = "specialMissingValueList: []"
                else:
                    rule["original_example"] += "; specialMissingValueList: []"
            else:
                values_str = ", ".join(map(str, original_list))
                if "original_example" not in rule:
                    rule["original_example"] = f"specialMissingValueList: [{values_str}]"
                else:
                    rule["original_example"] += f"; specialMissingValueList: [{values_str}]"
            
            # Format refine_example
            if added_values and not removed_values:
                # Only added values
                values_str = ", ".join(map(str, added_values))
                if "refine_example" not in rule:
                    rule["refine_example"] = f"Add {values_str} in specialMissingValueList"
                else:
                    rule["refine_example"] += f"; Add {values_str} in specialMissingValueList"
            elif removed_values and not added_values:
                # Only removed values
                values_str = ", ".join(map(str, removed_values))
                if "refine_example" not in rule:
                    rule["refine_example"] = f"Delete {values_str} from specialMissingValueList"
                else:
                    rule["refine_example"] += f"; Delete {values_str} from specialMissingValueList"
            elif added_values and removed_values:
                # Both added and removed
                added_str = ", ".join(map(str, added_values))
                removed_str = ", ".join(map(str, removed_values))
                if "refine_example" not in rule:
                    rule["refine_example"] = f"Add {added_str} in specialMissingValueList; Delete {removed_str} from specialMissingValueList"
                else:
                    rule["refine_example"] += f"; Add {added_str} in specialMissingValueList; Delete {removed_str} from specialMissingValueList"
        
        elif rule["type"] == "Duplicate":
            # Process duplicate type rules
            original_flag = rule["originalRule"]
            refine_flag = rule["refineRule"]
            
            rule["original_example"] = "No need to detect duplicate" if not original_flag else "Need to detect duplicate"
            rule["refine_example"] = "Need to detect duplicate" if refine_flag else "No need to detect duplicate"
        
        elif rule["type"] == "Range":
            # Process range type rules
            # Use processed column_str
            original_ranges = rule["originalRule"] if isinstance(rule["originalRule"], list) else [rule["originalRule"]]
            original_examples = []
            
            for original_range in original_ranges:
                start_bracket = "[" if original_range["startInclusive"] else "("
                end_bracket = "]" if original_range["endInclusive"] else ")"
                start_value = original_range["start"] if original_range["start"] is not None else "-∞"
                end_value = original_range["end"] if original_range["end"] is not None else "∞"
                original_examples.append(f"The range of {column_str}: {start_bracket}{start_value}, {end_value}{end_bracket}")
            
            rule["original_example"] = "; ".join(original_examples)
            
            # Process refineRule
            refine_ranges = rule["refineRule"]
            if isinstance(refine_ranges, list) and len(refine_ranges) > 0:
                # Handle nested list situation
                if isinstance(refine_ranges[0], list):
                    refine_ranges = refine_ranges[0]
                
                refine_examples = []
                for refine_range in refine_ranges:
                    start_bracket = "[" if refine_range["startInclusive"] else "("
                    end_bracket = "]" if refine_range["endInclusive"] else ")"
                    start_value = refine_range["start"] if refine_range["start"] is not None else "-∞"
                    end_value = refine_range["end"] if refine_range["end"] is not None else "∞"
                    refine_examples.append(f"Update range: {start_bracket}{start_value}, {end_value}{end_bracket}")
                
                rule["refine_example"] = "; ".join(refine_examples)
        
        elif rule["type"] == "Sequence":
            original_allowed = set(rule["originalRule"]["allowed_next"])
            refine_allowed = set(rule["refineRule"]["allowed_next"])
            
            added_values = refine_allowed - original_allowed
            removed_values = original_allowed - refine_allowed
            
            examples_original = []
            examples_refine = []
            
            for value in added_values:
                examples_original.append(f"{rule['originalRule']['value']} --> {add_strikethrough(value)}")
                examples_refine.append(f"{rule['originalRule']['value']} --> {value}")
            
            for value in removed_values:
                examples_original.append(f"{rule['originalRule']['value']} --> {value}")
                examples_refine.append(f"{rule['originalRule']['value']} --> {add_strikethrough(value)}")
            
            rule["original_example"] = "; ".join(examples_original) if examples_original else ""
            rule["refine_example"] = "; ".join(examples_refine) if examples_refine else ""
            
            # Store examples for deleteRules
            update_examples[column_str] = rule["original_example"]
        
        elif rule["type"] == "DifferentDomain":
            original_domains = set(rule["originalRule"])
            refine_domains = set(rule["refineRule"])
            
            added_domains = refine_domains - original_domains
            removed_domains = original_domains - refine_domains
            
            if not original_domains or (len(original_domains) == 1 and list(original_domains)[0] == ''):
                rule["original_example"] = f"In {column_str}, there are no differentDomain."
            else:
                rule["original_example"] = f"In {column_str}, {', '.join(original_domains)} are differentDomain"
            
            examples_refine = []
            if added_domains:
                examples_refine.append(f"Add {', '.join(added_domains)} to differentDomain")
            if removed_domains:
                examples_refine.append(f"Remove {', '.join(removed_domains)} from differentDomain")
            
            rule["refine_example"] = "; ".join(examples_refine) if examples_refine else ""
        
        elif rule["type"] == "Difference":
            original_diff = rule["originalRule"]
            
            diff_start_bracket = "[" if original_diff["startInclusive"] else "("
            diff_end_bracket = "]" if original_diff["endInclusive"] else ")"
            
            rule["original_example"] = f"In {column_str}, difference: {diff_start_bracket}{original_diff['start']}, {original_diff['end']}{diff_end_bracket}"
            
            refine_diff = rule["refineRule"]
            
            diff_changed = (original_diff["start"] != refine_diff["start"] or 
                           original_diff["end"] != refine_diff["end"] or
                           original_diff["startInclusive"] != refine_diff["startInclusive"] or
                           original_diff["endInclusive"] != refine_diff["endInclusive"])
            
            # Only add the changed part to the example
            if diff_changed:
                diff_start_bracket = "[" if refine_diff["startInclusive"] else "("
                diff_end_bracket = "]" if refine_diff["endInclusive"] else ")"
                rule["refine_example"] = f"Update difference: {diff_start_bracket}{refine_diff['start']}, {refine_diff['end']}{diff_end_bracket}"
            else:
                rule["refine_example"] = ""
        elif rule["type"] == "Logical and condition":
            # Process Logical and condition type rules
            if "originalRule" in rule and rule["originalRule"]:
                # Get condition columns and constraint columns
                condition_columns = rule["originalRule"].get("conditionColumnValue", [])
                constraint_columns = rule["originalRule"].get("constraintColumnValue", [])
                
                if condition_columns and constraint_columns:
                    # Get the value of the first condition column
                    first_condition = condition_columns[0]
                    condition_col_name = list(first_condition.keys())[0]
                    condition_values = first_condition[condition_col_name]
                    condition_value_str = ", ".join(map(str, condition_values))
                    
                    # Get the value of the first constraint column
                    first_constraint = constraint_columns[0]
                    constraint_col_name = list(first_constraint.keys())[0]
                    constraint_value = first_constraint[constraint_col_name]
                    
                    # Check if the constraint value is of range type
                    if isinstance(constraint_value, dict) and "start" in constraint_value and "end" in constraint_value:
                        # Constraint value is of range type
                        start_bracket = "[" if constraint_value.get("startInclusive", True) else "("
                        end_bracket = "]" if constraint_value.get("endInclusive", True) else ")"
                        start_value = constraint_value["start"]
                        end_value = constraint_value["end"]
                        
                        rule["original_example"] = f"When {condition_col_name} is {condition_value_str}, {constraint_col_name} is {start_bracket}{start_value}, {end_value}{end_bracket}"
                        
                        # Process refineRule
                        if isinstance(rule["refineRule"], list) and len(rule["refineRule"]) > 0:
                            refine_rule = rule["refineRule"][0]
                            refine_constraint_columns = refine_rule.get("constraintColumnValue", [])
                            
                            if refine_constraint_columns:
                                refine_first_constraint = refine_constraint_columns[0]
                                refine_constraint_col_name = list(refine_first_constraint.keys())[0]
                                refine_constraint_value = refine_first_constraint[refine_constraint_col_name]
                                
                                if isinstance(refine_constraint_value, dict) and "start" in refine_constraint_value and "end" in refine_constraint_value:
                                    refine_start_bracket = "[" if refine_constraint_value.get("startInclusive", True) else "("
                                    refine_end_bracket = "]" if refine_constraint_value.get("endInclusive", True) else ")"
                                    refine_start_value = refine_constraint_value["start"]
                                    refine_end_value = refine_constraint_value["end"]
                                    
                                    # Check for changes
                                    if (start_value != refine_start_value or 
                                        end_value != refine_end_value or 
                                        constraint_value.get("startInclusive") != refine_constraint_value.get("startInclusive") or 
                                        constraint_value.get("endInclusive") != refine_constraint_value.get("endInclusive")):
                                        
                                        rule["refine_example"] = f"When {condition_col_name} is {condition_value_str}, {constraint_col_name}: {start_bracket}{start_value}, {end_value}{end_bracket} -> {refine_start_bracket}{refine_start_value}, {refine_end_value}{refine_end_bracket}"
                                    else:
                                        rule["refine_example"] = "No change in condition rule"
                    else:
                        # Constraint value is not of range type, possibly a string array
                        constraint_value_str = ", ".join(map(str, constraint_value)) if isinstance(constraint_value, list) else str(constraint_value)
                        rule["original_example"] = f"When {condition_col_name} is {condition_value_str}, {constraint_col_name} is {constraint_value_str}"
                        
                        # Process refineRule
                        if isinstance(rule["refineRule"], list) and len(rule["refineRule"]) > 0:
                            refine_rule = rule["refineRule"][0]
                            refine_constraint_columns = refine_rule.get("constraintColumnValue", [])
                            
                            if refine_constraint_columns:
                                refine_first_constraint = refine_constraint_columns[0]
                                refine_constraint_col_name = list(refine_first_constraint.keys())[0]
                                refine_constraint_value = refine_first_constraint[refine_constraint_col_name]
                                
                                refine_constraint_value_str = ", ".join(map(str, refine_constraint_value)) if isinstance(refine_constraint_value, list) else str(refine_constraint_value)
                                
                                if constraint_value_str != refine_constraint_value_str:
                                    rule["refine_example"] = f"When {condition_col_name} is {condition_value_str}, {constraint_col_name}: {constraint_value_str} -> {refine_constraint_value_str}"
                                else:
                                    rule["refine_example"] = "No change in condition rule"
                else:
                    # If there is not enough information
                    columns = []
                    if isinstance(column, list):
                        columns = column
                    else:
                        columns = [column]
                    rule["original_example"] = f"The {' and '.join(columns)} has condition rules."
                    rule["refine_example"] = "Update condition rules"
            else:
                # If there is no originalRule
                columns = []
                if isinstance(column, list):
                    columns = column
                else:
                    columns = [column]
                rule["original_example"] = f"The {' and '.join(columns)} has condition rules."
                rule["refine_example"] = "Update condition rules"
        
        elif rule["type"] == "Lookup":
            # Process Lookup type rules
            original_lookup = rule["originalRule"][0] if isinstance(rule["originalRule"], list) else rule["originalRule"]
            refine_lookup = rule["refineRule"][0] if isinstance(rule["refineRule"], list) else rule["refineRule"]
            
            # Get parent column and child column names
            parent_col = original_lookup["parentColumnName"]
            child_col = original_lookup["childColumnName"]
            
            # Create dictionaries for easy comparison
            original_lookup_dict = {item["parentValue"]: set(item["childValueList"]) for item in original_lookup["lookupList"]}
            refine_lookup_dict = {item["parentValue"]: set(item["childValueList"]) for item in refine_lookup["lookupList"]}
            
            # Set a general original example
            rule["original_example"] = f"{parent_col} and {child_col} have lookup rules"
            
            # Find the changes
            changes = []
            
            # Check all original parent values
            for parent_value, original_children in original_lookup_dict.items():
                if parent_value in refine_lookup_dict:
                    refine_children = refine_lookup_dict[parent_value]
                    
                    # Check for changes
                    if original_children != refine_children:
                        added = refine_children - original_children
                        removed = original_children - refine_children
                        
                        if added or removed:
                            changes.append({
                                "parent_value": parent_value,
                                "added": list(added),
                                "removed": list(removed)
                            })
                else:
                    # Parent value deleted
                    changes.append({
                        "parent_value": parent_value,
                        "added": [],
                        "removed": list(original_children)
                    })
            
            # Check for newly added parent values
            for parent_value, refine_children in refine_lookup_dict.items():
                if parent_value not in original_lookup_dict:
                    changes.append({
                        "parent_value": parent_value,
                        "added": list(refine_children),
                        "removed": []
                    })
            
            # Generate refined examples
            if changes:
                refine_examples = []
                
                for change in changes:
                    parent_value = change["parent_value"]
                    added = change["added"]
                    removed = change["removed"]
                    
                    # Add removed child values
                    if removed:
                        removed_str = ", ".join([f"'{child}'" for child in removed])
                        refine_examples.append(f"When {parent_col} is '{parent_value}', delete {removed_str} in {child_col}List")
                    
                    # Add added child values
                    if added:
                        added_str = ", ".join([f"'{child}'" for child in added])
                        refine_examples.append(f"When {parent_col} is '{parent_value}', add {added_str} in {child_col}List")
                
                rule["refine_example"] = "; ".join(refine_examples)
            else:
                rule["refine_example"] = "No changes in lookup rule"
    
    # Process deleteRules, use the same example
    if "deleteRules" in result["refineDict"] and result["refineDict"]["deleteRules"]:
        for rule in result["refineDict"]["deleteRules"]:
            # Add column processing logic
            column = rule["column"]
            column_str = column[0] if isinstance(column, list) else column
            
            if rule["type"] == "DifferentDomain":
                if not rule["originalRule"] or (len(rule["originalRule"]) == 1 and rule["originalRule"][0] == ''):
                    rule["original_example"] = f"In {column_str}, there are no differentDomain."
                else:
                    rule["original_example"] = f"In {column_str}, {', '.join(rule['originalRule'])} are differentDomain"
                rule["refine_example"] = "Delete this differentDomain rule"
                
            elif rule["type"] == "Sequence":
                # Use the same example as updateRules
                rule["original_example"] = update_examples.get(column_str, "")
                rule["refine_example"] = "Delete this sequence rule"
                
            elif rule["type"] == "Difference":
                # Process difference type delete rules
                original_diff = rule["originalRule"]
                
                diff_start_bracket = "[" if original_diff["startInclusive"] else "("
                diff_end_bracket = "]" if original_diff["endInclusive"] else ")"
                
                rule["original_example"] = f"In {column_str}, difference: {diff_start_bracket}{original_diff['start']}, {original_diff['end']}{diff_end_bracket}"
                
                # Set the example for delete rule
                rule["refine_example"] = f"Delete difference rule in {column_str}"
            elif rule["type"] == "Logical and condition":
                # Process conditional logic rules
                if "originalRule" in rule and rule["originalRule"]:
                    # Get condition columns and constraint columns
                    condition_columns = rule["originalRule"].get("conditionColumnValue", [])
                    constraint_columns = rule["originalRule"].get("constraintColumnValue", [])
                    
                    # Handle the first case: constraint value with range
                    if condition_columns and constraint_columns:
                        # Get the value of the first condition column
                        first_condition = condition_columns[0]
                        condition_col_name = list(first_condition.keys())[0]
                        condition_values = first_condition[condition_col_name]
                        condition_value_str = ", ".join(map(str, condition_values))
                        
                        # Get the value of the first constraint column
                        first_constraint = constraint_columns[0]
                        constraint_col_name = list(first_constraint.keys())[0]
                        constraint_value = first_constraint[constraint_col_name]
                        
                        # Check if the constraint value is of range type
                        if isinstance(constraint_value, dict) and "start" in constraint_value and "end" in constraint_value:
                            # Constraint value is of range type
                            start_bracket = "[" if constraint_value.get("startInclusive", True) else "("
                            end_bracket = "]" if constraint_value.get("endInclusive", True) else ")"
                            start_value = constraint_value["start"]
                            end_value = constraint_value["end"]
                            
                            rule["original_example"] = f"When {condition_col_name} is {condition_value_str}, {constraint_col_name} is {start_bracket}{start_value}, {end_value}{end_bracket}"
                        else:
                            # Constraint value is not of range type, use the format of the second case
                            columns = []
                            if isinstance(column, list):
                                columns = column
                            else:
                                columns = [column]
                            rule["original_example"] = f"The {' and '.join(columns)} has condition rules."
                    else:
                        # If there is not enough information, use the format of the second case
                        columns = []
                        if isinstance(column, list):
                            columns = column
                        else:
                            columns = [column]
                        rule["original_example"] = f"The {' and '.join(columns)} has condition rules."
                else:
                    # If there is no originalRule, use the format of the second case
                    columns = []
                    if isinstance(column, list):
                        columns = column
                    else:
                        columns = [column]
                    rule["original_example"] = f"The {' and '.join(columns)} has condition rules."
                
                # Set the example for delete rule
                rule["refine_example"] = "Delete this conditional rule"
            
            elif rule["type"] == "MultipleDuplicate":
                # Process MultipleDuplicate type delete rules
                # If it is a list, join the column names
                if isinstance(column, list):
                    column_str = " and ".join(column)
                else:
                    column_str = column
                
                # Add example
                rule["original_example"] = f"The combination of {column_str} cannot be duplicated."
                rule["refine_example"] = "Delete this multipleDuplicate rule."
    
    # Process addRules for MultipleDuplicate type rules
    if "addRules" in result["refineDict"] and result["refineDict"]["addRules"]:
        for rule in result["refineDict"]["addRules"]:
            if rule["type"] == "MultipleDuplicate":
                # Get column names
                column = rule["column"]
                # If it is a list, join the column names
                if isinstance(column, list):
                    column_str = ", ".join(column)
                else:
                    column_str = column
                
                # Add example
                rule["original_example"] = f"There is no multipleDuplicate rule of {column_str} in original rules."
                rule["refine_example"] = f"Add multipleDuplicate rule of {column_str}."
    
    return result

# For each character, add a strikethrough
def add_strikethrough(text):
    return ''.join([char + '\u0336' for char in str(text)])