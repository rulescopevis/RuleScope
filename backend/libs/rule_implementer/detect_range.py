import pandas as pd
import numpy as np
from datetime import datetime

def _is_numeric_value(value):
    """Return True for real numeric scalars, excluding bool and null."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float, np.integer, np.floating))


def _get_decimal_places(value):
    if not _is_numeric_value(value):
        return 0
    value_str = str(value)
    if '.' in value_str:
        return len(value_str.split('.')[-1])
    return 0

def detect_numeric_range(column, range_rules):
    """
    Detect whether values in a data column are within specified range (vectorized optimized version)
    
    Parameters:
        column (pandas.Series): Data column to be checked
        range_rules (list): List of range rules, each rule is a dictionary
            containing 'start', 'end', 'startInclusive', 'endInclusive' keys
    
    Returns:
        list: Indexes of data not within any allowed range
    """
    
    # Parameter validation
    if not isinstance(range_rules, list):
        raise ValueError("range_rules must be a list")
    
    # If column is empty, return empty list
    if len(column) == 0:
        return []
    
    # Determine floating point precision
    decimal_places = 0
    for rule in range_rules:
        decimal_places = max(
            decimal_places,
            _get_decimal_places(rule.get('start')),
            _get_decimal_places(rule.get('end'))
        )
    
    # Define tolerance for floating point comparison
    epsilon = 1e-10
    
    # Filter out null values
    valid_mask = ~column.isna()
    
    # If all values are null, return empty list
    if not valid_mask.any():
        return []
    
    # Round numeric values
    values_rounded = column.copy()
    numeric_mask = valid_mask & column.apply(_is_numeric_value)
    if numeric_mask.any():
        values_rounded.loc[numeric_mask] = column.loc[numeric_mask].round(decimal_places)
    
    # Initialize mask: all valid values default to not in range
    in_any_range = pd.Series(False, index=column.index)
    
    # Vectorized processing of each range rule
    for rule in range_rules:
        start = rule['start']
        end = rule['end']
        start_inclusive = rule['startInclusive']
        end_inclusive = rule['endInclusive']
        
        # Create mask for current range
        in_current_range = pd.Series(True, index=column.index)
        
        # Vectorized boundary checking
        if not pd.isna(start):
            if start_inclusive:
                in_current_range &= values_rounded >= (start - epsilon)
            else:
                in_current_range &= values_rounded > (start + epsilon)
            
        if not pd.isna(end):
            if end_inclusive:
                in_current_range &= values_rounded <= (end + epsilon)
            else:
                in_current_range &= values_rounded < (end - epsilon)
        
        # Accumulate: mark as True if in any range
        in_any_range |= in_current_range
    
    # Find indexes of valid values not in any range
    outlier_mask = valid_mask & ~in_any_range
    
    return sorted(column.index[outlier_mask].tolist())


def detect_date_range(column, range_rules, main_format, other_format_list):
    """
    Detect whether date values in a data column are within specified range
    
    Parameters:
        column (pandas.Series): Data column to be checked
        range_rules (list): List of range rules, each rule is a dictionary
            containing 'start', 'end', 'startInclusive', 'endInclusive' keys
        main_format (str): Main date format, such as '%Y-%m-%d'
        other_format_list (list): List of other date formats, such as ['%b %d %Y', '%Y/%m/%d']
    
    Returns:
        list: Indexes of data not within any allowed range
    """
    
    # Parameter validation
    if not isinstance(range_rules, list):
        raise ValueError("range_rules must be a list")
    if not isinstance(other_format_list, list):
        raise ValueError("other_format_list must be a list")
    
    def parse_date(date_str):
        """
        Try to parse date string with different formats
        """
        if pd.isna(date_str):
            return None
            
        # If already datetime type, return directly
        if isinstance(date_str, (datetime, pd.Timestamp)):
            return date_str
            
        # Ensure date_str is string type
        if not isinstance(date_str, str):
            return None
            
        # First try main format
        try:
            return pd.to_datetime(date_str, format=main_format)
        except:
            pass
            
        # Then try other formats
        for date_format in other_format_list:
            try:
                return pd.to_datetime(date_str, format=date_format)
            except:
                continue
                
        # Finally try pandas auto parsing
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    
    # Process range boundary dates
    for rule in range_rules:
        raw_start = rule.get('start')
        raw_end = rule.get('end')

        has_start = not pd.isna(raw_start)
        has_end = not pd.isna(raw_end)

        parsed_start = parse_date(raw_start) if has_start else None
        parsed_end = parse_date(raw_end) if has_end else None

        if has_start and parsed_start is None:
            raise ValueError("Invalid date format in range rules (start)")
        if has_end and parsed_end is None:
            raise ValueError("Invalid date format in range rules (end)")
        if not has_start and not has_end:
            raise ValueError("Range rule must provide at least one bound")

        rule['start'] = parsed_start
        rule['end'] = parsed_end
            
    # Define tolerance for date comparison (small time difference)
    epsilon = pd.Timedelta(microseconds=1)
    
    outlier_indices = []
    
    # Iterate through each value and corresponding index in the series
    for idx, value in column.items():
        # Skip null values
        if pd.isna(value):
            continue
            
        # Parse date
        parsed_date = parse_date(value)
        if parsed_date is None:
            continue  # Skip unparseable date formats
            
        # Check if value is within any allowed range
        value_in_range = False
        for rule in range_rules:
            start = rule['start']
            end = rule['end']
            start_inclusive = rule['startInclusive']
            end_inclusive = rule['endInclusive']
            
            # Check if value is within range based on range type
            if start is None:
                in_start = True
            elif start_inclusive:
                in_start = parsed_date >= start
            else:
                in_start = parsed_date > start

            if end is None:
                in_end = True
            elif end_inclusive:
                in_end = parsed_date <= end
            else:
                in_end = parsed_date < end
            
            if in_start and in_end:
                value_in_range = True
                break
                
        # If value is not within any allowed range, add to outlier index list
        if not value_in_range:
            outlier_indices.append(idx)
            
    return sorted(outlier_indices)