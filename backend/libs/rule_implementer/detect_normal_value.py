import pandas as pd

def detect_normal_value(column, valueList):
    """
    Detect index positions of values in valueList within a data column
    
    Parameters:
        column (pandas.Series): Data column to be checked
        valueList (list): List of values to be detected
        
    Returns:
        list: Index list of data with values in valueList
    """
    
    valueIndexList = []
    
    # Iterate through each value and corresponding index in the series
    for idx, value in column.items():
        # Skip null values
        if pd.isna(value):
            continue
            
        # If current value is in valueList, add its index
        if value in valueList:
            valueIndexList.append(idx)
    
    return sorted(valueIndexList)