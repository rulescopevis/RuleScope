import pandas as pd

def detect_substring_character(columnList):
    """
    Detect whether two dataseries strings conform to substring relationship
    The first column string should be a substring of the second column string
    
    Args:
        columnList: Two dataseries to compare
    
    Returns:
        List of row indices that do not satisfy substring relationship
    """
    
    # Get two columns of data
    series1 = columnList[0]  # Should be substring
    series2 = columnList[1]  # Should be main string
    
    # Initialize result list
    invalid_index = []
    
    # Traverse each row for comparison
    for idx in series1.index:
        # Skip rows with null values
        if pd.isna(series1[idx]) or pd.isna(series2[idx]):
            continue
            
        # Convert to string for comparison
        str1 = str(series1[idx]).strip()
        str2 = str(series2[idx]).strip()
        
        # Check if str1 is a substring of str2
        if str1 not in str2:
            invalid_index.append(idx)
            
    return invalid_index