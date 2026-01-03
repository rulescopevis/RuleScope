def detect_duplicate(column):
    """
    Detect index positions of duplicate data in a data column
    
    Parameters:
        column (pandas.Series): Data column to be checked
        
    Returns:
        list: List of indexes of all duplicate values
    """
    import pandas as pd
    
    duplicateIndexList = []
    
    # Get count of all non-null values
    value_counts = column.value_counts()
    
    # Get values that appear more than once
    duplicate_values = value_counts[value_counts > 1].index.tolist()
    
    # If duplicate values exist
    if duplicate_values:
        # Iterate through each value and corresponding index in the series
        for idx, value in column.items():
            # Skip null values
            if pd.isna(value):
                continue
                
            # If current value is in duplicate value list, add its index
            if value in duplicate_values:
                duplicateIndexList.append(idx)
    
    return sorted(duplicateIndexList)