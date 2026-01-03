import pandas as pd
import numpy as np

def detect_multi_difference(df, columnName, orderCondition, differenceThreshold, tableDict):
    """
    Calculate differences between adjacent points in multidimensional space and check if they are within specified range
    
    Parameters:
        df (pandas.DataFrame): Data frame to be checked
        columnName (list): List of column names to be checked
        orderCondition (dict): Sort condition
        differenceThreshold (dict): Difference range, 
            {
                'start': float, 
                'end': float, 
                'startInclusive': bool, 
                'endInclusive': bool
            }
        tableDict (dict): Table configuration information
    
    Returns:
        list: List of dictionaries containing index pairs that do not meet difference requirements
    """
    # Parameter validation
    required_keys = ['start', 'end', 'startInclusive', 'endInclusive']
    if not all(key in differenceThreshold for key in required_keys):
        raise ValueError("differenceThreshold must contain all required keys: start, end, startInclusive, endInclusive")
    
    start = differenceThreshold['start']
    end = differenceThreshold['end']
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be less than or equal to end")
    
    if len(df) < 2:
        return []
    
    # Build sort conditions
    sort_columns = []
    sort_ascending = []
    
    for i in range(1, 4):
        column_key = f"firstOrderColumn" if i == 1 else f"secondOrderColumn" if i == 2 else "thirdOrderColumn"
        type_key = f"firstOrderType" if i == 1 else f"secondOrderType" if i == 2 else "thirdOrderType"
        
        if column_key in orderCondition:
            sort_columns.append(orderCondition[column_key])
            sort_ascending.append(orderCondition[type_key].lower() == "asc")
    
    # Process date columns
    if orderCondition['dateColumns'] != []:
        for col in orderCondition['dateColumns']:
            try:
                date_format = tableDict[col]['mainFormat']
                df[col] = pd.to_datetime(df[col], format=date_format)
            except (KeyError, ValueError):
                continue
    
    # Get sorted indices
    sorted_indices = df.sort_values(by=sort_columns, ascending=sort_ascending).index
    outlier_pairs = []
    
    # Traverse each pair of adjacent rows
    for i in range(len(sorted_indices) - 1):
        current_idx = sorted_indices[i]
        next_idx = sorted_indices[i + 1]
        
        # Check for null values
        has_null = False
        squared_diff_sum = 0
        
        for col in columnName:
            current_value = df.loc[current_idx, col]
            next_value = df.loc[next_idx, col]
            
            if pd.isna(current_value) or pd.isna(next_value):
                has_null = True
                break
            
            # Calculate square of difference for each dimension
            diff = abs(next_value - current_value)
            squared_diff_sum += diff * diff
        
        # If null values exist, skip checking this pair of adjacent points
        if has_null:
            continue
        
        # Calculate Euclidean distance
        total_diff = np.sqrt(squared_diff_sum)
        
        # Check if within range based on closed/open interval settings
        in_range = True
        if differenceThreshold['startInclusive']:
            in_range = in_range and total_diff >= start
        else:
            in_range = in_range and total_diff > start
            
        if differenceThreshold['endInclusive']:
            in_range = in_range and total_diff <= end
        else:
            in_range = in_range and total_diff < end
        
        if not in_range:
            outlier_pair = {
                "currentIndex": int(current_idx),
                "nextIndex": int(next_idx),
                "sortCurrentIndex": int(i),
                "sortNextIndex": int(i + 1)
            }
            outlier_pairs.append(outlier_pair)
    
    return outlier_pairs