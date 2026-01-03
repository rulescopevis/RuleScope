import pandas as pd
import copy
import json
import os
import numpy as np
import sys

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from rule_generator.cell_level.type import detect_column_types
from rule_generator.cell_level.integrity_duplicate import missing_duplicate_flag
from rule_generator.dependency_level.order import table_order_condition
from rule_generator.cell_level.character_info import (
    character_value,
    character_missing,
    character_duplicate,
    character_sequence as column_character_sequence,
)
from rule_generator.cell_level.numeric_info import (
    numeric_static,
    numeric_decimal_value,
    numeric_missing as column_numeric_missing,
    numeric_order_duplicate,
    numeric_difference as column_numeric_difference,
)
from rule_generator.cell_level.date_info import analyze_date_column, date_order, date_missing, date_duplicates
from rule_generator.domain_info import domainInfo
from generate_vis_info import generate_vis_info
from generate_table_vis_info import generate_table_vis_info

from rule_generator.cell_level.format_character import character_format
from rule_generator.dependency_level.domain_consistency_same_represent import character_same_represent
from rule_generator.dependency_level.domain_consistency_differenet_domain import character_domain
from rule_generator.cell_level.range import numeric_range
from rule_generator.dependency_level.sequence import character_sequence
from rule_generator.dependency_level.difference import numeric_difference

from rule_generator.dependency_level.comparison_relations_numeric import numeric_compareRelations
from rule_generator.dependency_level.comparison_relations_date import date_compareRelations
from rule_generator.dependency_level.comparison_relations_character import character_substring
from rule_generator.dependency_level.computational_relations import numeric_formula
from rule_generator.dependency_level.mapping_and_cardinality import character_lookup
from rule_generator.dependency_level.logical_and_condition import condition_logic_simple
from rule_generator.dependency_level.logical_and_condition_multiple import condition_logic_multiple
from rule_generator.dependency_level.difference_multiple import numeric_difference_multi
from rule_generator.dependency_level.duplicate_multiple import duplicate_duplicate_multi

def weighted_random_select(input_list, select_number=100):
    """
    Randomly select a given number of elements, favoring earlier indices.

    Args:
        input_list: Input list.
        select_number: Number of elements to select.

    Returns:
        list: Selected elements.
    """
    try:
        if not input_list:
            return []
        
        if select_number <= 0:
            return []
            
        if select_number >= len(input_list):
            return input_list.copy()
        
        weights = []
        for i in range(len(input_list)):
            weight = 1 / (i + 1)
            weights.append(weight)
            
        total_weight = sum(weights)
        normalized_weights = [w/total_weight for w in weights]
        
        selected_indices = np.random.choice(
            len(input_list),
            size=select_number,
            replace=False,
            p=normalized_weights
        )
        
        return [input_list[i] for i in selected_indices]
        
    except Exception as e:
        print(f"Error in weighted_random_select: {str(e)}")
        return []

def combine_same_entity(valueList, sameEntityList, rate_decimal=4):
    """
    Merge stats for different expressions of the same entity.

    Args:
        valueList: Original stats list.
        sameEntityList: Expressions for the same entity.
        rate_decimal: Decimal places for rate.

    Returns:
        Updated stats list.
    """
    value_dict = {item["value"]: item for item in valueList}
    processed_entities = set()
    result = []
    total_count = sum(item["count"] for item in valueList)
    for entity_group in sameEntityList:
        main_entity = entity_group["mainEntity"]
        same_entities = entity_group["sameEntityList"]
        
        if main_entity in processed_entities:
            continue
            
        main_stats = value_dict.get(main_entity, {"value": main_entity, "count": 0, "rate": 0})
        total_group_count = main_stats["count"]
        same_entity_stats = []
        for entity in same_entities:
            if entity in value_dict and entity not in processed_entities:
                stats = value_dict[entity]
                total_group_count += stats["count"]
                same_entity_stats.append({
                    "value": entity,
                    "count": stats["count"],
                    "rate": round(stats["count"] / total_count, rate_decimal)
                })
                processed_entities.add(entity)
        
        combined_stats = {
            "value": main_entity,
            "count": total_group_count,
            "rate": round(total_group_count / total_count, rate_decimal)
        }
        if same_entity_stats:
            combined_stats["sameEntityList"] = same_entity_stats
            
        result.append(combined_stats)
        processed_entities.add(main_entity)
    
    for value, stats in value_dict.items():
        if value not in processed_entities:
            result.append({
                "value": value,
                "count": stats["count"],
                "rate": round(stats["count"] / total_count, rate_decimal)
            })
    
    return result

def generate_sample_df(df, sampleNum=100, min_non_empty_ratio=0.3):
    """
    Sample rows and ensure a minimum non-empty ratio by resampling if needed.

    Parameters:
        df (pandas.DataFrame): Input dataframe.
        sampleNum (int): Number of rows to sample.
        min_non_empty_ratio (float): Minimum non-empty ratio required.

    Returns:
        pandas.DataFrame: Sampled dataframe.
    """
    def calculate_non_empty_ratio(df):
        """Compute ratio of non-empty values (np.nan and empty strings counted as empty)."""
        is_not_empty = df.notna() & (df != '')
        return is_not_empty.mean().mean()
    
    def get_non_empty_row_mask(df):
        """Get per-row non-empty ratio mask."""
        is_not_empty = df.notna() & (df != '')
        return is_not_empty.mean(axis=1)
    
    # Create deep copy to avoid modifying original dataframe
    df_copy = copy.deepcopy(df)
    
    # Check if sampleNum is larger than dataframe size
    if sampleNum > len(df_copy):
        return df_copy
        
    random_indices = np.random.choice(df_copy.index, size=sampleNum, replace=False)
    sampled_df = df_copy.loc[random_indices]

    current_non_empty_ratio = calculate_non_empty_ratio(sampled_df)
    
    if current_non_empty_ratio >= min_non_empty_ratio:
        return sampled_df
        
    row_non_empty_ratios = get_non_empty_row_mask(df_copy)
    rows_with_enough_values = df_copy.index[row_non_empty_ratios >= min_non_empty_ratio]
    
    if len(rows_with_enough_values) == 0:
        max_non_empty_ratio = row_non_empty_ratios.max()
        rows_with_enough_values = df_copy.index[row_non_empty_ratios >= max_non_empty_ratio * 0.9]
    
    # Return sampled dataframe
    return df_copy.loc[rows_with_enough_values]


def convert_to_numeric(data_list):
    """
    Convert a list of values to numeric types when possible.

    Returns a list of floats or ints if conversion succeeds; otherwise returns an empty list.
    """
    try:
        float_list = [float(x) for x in data_list]
        if all(str(x).isdigit() for x in data_list):
            return [int(x) for x in float_list]
        return float_list
    except (ValueError, TypeError):
        return []


def generate_order_dataframe(
    df,
    first_order_column,
    first_order_type,
    second_order_column=None,
    second_order_type=None,
    third_order_column=None,
    third_order_type=None,
    date_columns=None,
    table_dict=None,
):
    """
    Sort a dataframe by up to three columns with optional datetime parsing.
    """
    if not first_order_column or not first_order_type:
        raise ValueError("First priority sort column and type are required")

    df_copy = df.copy(deep=True)

    if date_columns and table_dict:
        for col in date_columns:
            try:
                date_format = table_dict[col]['mainFormat']
                df_copy[col] = pd.to_datetime(df_copy[col], format=date_format)
            except (KeyError, ValueError) as error:
                print(f"Failed to convert date column {col}: {str(error)}")
                continue

    sort_columns = []
    ascending_list = []

    sort_columns.append(first_order_column)
    ascending_list.append(first_order_type.lower() == 'asc')

    if second_order_column and second_order_type:
        sort_columns.append(second_order_column)
        ascending_list.append(second_order_type.lower() == 'asc')

    if third_order_column and third_order_type:
        sort_columns.append(third_order_column)
        ascending_list.append(third_order_type.lower() == 'asc')

    return df_copy.sort_values(by=sort_columns, ascending=ascending_list)

def find_substring_pairs(df, parentColumn, childColumn):
    """
    Find substring relationships between parent and child columns.

    Args:
        df (pandas.DataFrame): Input dataframe.
        parentColumn (str): Parent column name.
        childColumn (str): Child column name.

    Returns:
        list: Substring key-value pairs.
    """
    try:
        result_dict = {}
        for _, row in df.iterrows():
            parent_value = str(row[parentColumn])
            child_value = str(row[childColumn])
            if child_value and parent_value and child_value in parent_value:
                if parent_value in result_dict:
                    if child_value not in result_dict[parent_value]:
                        result_dict[parent_value].append(child_value)
                else:
                    result_dict[parent_value] = [child_value]
        value_pair_list = [
            {
                "parentColumnValue": parent_value,
                "childColumnValueList": child_values
            }
            for parent_value, child_values in result_dict.items()
            if child_values
        ]
        
        return value_pair_list
        
    except Exception as e:
        print(f"Error while finding substring relationships: {str(e)}")
        return []

def generate_validation_rule(df, dataName, model, savePath, orderConditionDict={}):
    sampledf = generate_sample_df(df, sampleNum=100)
    orderdf = generate_sample_df(df, sampleNum=100)

    initialResult = detect_column_types(df)
    if initialResult["result"]:
        tableDict = copy.deepcopy(initialResult["columnTypes"])
        validationDict = copy.deepcopy(initialResult["columnTypes"])
    else:
        print("[ERROR!] Column type detection failed")
        return None

    for column in tableDict.keys():
        if tableDict[column]["type"] == "datetime":
            dateInfo = analyze_date_column(df[column])
            if dateInfo["valueStatus"]:
                tableDict[column]["valueList"] = dateInfo["valueList"]
                tableDict[column]["mainFormat"] = dateInfo["mainFormat"]
                tableDict[column]["mainPattern"] = dateInfo["mainPattern"]
                validationDict[column]["dateFormat"] = dateInfo["mainFormat"]
                validationDict[column]["formatREGEX"] = dateInfo["mainPattern"]
            else:
                print(f"[ERROR!] [Column:{column}] Date value detection failed: {dateInfo['valueList']}")

    domainInfoResult = domainInfo(sampledf, model)
    if domainInfoResult["result"]:
        validationDict["domainDescription"] = domainInfoResult["domainDescription"]
    else:
        print("[ERROR!] Domain info detection failed")
        return None

    missingDuplicateFlag = missing_duplicate_flag(sampledf, validationDict["domainDescription"], model)

    table_order_condition_result = table_order_condition(orderdf, validationDict["domainDescription"], model)
    evaluationOrderConditionDict = copy.deepcopy(table_order_condition_result["tableOrderCondition"])

    if table_order_condition_result["result"]:
        orderConditionDict = copy.deepcopy(table_order_condition_result["tableOrderCondition"])
        if orderConditionDict["firstOrderColumn"] == "None":
            orderdf = df.copy(deep=True)
        else:
            orderConditionDict["dateColumns"] = []
            firstOrderColumn = orderConditionDict["firstOrderColumn"]
            firstOrderType = orderConditionDict["firstOrderType"]
            if tableDict[firstOrderColumn]["type"] == "datetime":
                orderConditionDict["dateColumns"].append(firstOrderColumn)
            if orderConditionDict["secondOrderColumn"] == "None":
                orderdf = generate_order_dataframe(
                    df,
                    firstOrderColumn,
                    firstOrderType,
                    date_columns=orderConditionDict["dateColumns"],
                    table_dict=tableDict,
                )
            else:
                secondOrderColumn = orderConditionDict["secondOrderColumn"]
                secondOrderType = orderConditionDict["secondOrderType"]
                if tableDict[secondOrderColumn]["type"] == "datetime":
                    orderConditionDict["dateColumns"].append(secondOrderColumn)
                if orderConditionDict["thirdOrderColumn"] == "None":
                    orderdf = generate_order_dataframe(
                        df,
                        firstOrderColumn,
                        firstOrderType,
                        secondOrderColumn,
                        secondOrderType,
                        date_columns=orderConditionDict["dateColumns"],
                        table_dict=tableDict,
                    )
                else:
                    thirdOrderColumn = orderConditionDict["thirdOrderColumn"]
                    thirdOrderType = orderConditionDict["thirdOrderType"]
                    if tableDict[thirdOrderColumn]["type"] == "datetime":
                        orderConditionDict["dateColumns"].append(thirdOrderColumn)
                    orderdf = generate_order_dataframe(
                        df,
                        firstOrderColumn,
                        firstOrderType,
                        secondOrderColumn,
                        secondOrderType,
                        thirdOrderColumn,
                        thirdOrderType,
                        date_columns=orderConditionDict["dateColumns"],
                        table_dict=tableDict,
                    )
    else:
        orderdf = df.copy(deep=True)

    if orderConditionDict != {}:
        orderConditionDict["dateColumns"] = []
        firstOrderColumn = orderConditionDict["firstOrderColumn"]
        firstOrderType = orderConditionDict["firstOrderType"]
        if tableDict[firstOrderColumn]["type"] == "datetime":
            orderConditionDict["dateColumns"].append(firstOrderColumn)
        if orderConditionDict["secondOrderColumn"] == "None":
            orderdf = generate_order_dataframe(
                df,
                firstOrderColumn,
                firstOrderType,
                date_columns=orderConditionDict["dateColumns"],
                table_dict=tableDict,
            )
        else:
            secondOrderColumn = orderConditionDict["secondOrderColumn"]
            secondOrderType = orderConditionDict["secondOrderType"]
            if tableDict[secondOrderColumn]["type"] == "datetime":
                orderConditionDict["dateColumns"].append(secondOrderColumn)
            if orderConditionDict["thirdOrderColumn"] == "None":
                orderdf = generate_order_dataframe(
                    df,
                    firstOrderColumn,
                    firstOrderType,
                    secondOrderColumn,
                    secondOrderType,
                    date_columns=orderConditionDict["dateColumns"],
                    table_dict=tableDict,
                )
            else:
                thirdOrderColumn = orderConditionDict["thirdOrderColumn"]
                thirdOrderType = orderConditionDict["thirdOrderType"]
                if tableDict[thirdOrderColumn]["type"] == "datetime":
                    orderConditionDict["dateColumns"].append(thirdOrderColumn)
                orderdf = generate_order_dataframe(
                    df,
                    firstOrderColumn,
                    firstOrderType,
                    secondOrderColumn,
                    secondOrderType,
                    thirdOrderColumn,
                    thirdOrderType,
                    date_columns=orderConditionDict["dateColumns"],
                    table_dict=tableDict,
                )
    else:
        orderdf = df.copy(deep=True)

    for column in tableDict.keys():
        validationDict[column]["specialMissingValueList"] = [None, "", "nan"]
        validationDict[column]["missingValueFlag"] = False
        validationDict[column]["duplicateFlag"] = False

        if column in missingDuplicateFlag["missingValueFlag"]:
            validationDict[column]["missingDetectFlag"] = True
        else:
            validationDict[column]["missingDetectFlag"] = False

        if column in missingDuplicateFlag["specialMissingValueDict"].keys():
            validationDict[column]["specialMissingValueList"].extend(
                missingDuplicateFlag["specialMissingValueDict"][column]
            )
        if column in missingDuplicateFlag["duplicateFlag"]:
            validationDict[column]["duplicateDetectFlag"] = True
        else:
            validationDict[column]["duplicateDetectFlag"] = False

        if tableDict[column]["type"] == "character":
            characterValue = character_value(df[column], count_rate_decimal=5)
            if characterValue["valueStatus"]:
                tableDict[column]["valueList"] = characterValue["valueList"]
            else:
                print(f"[ERROR!] [Column:{column}] Character value detection failed: {characterValue['valueList']}")

            if orderConditionDict != {}:
                characterSequence = column_character_sequence(orderdf[column], sequence_rate_decimal=8)
                if characterSequence["sequenceStatus"]:
                    tableDict[column]["sequenceList"] = characterSequence["sequenceList"]
                    tableDict[column]["orderCondition"] = orderConditionDict
                else:
                    print(f"[ERROR!] [Column:{column}] Character sequence detection failed: {characterSequence['sequenceList']}")

            characterMissing = character_missing(
                df[column], special_missing_values=validationDict[column]["specialMissingValueList"]
            )
            if characterMissing["missingStatus"]:
                tableDict[column]["missingDict"] = characterMissing["missingDict"]
                if tableDict[column]["missingDict"]["count"] > 0:
                    validationDict[column]["missingValueFlag"] = True
            else:
                print(f"[ERROR!] [Column:{column}] Character missing detection failed: {characterMissing['missingDict']}")

            characterDuplicate = character_duplicate(df[column])
            if characterDuplicate["duplicateStatus"]:
                validationDict[column]["duplicateFlag"] = characterDuplicate["duplicateFlag"]
            else:
                print(f"[ERROR!] [Column:{column}] Character duplicate detection failed: {characterDuplicate['duplicateFlag']}")

        elif tableDict[column]["type"] == "numeric":
            numericStatic = numeric_static(df[column])
            if numericStatic["staticStatus"]:
                tableDict[column]["staticDict"] = numericStatic["staticDict"]
            else:
                print(f"[ERROR!] [Column:{column}] Numeric static detection failed: {numericStatic['staticDict']}")

            if numericStatic["distributionStatus"]:
                tableDict[column]["distribution"] = numericStatic["distribution"]
                validationDict[column]["distribution"] = numericStatic["distribution"]
            else:
                print(f"[ERROR!] [Column:{column}] Numeric distribution detection failed")

            numericDecimalValue = numeric_decimal_value(df[column], count_rate_decimal=5)
            if numericDecimalValue["valueStatus"]:
                tableDict[column]["valueList"] = numericDecimalValue["valueList"]
            else:
                print(f"[ERROR!] [Column:{column}] Numeric value detection failed")

            if orderConditionDict != {}:
                numericDifferenceResult = column_numeric_difference(orderdf[column])
                if numericDifferenceResult["differenceStatus"]:
                    tableDict[column]["difference"] = numericDifferenceResult["differenceList"]
                    tableDict[column]["relativeDifference"] = numericDifferenceResult["relativeDifferenceList"]
                    tableDict[column]["orderCondition"] = orderConditionDict
                else:
                    print(
                        f"[ERROR!] [Column:{column}] Numeric difference detection failed: {numericDifferenceResult['differenceList']}"
                    )
                    print(
                        f"[ERROR!] [Column:{column}] Numeric relative difference detection failed: {numericDifferenceResult['relativeDifferenceList']}"
                    )

            if validationDict[column]["specialMissingValueList"] != []:
                numericSpecialMissingValue = convert_to_numeric(validationDict[column]["specialMissingValueList"])
            else:
                numericSpecialMissingValue = []

            numericMissing = column_numeric_missing(df[column], numeric_missing_values=numericSpecialMissingValue)
            if numericMissing["missingStatus"]:
                tableDict[column]["missingDict"] = numericMissing["missingDict"]
                if tableDict[column]["missingDict"]["count"] > 0:
                    validationDict[column]["missingValueFlag"] = True
            else:
                print(f"[ERROR!] [Column:{column}] Numeric missing detection failed: {numericMissing['missingDict']}")

            numericOrderDuplicate = numeric_order_duplicate(df[column])
            if numericOrderDuplicate["duplicateStatus"]:
                validationDict[column]["duplicateFlag"] = True
            else:
                print(
                    f"[ERROR!] [Column:{column}] Numeric duplicate detection failed: {numericOrderDuplicate['duplicateFlag']}"
                )

            if numericOrderDuplicate["orderStatus"]:
                tableDict[column]["order"] = numericOrderDuplicate["orderType"]
            else:
                print(
                    f"[ERROR!] [Column:{column}] Numeric order detection failed: {numericOrderDuplicate['orderType']}"
                )

        elif tableDict[column]["type"] == "datetime":
            dateOrderResult = date_order(df[column], tableDict[column]["mainFormat"], tableDict[column]["mainPattern"])
            if dateOrderResult["orderStatus"]:
                tableDict[column]["order"] = dateOrderResult["order"]
            else:
                print(f"[ERROR!] [Column:{column}] Date order detection failed: {dateOrderResult['order']}")

            dateMissing = date_missing(df[column], special_missing_values=validationDict[column]["specialMissingValueList"])
            if dateMissing["missingStatus"]:
                tableDict[column]["missingDict"] = dateMissing["missingDict"]
                if tableDict[column]["missingDict"]["count"] > 0:
                    validationDict[column]["missingValueFlag"] = True
            else:
                print(f"[ERROR!] [Column:{column}] Date missing detection failed: {dateMissing['missingDict']}")

            dateDuplicate = date_duplicates(df[column])
            if dateDuplicate["duplicateStatus"]:
                validationDict[column]["duplicateFlag"] = True
            else:
                print(f"[ERROR!] [Column:{column}] Date duplicate detection failed: {dateDuplicate['duplicateFlag']}")

    tableInfoPath = f"{savePath}/table_info.json"
    filepathVisInfo = f"{savePath}/visInfo.json"
    filepathTableVisInfo = f"{savePath}/tableVisInfo.json"

    with open(tableInfoPath, "w") as json_file:
        json.dump(tableDict, json_file, indent=4)

    generate_vis_info(tableInfoPath, 200, filepathVisInfo)
    generate_table_vis_info(tableInfoPath, 10, filepathTableVisInfo, df=df)

    dataframe = df
    staticDetectDataframe = copy.deepcopy(dataframe)
    interRowDetectDataframe = copy.deepcopy(dataframe)
    characterList = []
    numericList = []
    dateList = []

    columns = list(tableDict.keys())

    for column in columns:
        if "valueList" in tableDict[column].keys():
            dataList = [item["value"] for item in tableDict[column]["valueList"]]
            if len(dataList) > 100:
                sampleDataList = weighted_random_select(dataList, 100)
            else:
                sampleDataList = dataList
        if tableDict[column]["type"] == "character":
            sameRepresentResult = character_same_represent(
                tableDict[column]["valueList"], column, validationDict["domainDescription"], model
            )
            if sameRepresentResult["status"]:
                validationDict[column]["sameEntityList"] = sameRepresentResult["sameEntityList"]
            else:
                validationDict[column]["sameEntityList"] = []
            characterList.append(column)

            formatResult = character_format(sampleDataList, column, validationDict["domainDescription"], model)
            if formatResult["status"]:
                validationDict[column]["format"] = formatResult["characterFormat"]
            else:
                validationDict[column]["format"] = []

            domainResult = character_domain(dataList, column, validationDict["domainDescription"], model)
            if domainResult["status"]:
                validationDict[column]["differentDomainList"] = domainResult["differentDomainList"]
            else:
                validationDict[column]["differentDomainList"] = []

            if "sequenceList" in tableDict[column].keys():
                sequenceResult = character_sequence(
                    tableDict[column]["sequenceList"], column, validationDict["domainDescription"], model
                )
                if sequenceResult["status"]:
                    validationDict[column]["sequenceRule"] = sequenceResult["characterSequence"]
                    validationDict[column]["orderCondition"] = tableDict[column]["orderCondition"]
                else:
                    validationDict[column]["sequenceRule"] = []
                    validationDict[column]["orderCondition"] = []
            continue
        elif tableDict[column]["type"] == "numeric":
            numericList.append(column)
            if "staticDict" in tableDict[column].keys():
                rangeInfo = numeric_range(
                    tableDict[column]["staticDict"], column, validationDict["domainDescription"], model
                )
                if rangeInfo["status"]:
                    validationDict[column]["range"] = rangeInfo["numericRange"]
                else:
                    validationDict[column]["range"] = []

            if "difference" in tableDict[column].keys():
                differenceInfo = numeric_difference(
                    tableDict[column]["difference"], tableDict[column]["relativeDifference"], column, model
                )
                if differenceInfo["status"]:
                    validationDict[column]["difference"] = differenceInfo["numericDifference"]
                    validationDict[column]["orderCondition"] = tableDict[column]["orderCondition"]
                else:
                    validationDict[column]["difference"] = {}
                    validationDict[column]["orderCondition"] = []
        elif tableDict[column]["type"] == "datetime":
            dateList.append(column)

    if len(numericList) >= 2:
        numeric_compareRelationsResult = numeric_compareRelations(
            numericList, validationDict["domainDescription"], model
        )
        if numeric_compareRelationsResult["status"]:
            validationDict["numericCompareList"] = numeric_compareRelationsResult["numericCompareList"]

    if len(dateList) >= 2:
        date_compareRelationsResult = date_compareRelations(dateList, validationDict["domainDescription"], model)
        if date_compareRelationsResult["status"]:
            validationDict["dateCompareList"] = date_compareRelationsResult["dateCompareList"]
            for item in date_compareRelationsResult["dateCompareList"]:
                validationDict[item["column1"]]["compareFlag"] = True
                validationDict[item["column2"]]["compareFlag"] = True
        else:
            validationDict["dateCompareList"] = []
    else:
        validationDict["dateCompareList"] = []

    substringDF = generate_sample_df(dataframe[characterList])
    substringInfo = character_substring(substringDF, validationDict["domainDescription"], model)
    if substringInfo["status"]:
        validationDict["substringList"] = substringInfo["substringList"]
        for item in validationDict["substringList"]:
            validationDict[item["childColumn"]]["substringFlag"] = True
            validationDict[item["parentColumn"]]["substringFlag"] = True
            item["valuePairList"] = find_substring_pairs(dataframe, item["childColumn"], item["parentColumn"])
    else:
        validationDict["substringList"] = []

    formulaInfo = numeric_formula(numericList, validationDict["domainDescription"], model)
    if formulaInfo["status"]:
        validationDict["formulaList"] = formulaInfo["formulaList"]
        for item in formulaInfo["formulaList"]:
            for column in item["variableList"]:
                if column in list(validationDict.keys()):
                    validationDict[column]["formulaFlag"] = True

    if len(characterList) >= 2:
        lookupDF = copy.deepcopy(dataframe[characterList])
        lookupInfo = character_lookup(lookupDF, validationDict["domainDescription"], model)
        if lookupInfo["status"]:
            validationDict["lookupList"] = lookupInfo["lookupList"]
            for item in lookupInfo["lookupList"]:
                validationDict[item["parentColumnName"]]["lookupParentFlag"] = True
                validationDict[item["childColumnName"]]["lookupChildFlag"] = True

    conditionInfo = condition_logic_simple(interRowDetectDataframe, tableDict, validationDict["domainDescription"], model)
    if conditionInfo["status"] and len(conditionInfo["conditionLogicColumnList"]) != 0:
        validationDict["conditionLogicColumnList"] = conditionInfo["conditionLogicColumnList"]
        for item in conditionInfo["conditionLogicColumnList"]:
            for column in item["conditionColumns"]:
                validationDict[column]["conditionFlag"] = True
            for column in item["constraintColumns"]:
                validationDict[column]["constraintFlag"] = True
    else:
        validationDict["conditionLogicColumnList"] = []

    multi_differenceInfo = numeric_difference_multi(staticDetectDataframe, validationDict["domainDescription"], model)
    if multi_differenceInfo["status"]:
        validationDict["multiDifference"] = multi_differenceInfo["multiDifference"]
        for item in multi_differenceInfo["multiDifference"]:
            for column in item["columns"]:
                validationDict[column]["multiDifferenceFlag"] = True
    else:
        validationDict["multiDifference"] = []

    multipleDuplicateInfo = duplicate_duplicate_multi(sampledf, validationDict["domainDescription"], model)
    if multipleDuplicateInfo["status"]:
        validationDict["multipleDuplicateColumnsList"] = multipleDuplicateInfo["multipleDuplicateColumnsList"]
        for item in multipleDuplicateInfo["multipleDuplicateColumnsList"]:
            for column in item:
                validationDict[column]["multipleDuplicateFlag"] = True
    else:
        validationDict["multipleDuplicateColumnsList"] = []

    multipleConditionInfo = condition_logic_multiple(interRowDetectDataframe, tableDict, validationDict["domainDescription"], model)
    if multipleConditionInfo["status"] and len(multipleConditionInfo["multipleConditionLogicColumnList"]) != 0:
        validationDict["multipleConditionLogicColumnList"] = multipleConditionInfo["multipleConditionLogicColumnList"]
        for item in multipleConditionInfo["multipleConditionLogicColumnList"]:
            for column in item["conditionColumns"]:
                validationDict[column]["multipleConditionFlag"] = True
            for column in item["constraintColumns"]:
                validationDict[column]["multipleConditionFlag"] = True
    else:
        validationDict["multipleConditionLogicColumnList"] = []

    with open(f"{savePath}/validation_rules.json", "w") as json_file:
        json.dump(validationDict, json_file, indent=4)

    return tableInfoPath
