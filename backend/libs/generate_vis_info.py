import json
import pandas as pd

def generate_vis_info(tableInfoPath: str, binNum: int, savePath: str, decimal_places=6, specialMissingValueList=None):
    visInfo = {}
    with open(tableInfoPath, 'r') as f:
        tableInfo = json.load(f)
    for column in tableInfo.keys():
        if tableInfo[column]['type'] == 'character':
            valueList = tableInfo[column]['valueList']
            sortedValueList = sorted(valueList, key=lambda x: x["count"], reverse=True)
            visInfo[column] = {}
            visInfo[column]['valueList'] = sortedValueList
        elif tableInfo[column]['type'] == 'numeric':
            valueList = tableInfo[column]['valueList']   
            if specialMissingValueList:
                valid_values = [item for item in valueList 
                              if item["value"] is not None and 
                              str(item["value"]).strip() not in specialMissingValueList]
            else:
                valid_values = [item for item in valueList if item["value"] is not None]
                
            unique_values = len(set(item["value"] for item in valid_values))
            visInfo[column] = {}
            if unique_values <= binNum:
                visInfo[column]['valueList'] = valid_values
            else:
                minValue = tableInfo[column]['staticDict']['min']
                maxValue = tableInfo[column]['staticDict']['max']
                sortedValueList = sorted(valid_values, key=lambda x: x["value"])
                
                totalRange = maxValue - minValue
                binWidth = totalRange / binNum
                
                bins = []
                for i in range(binNum):
                    if i == 0:
                        bin_value = minValue
                        bin_start = minValue
                        bin_end = minValue + binWidth/2
                    elif i == binNum - 1:
                        bin_value = maxValue
                        bin_start = maxValue - binWidth/2
                        bin_end = maxValue
                    else:
                        bin_value = minValue + i * binWidth
                        bin_start = bin_value - binWidth/2
                        bin_end = bin_value + binWidth/2
                    
                    bins.append({
                        "value": round(bin_value, decimal_places),
                        "count": 0,
                        "rate": 0.0,
                        "_start": bin_start,
                        "_end": bin_end
                    })
                
                total_count = 0
                for item in sortedValueList:
                    current_value = item["value"]
                    current_count = item["count"]
                    total_count += current_count
                    
                    for bin_item in bins:
                        if (current_value > bin_item["_start"] and current_value <= bin_item["_end"]) or \
                        (bin_item["value"] == minValue and current_value == minValue):
                            bin_item["count"] += current_count
                            break
                
                for bin_item in bins:
                    bin_item["rate"] = round(bin_item["count"] / total_count if total_count > 0 else 0.0, decimal_places)
                    del bin_item["_start"]
                    del bin_item["_end"]
                    
                visInfo[column]['valueList'] = bins

        elif tableInfo[column]['type'] == 'datetime':
            valueList = tableInfo[column]['valueList']
            mainFormat = tableInfo[column]['mainFormat']
            visInfo[column] = {}
            
            valid_dates = []
            for item in valueList:
                if item['value'] is not None and (not specialMissingValueList or 
                   str(item['value']).strip() not in specialMissingValueList):
                    try:
                        date_value = pd.to_datetime(item['value'])
                        if '%H' in mainFormat or '%M' in mainFormat or '%S' in mainFormat:
                            formatted_date = date_value.strftime('%Y-%m-%d %H:%M:%S')
                        elif '%d' in mainFormat:
                            formatted_date = date_value.strftime('%Y-%m-%d')
                        else:
                            formatted_date = date_value.strftime('%Y-%m')
                        
                        valid_dates.append({
                            "value": formatted_date,
                            "count": item["count"],
                            "rate": item["rate"]
                        })
                    except:
                        continue
            
            sorted_dates = sorted(valid_dates, key=lambda x: x["value"])
            
            unique_dates = len(set(item["value"] for item in sorted_dates))
            if unique_dates <= binNum:
                visInfo[column]['valueList'] = sorted_dates
            else:
                min_date = pd.to_datetime(sorted_dates[0]["value"])
                max_date = pd.to_datetime(sorted_dates[-1]["value"])
                
                total_seconds = (max_date - min_date).total_seconds()
                bin_width_seconds = total_seconds / (binNum - 1)
                
                bins = []
                for i in range(binNum):
                    bin_date = min_date + pd.Timedelta(seconds=i * bin_width_seconds)
                    if i == binNum - 1:
                        bin_date = max_date
                        
                    if '%H' in mainFormat or '%M' in mainFormat or '%S' in mainFormat:
                        formatted_bin_date = bin_date.strftime('%Y-%m-%d %H:%M:%S')
                    elif '%d' in mainFormat:
                        formatted_bin_date = bin_date.strftime('%Y-%m-%d')
                    else:
                        formatted_bin_date = bin_date.strftime('%Y-%m')
                    
                    bins.append({
                        "value": formatted_bin_date,
                        "count": 0,
                        "rate": 0.0
                    })
                
                current_bin = 0
                total_count = 0
                
                for item in sorted_dates:
                    current_date = pd.to_datetime(item["value"])
                    current_count = item["count"]
                    total_count += current_count
                    
                    while (current_bin < binNum - 1 and 
                        current_date > min_date + pd.Timedelta(seconds=(current_bin + 1) * bin_width_seconds)):
                        current_bin += 1
                        
                    bins[current_bin]["count"] += current_count
                
                for bin_item in bins:
                    bin_item["rate"] = round(bin_item["count"] / total_count if total_count > 0 else 0.0, decimal_places)
                
                visInfo[column]['valueList'] = bins

    with open(savePath, "w") as json_file:
        json.dump(visInfo, json_file, indent=4)
