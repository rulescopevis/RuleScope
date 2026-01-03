import pandas as pd

def detect_conflict_flag(invalid_index, csv_file_path):
    """
    Return a conflict flag value based on the ratio of invalid_index array and CSV file data rows
    
    Parameters:
        invalid_index: Array of invalid indices
        csv_file_path: Path to CSV file
    
    Return values:
        0: invalid_index array is empty
        1: Number of invalid_index < 1% of CSV file data rows
        2: 1% <= Number of invalid_index < 10% of CSV file data rows
        3: Number of invalid_index >= 10% of CSV file data rows
    """
    # If invalid_index array is empty, return 0
    if not invalid_index or len(invalid_index) == 0:
        return 0

    # Read CSV file and get number of data rows
    try:
        df = pd.read_csv(csv_file_path)
        total_rows = len(df)
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

    # If CSV file is empty, avoid division by zero error
    if total_rows == 0:
        return 4  # If CSV is empty but invalid_index is not empty, return highest conflict level

    # Calculate ratio
    invalid_ratio = len(invalid_index) / total_rows

    # Return corresponding flag value based on ratio
    if invalid_ratio < 0.001:  # Less than 1%
        return 1
    elif invalid_ratio < 0.01:  # Greater than or equal to 1% but less than 10%
        return 2
    elif invalid_ratio < 0.1:  # Greater than or equal to 10% but less than 20%
        return 3
    else:  # Greater than or equal to 20%
        return 4
