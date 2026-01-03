from datetime import datetime
from typing import List, Dict, Union, Optional

def refine_comparison_numeric_date(compareList: List[Dict], 
                                 dataType: str,
                                 validFlag: bool,
                                 selectValueList: List[Dict],
                                 dateFormatList: Optional[List[str]] = None) -> Dict:
    
    def convert_to_datetime(value: str) -> datetime:
        try:
            if isinstance(value, datetime):
                return value
                
            date_formats = dateFormatList if dateFormatList else [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%Y.%m.%d"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date string: {value}")
        except Exception as e:
            raise ValueError(f"Date conversion error: {str(e)}")

    def get_all_compare_relations(original_relation: str) -> List[str]:
        all_relations = ["larger", "larger_equal", "equal", "smaller", "smaller_equal", "not_equal"]
        # Exclude original relation
        return [rel for rel in all_relations if rel != original_relation]

    def check_relation(value1: Union[float, datetime], 
                      value2: Union[float, datetime], 
                      relation: str) -> bool:
        if relation == "larger":
            return value1 > value2
        elif relation == "larger_equal":
            return value1 >= value2
        elif relation == "equal":
            return value1 == value2
        elif relation == "smaller":
            return value1 < value2
        elif relation == "smaller_equal":
            return value1 <= value2
        elif relation == "not_equal":
            return value1 != value2
        return False

    def find_valid_relations(value1: Union[float, datetime], 
                           value2: Union[float, datetime], 
                           want_valid: bool,
                           original_relation: str) -> List[str]:
        all_relations = get_all_compare_relations(original_relation)
        valid_relations = []
        
        for relation in all_relations:
            is_valid = check_relation(value1, value2, relation)
            if (is_valid and want_valid) or (not is_valid and not want_valid):
                valid_relations.append(relation)
                
        return valid_relations

    def check_original_relation(value1: Union[float, datetime], 
                              value2: Union[float, datetime], 
                              relation: str) -> bool:
        return check_relation(value1, value2, relation)

    try:
        if dataType not in ["numeric", "datetime"]:
            raise ValueError("Invalid dataType. Must be 'numeric' or 'datetime'")

        # Handle empty compareList case
        if not compareList:
            if len(selectValueList) < 2:
                return {
                    "refineStatus": False,
                    "refineCompareRelationList": []
                }

            # Get column names from first data entry
            columns = list(selectValueList[0].keys())
            if len(columns) < 2:
                return {
                    "refineStatus": False,
                    "refineCompareRelationList": []
                }

            # Use first two columns for comparison
            column1, column2 = columns[0], columns[1]
            all_relations = ["larger", "larger_equal", "equal", "smaller", "smaller_equal", "not_equal"]
            valid_relations = set(all_relations)

            # Check all data pairs against each relation
            for select_value in selectValueList:
                value1 = select_value.get(column1)
                value2 = select_value.get(column2)

                if value1 is None or value2 is None:
                    continue

                try:
                    if dataType == "datetime":
                        value1 = convert_to_datetime(value1)
                        value2 = convert_to_datetime(value2)
                    else:  # numeric
                        value1 = float(value1)
                        value2 = float(value2)

                    # Check each relation
                    current_valid_relations = set()
                    for relation in all_relations:
                        is_valid = check_relation(value1, value2, relation)
                        if (is_valid and validFlag) or (not is_valid and not validFlag):
                            current_valid_relations.add(relation)

                    # Intersection of valid relations
                    valid_relations.intersection_update(current_valid_relations)

                except (ValueError, TypeError):
                    continue

            # Return False if no valid relations found
            if not valid_relations:
                return {
                    "refineStatus": False,
                    "refineCompareRelationList": []
                }

            return {
                "refineStatus": True,
                "refineCompareRelationList": list(valid_relations)
            }

        # Original processing logic
        original_relation = compareList[0]["compareRelation"]
        valid_list = []
        invalid_list = []

        # Preprocessing: classify data into valid_list and invalid_list
        for select_value in selectValueList:
            value1 = select_value.get(compareList[0]["column1"])
            value2 = select_value.get(compareList[0]["column2"])
            
            if value1 is None or value2 is None:
                continue

            try:
                if dataType == "datetime":
                    value1 = convert_to_datetime(value1)
                    value2 = convert_to_datetime(value2)
                else:  # numeric
                    value1 = float(value1)
                    value2 = float(value2)

                # Check if original relation is satisfied
                if check_original_relation(value1, value2, original_relation):
                    valid_list.append(select_value)
                else:
                    invalid_list.append(select_value)
            except (ValueError, TypeError):
                continue

        # Select working list based on validFlag
        working_list = invalid_list if validFlag else valid_list
        
        # Return refineStatus False if working list is empty
        if not working_list:
            return {
                "refineStatus": False,
                "refineCompareRelationList": []
            }

        # Optimize relations using filtered data
        refine_relations = set()
        
        for select_value in working_list:
            value1 = select_value.get(compareList[0]["column1"])
            value2 = select_value.get(compareList[0]["column2"])
            
            if value1 is None or value2 is None:
                continue

            if dataType == "datetime":
                value1 = convert_to_datetime(value1)
                value2 = convert_to_datetime(value2)
            else:  # numeric
                value1 = float(value1)
                value2 = float(value2)

            valid_relations = find_valid_relations(value1, value2, validFlag, original_relation)
            
            if not refine_relations:
                refine_relations.update(valid_relations)
            else:
                refine_relations.intersection_update(valid_relations)
        refineCompareRelationList = []
        for relation in refine_relations:
            refineCompareRelationList.append({
                "column1": compareList[0]["column1"],
                "column2": compareList[0]["column2"],
                "compareRelation": relation
            })
        return {
            "refineStatus": len(refine_relations) > 0,
            "refineCompareRelationList": refineCompareRelationList
        }

    except Exception as e:
        return {
            "refineStatus": False,
            "refineCompareRelationList": [],
            "error": str(e)
        }