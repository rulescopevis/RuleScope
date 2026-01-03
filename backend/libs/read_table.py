import pandas as pd

def read_table(file_path, char_columns=None, numeric_columns=None, datetime_columns=None, 
               datetime_format=None, auto_detect=0.001):
    """
    Custom function to read CSV and Excel files with type conversion
    file_path: Path to the CSV/Excel file
    char_columns: List of column names to be converted to character type
    numeric_columns: List of column names to be converted to numeric type
    datetime_columns: List of column names to be converted to datetime type
    datetime_format: Format string for datetime parsing (e.g., '%Y-%m-%d')
    auto_detect: Threshold ratio for detecting low-cardinality columns (default=0.001)
    """
    # Determine file type from extension
    file_extension = file_path.lower().split('.')[-1]
    
    # Read data based on file type
    if file_extension == 'csv':
        df = pd.read_csv(file_path)
    elif file_extension in ['xlsx', 'xls']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file extension: .{file_extension}. Only .csv, .xlsx, and .xls are supported.")
    
    # Automatically detect columns that need conversion
    if auto_detect is not None and auto_detect is not False:
        detected_chars = []
        for col in df.columns:
            # Check if it's a numeric column
            if pd.api.types.is_numeric_dtype(df[col]):
                # Calculate unique value ratio
                unique_ratio = len(df[col].unique()) / len(df)
                # If unique value ratio is less than or equal to threshold, add it to character columns
                if unique_ratio <= auto_detect:
                    detected_chars.append(col)
        
        # Merge manually specified and automatically detected character columns
        if char_columns:
            char_columns = list(set(char_columns + detected_chars))
        else:
            char_columns = detected_chars
    
    # Remove any numeric columns from char_columns if they exist in both
    if numeric_columns and char_columns:
        char_columns = [col for col in char_columns if col not in numeric_columns]
    
    # Convert specified numeric columns
    if numeric_columns:
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert specified datetime columns
    if datetime_columns:
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format=datetime_format, errors='coerce')
    
    # Convert character columns (keeping existing functionality)
    if char_columns:
        for col in char_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else "")
    
    return df