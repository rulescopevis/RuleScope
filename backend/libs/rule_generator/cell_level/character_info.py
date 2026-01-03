import numpy as np

def character_value(df_column, count_rate_decimal=2):
    result = {
        'valueStatus': False,
        'valueList': None,
    }
    
    try:
        value_counts = {}
        total_rows = len(df_column)
        
        # Loop through the column once to gather both value counts and sequences
        for i in range(len(df_column)):
            current_value = df_column.iloc[i]
            
            # Update value counts
            if current_value not in value_counts:
                value_counts[current_value] = 1
            else:
                value_counts[current_value] += 1

        # Format value counts output
        value_counts_list = []
        for value, count in value_counts.items():
            value_counts_list.append({
                'value': value,
                'count': count,
                'countRate': round(count/total_rows, count_rate_decimal)
            })
        
        # Sort value_counts_list by count in descending order
        value_counts_list = sorted(value_counts_list, key=lambda x: x['count'], reverse=True)
        
        result['valueStatus'] = True
        result['valueList'] = value_counts_list
            
    except Exception as e:
        if not result['valueStatus']:
            result['valueList'] = str(e)
    
    return result

def character_sequence(df_column, sequence_rate_decimal=2, sequence_limit=200):
    result = {
        'sequenceStatus': False,
        'sequenceList': None
    }
    
    try:
        sequence_stats = {}
        unique_sequence_count = 0
        
        # Loop through the column once to gather both value counts and sequences
        for i in range(len(df_column)):
            current_value = df_column.iloc[i]
                
            # Update sequence stats if not last row
            if i < len(df_column) - 1:
                next_value = df_column.iloc[i+1]
                
                # Initialize sequence stats for current value if not exists
                if current_value not in sequence_stats:
                    sequence_stats[current_value] = {}
                
                # Update next value counts for current value and track unique sequences
                if next_value not in sequence_stats[current_value]:
                    sequence_stats[current_value][next_value] = 1
                    unique_sequence_count += 1
                    
                    # Check if we've exceeded the sequence limit
                    if unique_sequence_count > sequence_limit:
                        result['sequenceStatus'] = False
                        result['sequenceList'] = f"Exceeded sequence limit of {sequence_limit}"
                        break
                else:
                    sequence_stats[current_value][next_value] += 1
        
        # Format sequence stats output if we haven't exceeded the limit
        if unique_sequence_count <= sequence_limit:
            sequence_list = []
            for value, next_values in sequence_stats.items():
                total_sequences = sum(next_values.values())
                next_value_list = []
                for next_value, count in next_values.items():
                    next_value_list.append({
                        'value': next_value,
                        'count': count,
                        'sequenceRate': round(count/total_sequences, sequence_rate_decimal)
                    })
                sequence_list.append({
                    'value': value,
                    'nextValueList': next_value_list
                })
            result['sequenceStatus'] = True
            result['sequenceList'] = sequence_list
            
    except Exception as e:
        if not result['sequenceStatus']:
            result['sequenceList'] = str(e)
    
    return result

def character_duplicate(df_column):
    """
    Analyze whether a column contains duplicates for numeric and character data.

    Args:
        df_column: DataFrame column.

    Returns:
        dict: Duplicate detection status and flag.
    """
    result = {
        'duplicateStatus': False,
        'duplicateFlag': None
    }
    
    try:
        if df_column.empty:
            raise ValueError("Input column is empty")
            
        if df_column.isna().all():
            raise ValueError("Input column contains only NA values")
            
        non_na_values = df_column.dropna()
        
        result['duplicateStatus'] = True
        if non_na_values.duplicated().any():
            result['duplicateFlag'] = True
        else:
            result['duplicateFlag'] = False
        
    except Exception as e:
        result['duplicateStatus'] = False
        result['duplicateFlag'] = str(e)
        
        
    return result

def character_missing(df_column, count_rate_decimal=6, special_missing_values=[]):
    """
    Analyze missing values in a column.

    Args:
        df_column: DataFrame column.
        count_rate_decimal: Decimal places for rate calculations.
        special_missing_values: Custom missing-value markers, e.g., ['MISSING', 'N/A', 'Unknown'].

    Returns:
        dict: Missing-value statistics.
    """
    result = {
        'missingStatus': False,
        'missingDict': None
    }
    
    try:
        if len(df_column) == 0:
            raise ValueError("Input column is empty")
            
        missing_mask = df_column.isna()
        
        standard_missing_count = int(missing_mask.sum())
        total_count = len(df_column)
        standard_missing_indexes = [int(i) if isinstance(i, np.integer) else i 
                                  for i in df_column.index[missing_mask].tolist()]
        
        special_missing_list = []
        all_missing_indexes = standard_missing_indexes.copy()
        total_missing_count = standard_missing_count

        for value in special_missing_values:
            try:
                value_mask = (df_column == value)
                value_count = int(value_mask.sum())
                
                if value_count > 0:
                    value_indexes = [int(idx) if isinstance(idx, np.integer) else idx 
                                   for idx in df_column.index[value_mask].tolist()]
                    # Track overall missing statistics
                    all_missing_indexes.extend(value_indexes)
                    total_missing_count += value_count
                    
                    special_missing_list.append({
                        'specialMissingValue': value,
                        'count': value_count,
                        'rate': round(value_count / total_count, count_rate_decimal),
                        'index': value_indexes
                    })
            except (TypeError, ValueError):
                continue
        
        all_missing_indexes = sorted(list(set(all_missing_indexes)))
        
        result_dict = {
            'count': total_missing_count,
            'rate': round(total_missing_count / total_count, count_rate_decimal),
            'index': all_missing_indexes
        }
        
        if special_missing_list:
            result_dict['specialMissingList'] = special_missing_list
        
        result['missingStatus'] = True
        result['missingDict'] = result_dict
        
    except Exception as e:
        result['missingStatus'] = False
        result['missingDict'] = str(e)
    
    return result