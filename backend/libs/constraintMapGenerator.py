import pandas as pd
import json

def generate_constraint_map(validation_rules_path, csv_data_path, save_path=None):
    constraint_map = {}
    validation_rules = json.load(open(validation_rules_path, 'r', encoding='utf-8'))
    csv_data = pd.read_csv(csv_data_path)
    for column in csv_data.columns:
        if column in validation_rules.keys():
            constraint_map[column] = []
        else:
            raise ValueError(f"Column {column} not found in validation rules.")
    for column in csv_data.columns:
        # generate compare rules map
        if "numericCompareList" in validation_rules.keys():
            for item in validation_rules["numericCompareList"]:
                if "column1" in item.keys() and "column2" in item.keys():
                    constraint_map[item["column1"]].append(item["column2"])
                    constraint_map[item["column2"]].append(item["column1"])
                else:
                    raise ValueError("Invalid compare rule format.")
        if "dateCompareList" in validation_rules.keys():
            for item in validation_rules["dateCompareList"]:
                if "column1" in item.keys() and "column2" in item.keys():
                    constraint_map[item["column1"]].append(item["column2"])
                    constraint_map[item["column2"]].append(item["column1"])
                else:
                    raise ValueError("Invalid date compare rule format.")
        # generate condition and logical rules map
        if "conditionLogicColumnList" in validation_rules.keys():
            for item in validation_rules["conditionLogicColumnList"]:
                if "conditionColumns" in item.keys() and "constraintColumns" in item.keys():
                    for cond_col in item["conditionColumns"]:
                        for other_cond_col in item["conditionColumns"]:
                            if cond_col != other_cond_col:
                                constraint_map[cond_col].append(other_cond_col)
                        for constr_col in item["constraintColumns"]:
                            constraint_map[cond_col].append(constr_col)
                    for constr_col in item["constraintColumns"]:
                        for other_constr_col in item["constraintColumns"]:
                            if constr_col != other_constr_col:
                                constraint_map[constr_col].append(other_constr_col)
                        for cond_col in item["conditionColumns"]:
                            constraint_map[constr_col].append(cond_col)
                else:
                    raise ValueError("Invalid condition logic rule format.")
        # generate multi-difference rules map
        if "multiDifference" in validation_rules.keys():
            for item in validation_rules["multiDifference"]:
                if "columns" in item.keys():
                    for col1 in item["columns"]:
                        for col2 in item["columns"]:
                            if col1 != col2:
                                constraint_map[col1].append(col2)
                else:
                    raise ValueError("Invalid multi-difference rule format.")
        # generate multi-duplicate rules map
        if "multipleDuplicateColumnsList" in validation_rules.keys():
            for columns in validation_rules["multipleDuplicateColumnsList"]:
                for col1 in columns:
                    for col2 in columns:
                        if col1 != col2:
                            constraint_map[col1].append(col2)
        # generate multi-condition and logical rules map
        if "multipleConditionLogicColumnList" in validation_rules.keys():
            for item in validation_rules["multipleConditionLogicColumnList"]:
                if "conditionColumns" in item.keys() and "constraintColumns" in item.keys():
                    for cond_col in item["conditionColumns"]:
                        for other_cond_col in item["conditionColumns"]:
                            if cond_col != other_cond_col:
                                constraint_map[cond_col].append(other_cond_col)
                        for constr_col in item["constraintColumns"]:
                            constraint_map[cond_col].append(constr_col)
                    for constr_col in item["constraintColumns"]:
                        for other_constr_col in item["constraintColumns"]:
                            if constr_col != other_constr_col:
                                constraint_map[constr_col].append(other_constr_col)
                        for cond_col in item["conditionColumns"]:
                            constraint_map[constr_col].append(cond_col)
                else:
                    raise ValueError("Invalid multi-condition logic rule format.")
        # generate substring rules map
        if "substringList" in validation_rules.keys():
            for item in validation_rules["substringList"]:
                if "column1" in item.keys() and "column2" in item.keys():
                    constraint_map[item["column1"]].append(item["column2"])
                    constraint_map[item["column2"]].append(item["column1"])
                else:
                    raise ValueError("Invalid substring rule format.")
        # generate lookup rules map
        if "lookupList" in validation_rules.keys():
            for item in validation_rules["lookupList"]:
                if "parentColumnName" in item.keys() and "childColumnName" in item.keys():
                    constraint_map[item["parentColumnName"]].append(item["childColumnName"])
                    constraint_map[item["childColumnName"]].append(item["parentColumnName"])
                else:
                    raise ValueError("Invalid lookup rule format.")
    popList = []
    for column in constraint_map.keys():
        constraint_map[column] = list(set(constraint_map[column]))
        if constraint_map[column] == []:
            popList.append(column)
    for column in popList:
        constraint_map.pop(column)
    if save_path:
        with open(save_path, 'w') as f:
            json.dump(constraint_map, f, indent=4)
    
    return constraint_map
