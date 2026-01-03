import pandas as pd
import numpy as np

def detect_absolute_difference(df, columnName, orderCondition, differenceThreshold, tableDict):
    """
    Detect whether the difference between adjacent values in a data column is within the specified range (vectorized optimized version)
    
    Parameters:
        df (pandas.DataFrame): Data frame to be checked
        columnName (str): Column name to be checked
        orderCondition (dict): Sort condition
        differenceThreshold (dict): Difference range, 
            {
                'start': float, 
                'end': float, 
                'startInclusive': bool, 
                'endInclusive': bool
            }
    
    Returns:
        list: List of dictionaries containing index pairs that do not meet the difference requirement
    """
    
    # Parameter validation
    required_keys = ['start', 'end', 'startInclusive', 'endInclusive']
    if not all(key in differenceThreshold for key in required_keys):
        raise ValueError("differenceThreshold must contain all required keys: start, end, startInclusive, endInclusive")
    
    start = differenceThreshold['start']
    end = differenceThreshold['end']
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be less than or equal to end")
    
    # Determine floating point precision
    decimal_places = max(
        len(str(start).split('.')[-1]) if '.' in str(start) else 0,
        len(str(end).split('.')[-1]) if '.' in str(end) else 0
    )
    
    # Define tolerance for floating point comparison
    epsilon = 1e-10
    
    if len(df) < 2:
        return []
    
    # Create copy to avoid modifying original data
    df_copy = df.copy()
    
    # Build sort conditions
    sort_columns = []
    sort_ascending = []
    
    for i in range(1, 4):
        column_key = f"firstOrderColumn" if i == 1 else f"secondOrderColumn" if i == 2 else "thirdOrderColumn"
        type_key = f"firstOrderType" if i == 1 else f"secondOrderType" if i == 2 else "thirdOrderType"
        
        if column_key in orderCondition:
            sort_columns.append(orderCondition[column_key])
            sort_ascending.append(orderCondition[type_key].lower() == "asc")
    
    if orderCondition.get('dateColumns', []):
        for col in orderCondition['dateColumns']:
            try:
                date_format = tableDict[col]['mainFormat']
                df_copy[col] = pd.to_datetime(df_copy[col], format=date_format)
            except (KeyError, ValueError) as e:
                # Error converting date column, continue
                continue
    
    # Get sorted data
    df_sorted = df_copy.sort_values(by=sort_columns, ascending=sort_ascending)
    sorted_indices = df_sorted.index.to_numpy()
    
    # Vectorized get column values
    values = df_sorted[columnName].to_numpy()
    
    # Create arrays for current and next values
    current_values = values[:-1]
    next_values = values[1:]
    
    # Create valid value mask (both values are not null)
    valid_mask = ~(pd.isna(current_values) | pd.isna(next_values))
    
    # If no valid pairs, return directly
    if not valid_mask.any():
        return []
    
    # Vectorized rounding
    current_rounded = np.round(current_values[valid_mask], decimal_places)
    next_rounded = np.round(next_values[valid_mask], decimal_places)
    
    # Vectorized calculate differences
    diffs = np.abs(next_rounded - current_rounded)
    
    # Vectorized range check
    if differenceThreshold['startInclusive']:
        start_check = diffs >= (start - epsilon)
    else:
        start_check = diffs > (start + epsilon)
    
    if differenceThreshold['endInclusive']:
        end_check = diffs <= (end + epsilon)
    else:
        end_check = diffs < (end - epsilon)
    
    # Find indices outside the range
    in_range = start_check & end_check
    outlier_mask_valid = ~in_range
    
    # Map back to original indices
    valid_indices = np.where(valid_mask)[0]
    outlier_indices = valid_indices[outlier_mask_valid]
    
    # Build result list
    outlier_pairs = []
    for i in outlier_indices:
        outlier_pair = {
            "currentIndex": int(sorted_indices[i]),
            "nextIndex": int(sorted_indices[i + 1]),
            "sortCurrentIndex": int(i),
            "sortNextIndex": int(i + 1)
        }
        outlier_pairs.append(outlier_pair)
    
    return outlier_pairs


def detect_relative_difference(df, columnName, orderCondition, differenceThreshold, tableDict):
    """
    Detect whether the relative difference between adjacent values in a data column is within the specified range (vectorized optimized version)
    
    Parameters:
        df (pandas.DataFrame): Data frame to be checked
        columnName (str): Column name to be checked
        orderCondition (dict): Sort condition
        differenceThreshold (dict): Relative difference range, 
            {
                'start': float, 
                'end': float, 
                'startInclusive': bool, 
                'endInclusive': bool
            }
    
    Returns:
        list: List of dictionaries containing index pairs that do not meet the relative difference requirement
    """
    
    # Parameter validation
    required_keys = ['start', 'end', 'startInclusive', 'endInclusive']
    if not all(key in differenceThreshold for key in required_keys):
        raise ValueError("differenceThreshold must contain all required keys: start, end, startInclusive, endInclusive")
    
    start = differenceThreshold['start']
    end = differenceThreshold['end']
    if start > end:
        raise ValueError("Invalid differenceThreshold range: start must be less than or equal to end")
    
    # Determine floating point precision
    decimal_places = max(
        len(str(start).split('.')[-1]) if '.' in str(start) else 0,
        len(str(end).split('.')[-1]) if '.' in str(end) else 0
    )
    
    # Define tolerance for floating point comparison
    epsilon = 1e-10
    
    if len(df) < 2:
        return []
    
    # Create copy to avoid modifying original data
    df_copy = df.copy()
    
    # Build sort conditions
    sort_columns = []
    sort_ascending = []
    
    for i in range(1, 4):
        column_key = f"firstOrderColumn" if i == 1 else f"secondOrderColumn" if i == 2 else "thirdOrderColumn"
        type_key = f"firstOrderType" if i == 1 else f"secondOrderType" if i == 2 else "thirdOrderType"
        
        if column_key in orderCondition:
            sort_columns.append(orderCondition[column_key])
            sort_ascending.append(orderCondition[type_key].lower() == "asc")

    if orderCondition.get('dateColumns', []):
        for col in orderCondition['dateColumns']:
            try:
                date_format = tableDict[col]['mainFormat']
                df_copy[col] = pd.to_datetime(df_copy[col], format=date_format)
            except (KeyError, ValueError) as e:
                # Error converting date column, continue
                continue
    
    # Get sorted data
    df_sorted = df_copy.sort_values(by=sort_columns, ascending=sort_ascending)
    sorted_indices = df_sorted.index.to_numpy()
    
    # Vectorized get column values
    values = df_sorted[columnName].to_numpy()
    
    # Create arrays for current and next values
    current_values = values[:-1]
    next_values = values[1:]
    
    # Create valid value mask (both values are not null)
    valid_mask = ~(pd.isna(current_values) | pd.isna(next_values))
    
    # If no valid pairs, return directly
    if not valid_mask.any():
        return []
    
    # Vectorized rounding
    current_rounded = np.round(current_values[valid_mask], decimal_places)
    next_rounded = np.round(next_values[valid_mask], decimal_places)
    
    # Vectorized calculate absolute differences
    abs_diffs = np.abs(next_rounded - current_rounded)
    
    # Detect division by zero
    zero_mask = current_rounded == 0
    
    # Initialize relative difference array
    relative_diffs = np.zeros_like(abs_diffs)
    
    # Calculate relative differences for non-zero values
    non_zero_mask = ~zero_mask
    if non_zero_mask.any():
        relative_diffs[non_zero_mask] = abs_diffs[non_zero_mask] / np.abs(current_rounded[non_zero_mask])
    
    # Vectorized range check (non-zero values)
    if differenceThreshold['startInclusive']:
        start_check = relative_diffs >= (start - epsilon)
    else:
        start_check = relative_diffs > (start + epsilon)
    
    if differenceThreshold['endInclusive']:
        end_check = relative_diffs <= (end + epsilon)
    else:
        end_check = relative_diffs < (end - epsilon)
    
    # Find indices outside the range (including division by zero cases)
    in_range = start_check & end_check & non_zero_mask
    outlier_mask_valid = ~in_range
    
    # Map back to original indices
    valid_indices = np.where(valid_mask)[0]
    outlier_indices = valid_indices[outlier_mask_valid]
    
    # Build result list
    outlier_pairs = []
    for i in outlier_indices:
        outlier_pair = {
            "currentIndex": int(sorted_indices[i]),
            "nextIndex": int(sorted_indices[i + 1]),
            "sortCurrentIndex": int(i),
            "sortNextIndex": int(i + 1)
        }
        outlier_pairs.append(outlier_pair)
    
    return outlier_pairs