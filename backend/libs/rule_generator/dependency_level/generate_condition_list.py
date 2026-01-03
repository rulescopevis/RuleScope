from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime

class ColumnType(Enum):
    CHARACTER = "character"
    BOOL = "bool"
    NUMERIC = "numeric"
    DATETIME = "datetime"

class ConditionType(Enum):
    EQUALITY_BASED = "EqualityBased"
    RANGE_BASED = "RangeBased"

def convert_value(value, target_type):
    """Convert values for numeric or datetime targets."""
    if pd.isna(value):
        return None
        
    if target_type == "numeric":
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace(' ', '')
            numeric_value = pd.to_numeric(value, errors='coerce')
            if pd.isna(numeric_value):
                return None
            if float(numeric_value).is_integer():
                return int(numeric_value)
            return float(numeric_value)
        except:
            return None
            
    elif target_type == "datetime":
        if isinstance(value, datetime):
            return value
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
            
        if isinstance(value, (int, float)):
            str_value = str(int(value))
            if len(str_value) == 8:  # YYYYMMDD
                try:
                    return datetime.strptime(str_value, '%Y%m%d')
                except:
                    pass
            elif len(str_value) == 14:  # YYYYMMDDHHMMSS
                try:
                    return datetime.strptime(str_value, '%Y%m%d%H%M%S')
                except:
                    pass
        
        if not isinstance(value, str):
            return None
            
        common_formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y',
            '%Y.%m.%d', '%d.%m.%Y',
            '%d %b %Y', '%b %d, %Y',
            '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'
        ]
        
        for fmt in common_formats:
            try:
                return datetime.strptime(value, fmt)
            except:
                continue
        
        try:
            dt = pd.to_datetime(value, errors='coerce')
            if pd.notna(dt):
                return dt.to_pydatetime()
        except:
            pass

        return None
    
    return value

def convert_series(series, target_type):
    """Convert a Series to the target type if possible."""
    if target_type == "numeric" and pd.api.types.is_numeric_dtype(series):
        return series
    elif target_type == "datetime" and pd.api.types.is_datetime64_any_dtype(series):
        return series
        
    try:
        if target_type == "numeric":
            if series.dtype == object:
                series = series.str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
            return pd.to_numeric(series, errors='coerce')
        elif target_type == "datetime":
            return pd.to_datetime(series, errors='coerce')
    except Exception as e:
        print(f"Failed to convert series to {target_type}: {str(e)}")
        return series
    
    return series

def calculate_stats_and_outliers(data):
    """Compute basic stats and percentile markers for numeric/datetime data."""
    valid_data = data.dropna()
    
    if len(valid_data) == 0:
        return None
    
    if pd.api.types.is_datetime64_any_dtype(valid_data):
        timestamp_data = valid_data.astype(np.int64) // 10**9
        if len(timestamp_data) == 0: return None
        
        stats = {
            "min": pd.Timestamp.fromtimestamp(timestamp_data.min()),
            "max": pd.Timestamp.fromtimestamp(timestamp_data.max()),
            "median": pd.Timestamp.fromtimestamp(timestamp_data.median()),
            "std": timestamp_data.std(),
            "P1": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.01)),
            "P5": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.05)),
            "P10": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.10)),
            "P90": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.90)),
            "P95": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.95)),
            "P99": pd.Timestamp.fromtimestamp(timestamp_data.quantile(0.99))
        }
        for key, value in stats.items():
            if isinstance(value, pd.Timestamp):
                stats[key] = value.to_pydatetime().isoformat()
            elif not isinstance(value, str):
                stats[key] = float(value)
        return stats

    elif pd.api.types.is_numeric_dtype(valid_data):
        if len(valid_data) == 0: return None
        stats = {
            "min": valid_data.min(),
            "max": valid_data.max(),
            "median": valid_data.median(),
            "std": valid_data.std(),
            "P1": valid_data.quantile(0.01),
            "P5": valid_data.quantile(0.05),
            "P10": valid_data.quantile(0.10),
            "P90": valid_data.quantile(0.90),
            "P95": valid_data.quantile(0.95),
            "P99": valid_data.quantile(0.99)
        }
        for key, value in stats.items():
             if not isinstance(value, str):
                stats[key] = float(value)
        return stats
    
    return None

def find_range_based_segments(series):
    """Identify contiguous range segments for numeric or datetime data."""
    sorted_values = sorted(series.dropna().unique())
    segments = []
    
    if len(sorted_values) <= 1:
        if sorted_values:
            val = sorted_values[0]
            segments.append({
                'start': val, 'end': val, 'startInclusive': True, 'endInclusive': True
            })
        return segments
    
    current_start = sorted_values[0]
    current_value = sorted_values[0]
    
    for next_value in sorted_values[1:]:
        is_datetime = pd.api.types.is_datetime64_any_dtype(series) or isinstance(current_value, datetime)
        
        is_continuous = False
        if is_datetime:
            cv = pd.to_datetime(current_value)
            nv = pd.to_datetime(next_value)
            if (nv - cv) <= pd.Timedelta(days=1):
                is_continuous = True
        else: # numeric
            if abs(next_value - current_value) <= 1:
                 is_continuous = True

        if not is_continuous:
            segments.append({
                'start': current_start,
                'end': current_value,
                'startInclusive': True,
                'endInclusive': True
            })
            current_start = next_value
        current_value = next_value
    
    segments.append({
        'start': current_start,
        'end': current_value,
        'startInclusive': True,
        'endInclusive': True
    })
    
    return segments

def generate_condition_list(conditionColumn, constraintColumn, typeDict, maxListLength=50):
    """Generate condition list for a single condition and constraint column."""
    condition_type = typeDict.get(conditionColumn.name)
    constraint_type = typeDict.get(constraintColumn.name)
    
    if condition_type == "numeric":
        conditionColumn = convert_series(conditionColumn, "numeric")
    elif condition_type == "datetime":
        conditionColumn = convert_series(conditionColumn, "datetime")
        
    if constraint_type == "numeric":
        constraintColumn = convert_series(constraintColumn, "numeric")
    elif constraint_type == "datetime":
        constraintColumn = convert_series(constraintColumn, "datetime")

    result = []
    
    condition_col_type = typeDict.get(conditionColumn.name)
    constraint_col_type = typeDict.get(constraintColumn.name)
    
    is_condition_range_based = condition_col_type in ["numeric", "datetime"]
    is_constraint_range_based = constraint_col_type in ["numeric", "datetime"]
    
    df = pd.DataFrame({
        'condition': conditionColumn,
        'constraint': constraintColumn
    })
    
    def custom_sort_key(x):
        if pd.isna(x):
            return (0, '')
        if isinstance(x, (int, float, datetime, pd.Timestamp)):
            return (1, x)
        return (2, str(x))
    
    if is_condition_range_based:
        df_valid = df.dropna(subset=['condition'])
        segments = find_range_based_segments(df_valid['condition'])
        
        for segment in segments:
            mask = (df_valid['condition'] >= segment['start'])
            if not segment['endInclusive']:
                mask &= (df_valid['condition'] < segment['end'])
            else:
                mask &= (df_valid['condition'] <= segment['end'])
            
            segment_data = df_valid[mask]
            
            if is_constraint_range_based:
                continue
            else:
                constraint_values = list(segment_data['constraint'].unique())
                constraint_values.sort(key=custom_sort_key)
                
                condition_stats = calculate_stats_and_outliers(segment_data['condition'])
                
                result.append({
                    "conditionValue": segment,
                    "conditionType": ConditionType.RANGE_BASED.value,
                    "constraintValue": [None if pd.isna(v) else v for v in constraint_values],
                    "constraintType": ConditionType.EQUALITY_BASED.value,
                    "conditionStaticInfo": condition_stats
                })
    else:
        condition_values = list(df['condition'].unique())
        condition_values.sort(key=custom_sort_key)
        
        for condition_value in condition_values:
            if pd.isna(condition_value):
                segment_data = df[df['condition'].isna()]
            else:
                segment_data = df[df['condition'] == condition_value]
            
            final_condition_value = None if pd.isna(condition_value) else condition_value

            if is_constraint_range_based:
                constraint_data = segment_data['constraint'].dropna()
                if len(constraint_data) > 0:
                    constraint_stats = calculate_stats_and_outliers(constraint_data)
                    
                    result.append({
                        "conditionValue": [final_condition_value],
                        "conditionType": ConditionType.EQUALITY_BASED.value,
                        "constraintValue": {
                            'start': constraint_data.min(),
                            'end': constraint_data.max(),
                            'startInclusive': True,
                            'endInclusive': True
                        },
                        "constraintType": ConditionType.RANGE_BASED.value,
                        "constraintStaticInfo": constraint_stats
                    })
            else:
                constraint_values = list(segment_data['constraint'].unique())
                constraint_values.sort(key=custom_sort_key)
                
                result.append({
                    "conditionValue": [final_condition_value],
                    "conditionType": ConditionType.EQUALITY_BASED.value,
                    "constraintValue": [None if pd.isna(v) else v for v in constraint_values],
                    "constraintType": ConditionType.EQUALITY_BASED.value
                })

    if len(result) > maxListLength:
        return []
    else:
        finalResult = {
            "conditionColumns": [conditionColumn.name],
            "constraintColumns": [constraintColumn.name],
            "columnType": {
                conditionColumn.name: map_column_type_to_condition_type(typeDict[conditionColumn.name]),
                constraintColumn.name: map_column_type_to_condition_type(typeDict[constraintColumn.name])
            },
            "conditionAndLogicList": [{
                "conditionColumnValue": [{
                    conditionColumn.name: item["conditionValue"],
                    **({"staticInfo": item["conditionStaticInfo"]} if "conditionStaticInfo" in item and typeDict[conditionColumn.name] in ["numeric", "datetime"] else {})
                }],
                "constraintColumnValue": {
                    constraintColumn.name: item["constraintValue"],
                    **({"staticInfo": item["constraintStaticInfo"]} if "constraintStaticInfo" in item and typeDict[constraintColumn.name] in ["numeric", "datetime"] else {})
                }
            } for item in result]
        }
        return finalResult

def map_column_type_to_condition_type(column_type):
    """Map column type to condition type label."""
    if column_type in ['character', 'bool']:
        return ConditionType.EQUALITY_BASED.value
    elif column_type in ['numeric', 'datetime']:
        return ConditionType.RANGE_BASED.value
    return ConditionType.EQUALITY_BASED.value

def generate_multiple_condition_list(df, type_info, maxListLength=100):
    """Generate multi-column condition rules from a DataFrame."""
    condition_columns = type_info.get('conditionColumnList', [])
    constraint_columns = type_info.get('constraintColumnList', [])
    column_types = type_info.get('columnType', {})

    numeric_datetime_cond_count = sum(
        1 for col in condition_columns
        if column_types.get(col) in ['numeric', 'datetime']
    )
    if numeric_datetime_cond_count >= 2:
        return []

    df_processed = df.copy()
    for col, col_type in column_types.items():
        if col in df_processed.columns and col_type in ['numeric', 'datetime']:
            df_processed[col] = convert_series(df_processed[col], col_type)

    eq_constraint_cols = [
        col for col in constraint_columns if column_types.get(col) in ('character', 'bool')
    ]
    range_constraint_cols = [
        col for col in constraint_columns if column_types.get(col) in ('numeric', 'datetime')
    ]

    grouping_keys = condition_columns + eq_constraint_cols
    if not grouping_keys:
        return []

    grouped = df_processed.groupby(grouping_keys, dropna=False)

    condition_and_logic_list = []
    for group_key, group_df in grouped:
        if group_df.empty:
            continue

        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        group_key_dict = dict(zip(grouping_keys, group_key))

        condition_column_value = []
        for col in condition_columns:
            val = group_key_dict[col]
            condition_val = None if pd.isna(val) else val
            
            item = {col: [condition_val]}
            if column_types.get(col) in ['numeric', 'datetime']:
                item["staticInfo"] = calculate_stats_and_outliers(group_df[col])
            condition_column_value.append(item)

        constraint_column_value = {}
        for col in eq_constraint_cols:
            val = group_key_dict[col]
            constraint_column_value[col] = [None if pd.isna(val) else val]

        for col in range_constraint_cols:
            valid_data = group_df[col].dropna()
            if not valid_data.empty:
                min_val = valid_data.min()
                max_val = valid_data.max()
                
                start_val = min_val.to_pydatetime() if isinstance(min_val, pd.Timestamp) else min_val
                end_val = max_val.to_pydatetime() if isinstance(max_val, pd.Timestamp) else max_val

                constraint_column_value[col] = {
                    'value': {
                        'start': start_val,
                        'end': end_val,
                        'startInclusive': True,
                        'endInclusive': True
                    },
                    'staticInfo': calculate_stats_and_outliers(valid_data)
                }
        
        if constraint_column_value:
            condition_and_logic_list.append({
                "conditionColumnValue": condition_column_value,
                "constraintColumnValue": constraint_column_value
            })
    
    if len(condition_and_logic_list) > maxListLength:
        return []

    final_result = {
        "conditionColumns": condition_columns,
        "constraintColumns": constraint_columns,
        "columnType": {
            col: map_column_type_to_condition_type(col_type)
            for col, col_type in column_types.items()
        },
        "conditionAndLogicList": condition_and_logic_list
    }
    
    return final_result