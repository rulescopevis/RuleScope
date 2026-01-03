import pandas as pd
import re

def detect_format(column, format):
    """
    Detect index positions of data that does not match the specified regular expression in a data column
    
    Parameters:
        column (pandas.Series): Data column to be checked
        format (str): Regular expression
        
    Returns:
        list: Index list of data that does not match the regular expression
    """
    
    formatIndexList = []
    
    # Iterate through each value and corresponding index in the series
    for idx, value in column.items():
        # Skip null values
        if pd.isna(value):
            continue
            
        # Check if it matches the regular expression
        if not re.match(format, str(value)):
            formatIndexList.append(idx)
            
    return formatIndexList