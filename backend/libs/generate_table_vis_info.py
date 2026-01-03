import json
import pandas as pd

def generate_table_vis_info(tableInfoPath: str, binNum: int, savePath: str, df: pd.DataFrame, decimal_places=6, specialMissingValueList=None):
    """
    Generate table visualization information.

    Args:
        tableInfoPath (str): Path to table info file.
        binNum (int): Number of bins.
        savePath (str): Output file path.
        df (pd.DataFrame): Dataframe.
        decimal_places (int, optional): Decimal precision. Defaults to 6.
        specialMissingValueList (list, optional): Special missing values list, e.g., [{"columnName": [special_values]}]. Defaults to None.
    """
    visInfo = {}
    with open(tableInfoPath, 'r') as f:
        tableInfo = json.load(f)

    for column in tableInfo.keys():
        if tableInfo[column]['type'] == 'character':
            valueList = tableInfo[column]['valueList']
            
            current_special_missing_values = []
            if specialMissingValueList:
                for item in specialMissingValueList:
                    if column in item:
                        current_special_missing_values = item[column]
                        break
            
            valid_values = []
            for item in valueList:
                value = item["value"]
                if not pd.isna(value) and value not in current_special_missing_values:
                    valid_values.append(item)
            
            sortedValueList = sorted(valid_values, key=lambda x: x["count"], reverse=True)
            visInfo[column] = {}
            for item in sortedValueList:
                item['index'] = df[df[column] == item["value"]].index.tolist()
                item['duration'] = str(item["value"])
            visInfo[column]['valueList'] = sortedValueList

        elif tableInfo[column]['type'] == 'numeric':
            valueList = tableInfo[column]['valueList']
            
            current_special_missing_values = []
            if specialMissingValueList:
                for item in specialMissingValueList:
                    if column in item:
                        current_special_missing_values = item[column]
                        break
            
            valid_values = []
            for item in valueList:
                value = item["value"]
                if not pd.isna(value) and value not in current_special_missing_values:
                    valid_values.append(item)
                    
            unique_values = len(set(item["value"] for item in valid_values))
            visInfo[column] = {}
            
            if unique_values <= binNum:
                for item in valid_values:
                    item['duration'] = str(item['value'])
                visInfo[column]['valueList'] = valid_values
                visInfo[column]['index'] = [df[df[column] == item["value"]].index.tolist() for item in valid_values]
            else:
                sortedValueList = sorted(valid_values, key=lambda x: x["value"])
                min_value = sortedValueList[0]["value"]
                max_value = sortedValueList[-1]["value"]
                bin_width = (max_value - min_value) / binNum
                
                bins = []
                current_bin = {"count": 0, "values": []}
                current_bin_start = min_value
                
                for item in sortedValueList:
                    if item["value"] > current_bin_start + bin_width and len(bins) < binNum - 1:
                        if current_bin["values"]:
                            mid_value = (current_bin_start + (current_bin_start + bin_width)) / 2
                            total_count = sum(item["count"] for item in sortedValueList)
                            bin_dict = {
                                "value": round(mid_value, decimal_places),
                                "count": current_bin["count"],
                                "rate": round(current_bin["count"] / total_count, decimal_places),
                                "duration": f"{round(current_bin_start, 2)}-{round(current_bin_start + bin_width, 2)}"
                            }
                            
                            bin_dict["index"] = []
                            for val in current_bin["values"]:
                                bin_dict["index"].extend(df[df[column] == val["value"]].index.tolist())
                            
                            bins.append(bin_dict)
                            current_bin = {"count": 0, "values": []}
                            current_bin_start += bin_width
                    
                    current_bin["count"] += item["count"]
                    current_bin["values"].append(item)
                
                if current_bin["values"]:
                    mid_value = (current_bin_start + max_value) / 2
                    total_count = sum(item["count"] for item in sortedValueList)
                    bin_dict = {
                        "value": round(mid_value, decimal_places),
                        "count": current_bin["count"],
                        "rate": round(current_bin["count"] / total_count, decimal_places),
                        "duration": f"{round(current_bin_start, 2)}-{round(max_value, 2)}"
                    }
                    
                    bin_dict["index"] = []
                    for val in current_bin["values"]:
                        bin_dict["index"].extend(df[df[column] == val["value"]].index.tolist())
                    
                    bins.append(bin_dict)
                
                visInfo[column]['valueList'] = bins

        elif tableInfo[column]['type'] == 'datetime':
            valueList = tableInfo[column]['valueList']
            mainFormat = tableInfo[column]['mainFormat']
            
            current_special_missing_values = []
            if specialMissingValueList:
                for item in specialMissingValueList:
                    if column in item:
                        current_special_missing_values = item[column]
                        break
            
            valid_values = []
            for item in valueList:
                value = item["value"]
                if not pd.isna(value) and value not in current_special_missing_values:
                    valid_values.append(item)
            
            for item in valid_values:
                item['duration'] = str(item['value'])
                item['index'] = df[df[column] == item["value"]].index.tolist()
                    
            visInfo[column] = {}
            visInfo[column]['valueList'] = valid_values

    with open(savePath, "w") as json_file:
        json.dump(visInfo, json_file, indent=4)

