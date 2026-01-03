def detect_multi_duplicate(columnList):
    """
    Detect if there are duplicate combination values in multiple columns
    
    Parameters:
        columnList: list of pandas.Series, list of columns to check for duplicates
    
    Returns:
        list: Index list of rows with duplicate values
    """
    # Input validation
    if not columnList or len(columnList) < 2:
        raise ValueError("columnList must contain at least two Series")
    
    # Validate that all Series have the same indices
    first_index = columnList[0].index
    for series in columnList[1:]:
        if not series.index.equals(first_index):
            raise ValueError("All Series must have the same indices")
    
    # Combine all columns into a DataFrame
    import pandas as pd
    temp_df = pd.concat(columnList, axis=1)
    
    # Find duplicate rows, but exclude rows with all null values
    # First mark rows with all null values
    all_na_rows = temp_df.isna().all(axis=1)
    
    # Find duplicate rows
    duplicated_rows = temp_df.duplicated(keep=False)
    
    # Exclude rows with all null values
    duplicated_rows = duplicated_rows & ~all_na_rows
    
    # Get indices of duplicate rows and sort
    duplicate_indices = sorted(duplicated_rows[duplicated_rows].index.tolist())
    
    return duplicate_indices