import json
import pandas as pd
import numpy as np
from scipy import stats, signal
import os
import sys
from sklearn.cluster import DBSCAN

# Attempt optional GPU acceleration; fall back to CPU if unavailable.
try:
    import cuml
    import cupy as cp
    GPU_AVAILABLE = True
    print("cuML and cuPy detected. GPU acceleration enabled.")
except ImportError:
    GPU_AVAILABLE = False
    print("cuML or cuPy not found. Using CPU-based scikit-learn.")

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from rule_generator.cell_level.type import detect_column_types

def numeric_decimal_value(df_column, count_rate_decimal=2):
    """
    Analyze decimal precision and value distribution for a numeric column.

    Args:
        df_column: Numeric pandas Series.
        count_rate_decimal: Decimal places for rate calculations.

    Returns:
        dict with status and analysis results.
    """
    result = {
        'decimalStatus': False,
        'decimalList': None,
        'valueStatus': False, 
        'valueList': None,
    }
    try:
        if df_column.empty:
            raise ValueError("Input column is empty")
        
        column_types = detect_column_types(pd.DataFrame(df_column))
        columnNameList = column_types['columnTypes'].keys()
        columnName = list(columnNameList)[0]
        column_type = column_types['columnTypes'][columnName]['type']
        if column_type != 'numeric':
            raise ValueError("Input column must be numeric type")
        else:
            df_column = pd.to_numeric(df_column, errors='coerce')
            
        total_rows = len(df_column)
        
        try:
            decimal_counts = {}
            
            for value in df_column.dropna():
                value = float(value) if pd.api.types.is_float_dtype(type(value)) else int(value)
                str_value = str(value)
                
                if 'e' in str_value.lower():
                    str_value = f"{float(str_value):.10f}".rstrip('0').rstrip('.')
                
                decimal_places = len(str_value.split('.')[1]) if '.' in str_value else 0
                decimal_counts[decimal_places] = decimal_counts.get(decimal_places, 0) + 1
            
            decimal_list = [
                {
                    'decimal': int(decimal),
                    'count': int(count),
                    'rate': float(round(count/total_rows, count_rate_decimal))
                }
                for decimal, count in decimal_counts.items()
            ]
            
            result['decimalStatus'] = True
            result['decimalList'] = sorted(decimal_list, key=lambda x: x['count'], reverse=True)
            
        except Exception as e:
            result['decimalStatus'] = False
            result['decimalList'] = str(e)
            
        try:
            value_counts = df_column.value_counts(dropna=False)
            value_list = [
                {
                    'value': None if pd.isna(value) else float(value) if isinstance(value, (float, np.floating)) else int(value),
                    'count': int(count),
                    'rate': round(count/total_rows, count_rate_decimal)
                }
                for value, count in value_counts.items()
            ]
            
            result['valueStatus'] = True
            result['valueList'] = value_list
            
        except Exception as e:
            result['valueStatus'] = False
            result['valueList'] = str(e)
            
    except Exception as e:
        result = {
            'decimalStatus': False,
            'decimalList': str(e),
            'valueStatus': False,
            'valueList': str(e)
        }
    
    return result

def numeric_difference(df_column, difference_decimal=4, relative_difference_decimal=4):
    """
    Analyze absolute and relative differences for consecutive numeric values.

    Args:
        df_column: Numeric pandas Series.
        difference_decimal: Decimal places for differences.
        relative_difference_decimal: Decimal places for relative differences.

    Returns:
        dict with status and analysis results.
    """
    result = {
        'differenceStatus': False,
        'differenceList': None,
        'relativeDifferenceStatus': False,
        'relativeDifferenceList': None
    }
    try:
        if df_column.empty:
            raise ValueError("Input column is empty")
        
        column_types = detect_column_types(pd.DataFrame(df_column))
        columnNameList = column_types['columnTypes'].keys()
        columnName = list(columnNameList)[0]
        column_type = column_types['columnTypes'][columnName]['type']
        if column_type != 'numeric':
            raise ValueError("Input column must be numeric type")
        else:
            df_column = pd.to_numeric(df_column, errors='coerce')
            
        try:
            differences = []
            relative_differences = []
            series_values = df_column.values
            
            for i in range(len(series_values)-1):
                current_val = series_values[i]
                next_val = series_values[i+1]
                
                if pd.isna(current_val) or pd.isna(next_val):
                    difference = None
                    relative_difference = None
                else:
                    # 转换为Python原生类型
                    current_val = float(current_val)
                    next_val = float(next_val)
                    difference = float(round(abs(next_val - current_val), difference_decimal))
                    if current_val != 0:
                        relative_difference = float(round(difference / abs(current_val), relative_difference_decimal))
                    else:
                        relative_difference = None
                        
                differences.append(difference)
                relative_differences.append(relative_difference)
            
            result['differenceStatus'] = True
            result['differenceList'] = differences
            
            result['relativeDifferenceStatus'] = True
            result['relativeDifferenceList'] = relative_differences
            
        except Exception as e:
            result['differenceStatus'] = False
            result['differenceList'] = str(e)
            result['relativeDifferenceStatus'] = False
            result['relativeDifferenceList'] = str(e)
            
    except Exception as e:
        result = {
            'differenceStatus': False,
            'differenceList': str(e),
            'relativeDifferenceStatus': False,
            'relativeDifferenceList': str(e)
        }
    
    return result

def numeric_static(df_column):
    """
    Analyze numeric statistics, distribution type, and outlier bounds; supports optional GPU acceleration.

    Args:
        df_column (pd.Series or np.ndarray): Numeric column.

    Returns:
        dict with status, stats, distribution classification, and outlier info.
    """
    result = {
        'staticStatus': False,
        'staticDict': {},
        'outlierFunctionStatus': False,
        'outlierFunction': None,
        'outlierParameters': None,
        'outlierRange': None,
        'distributionStatus': False,
        'distribution': None
    }
    
    try:
        if not isinstance(df_column, (pd.Series, np.ndarray)):
            raise TypeError("Input must be a pandas Series or numpy array")
            
        if isinstance(df_column, pd.Series):
            data = df_column.values
        else:
            data = df_column
            
        data = data[np.isfinite(data)]
        
        if len(data) < 30:
            result['staticDict'] = "Not enough data"
            result['outlierFunction'] = "not enough data"
            result['distribution'] = "not enough data"
            return result
            
        result['staticDict']['min'] = float(np.min(data))
        result['staticDict']['max'] = float(np.max(data))
        result['staticDict']['median'] = float(np.median(data))
        result['staticDict']['mean'] = float(np.mean(data))
        result['staticDict']['std'] = float(np.std(data))
        result['staticDict']['skewness'] = float(stats.skew(data))
        result['staticDict']['kurtosis'] = float(stats.kurtosis(data))
        
        percentiles = np.percentile(data, [1, 5, 10, 25, 75, 90, 95, 99])
        result['staticDict']['p1'] = float(percentiles[0])
        result['staticDict']['p5'] = float(percentiles[1])
        result['staticDict']['p10'] = float(percentiles[2])
        result['staticDict']['q1'] = float(percentiles[3])
        result['staticDict']['q3'] = float(percentiles[4])
        result['staticDict']['p90'] = float(percentiles[5])
        result['staticDict']['p95'] = float(percentiles[6])
        result['staticDict']['p99'] = float(percentiles[7])
        
        result['staticDict']['mad'] = float(stats.median_abs_deviation(data, scale='normal'))
        result['staticDict']['iqr'] = float(result['staticDict']['q3'] - result['staticDict']['q1'])
        
        def is_normal():
            mean = result['staticDict']['mean']
            median = result['staticDict']['median']
            std = result['staticDict']['std']
            if std == 0: return True
            rules = [
                abs(result['staticDict']['skewness']) < 0.5,
                abs(result['staticDict']['kurtosis']) < 0.5,
                abs(mean - median) < 0.2 * std
            ]
            return sum(rules) >= 3
            
        def is_skewed():
            return abs(result['staticDict']['skewness']) > 1.0
            
        def is_multimodal(sample_data):
            try:
                if np.std(sample_data) < 1e-9: return False
                kde = stats.gaussian_kde(sample_data)
                x = np.linspace(sample_data.min(), sample_data.max(), 200)
                y = kde(x)
                peaks = signal.find_peaks(y)[0]
                return len(peaks) > 1
            except Exception:
                return False

        EXPENSIVE_CHECK_THRESHOLD = 100000 
        KDE_SAMPLE_SIZE = 5000
        use_expensive_checks = len(data) < EXPENSIVE_CHECK_THRESHOLD

        result['distributionStatus'] = True
        
        if is_normal():
            result['distribution'] = "normal"
            result['outlierFunction'] = "zscore"
            result['outlierParameters'] = {'threshold': 3}
            mean, std = result['staticDict']['mean'], result['staticDict']['std']
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std
            result['outlierRange'] = {'start': float(lower_bound), 'end': float(upper_bound), 'startInclusive': True, 'endInclusive': True}

        elif is_skewed():
            result['distribution'] = "skewed"
            result['outlierFunction'] = "modified_zscore"
            result['outlierParameters'] = {'threshold': 3.5}
            median, mad = result['staticDict']['median'], result['staticDict']['mad']
            if mad == 0:
                q1, q3, iqr = result['staticDict']['q1'], result['staticDict']['q3'], result['staticDict']['iqr']
                lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            else:
                lower_bound = median - 3.5 * mad / 0.6745
                upper_bound = median + 3.5 * mad / 0.6745
            result['outlierRange'] = {'start': float(lower_bound), 'end': float(upper_bound), 'startInclusive': True, 'endInclusive': True}
            
        elif use_expensive_checks and is_multimodal(np.random.choice(data, size=min(len(data), KDE_SAMPLE_SIZE), replace=False)):
            result['distribution'] = "multimodal"
            result['outlierFunction'] = "dbscan"
            
            data_reshaped = data.reshape(-1, 1)
            std_dev = np.std(data_reshaped)

            if std_dev > 1e-9:
                eps_val = 0.5 
                min_samples_val = 2
                result['outlierParameters'] = {'eps': eps_val, 'min_samples': min_samples_val}
                
                normalized_data = data_reshaped / std_dev
                
                if GPU_AVAILABLE:
                    db = cuml.DBSCAN(eps=eps_val, min_samples=min_samples_val)
                    gpu_data = cp.asarray(normalized_data)
                    clusters = db.fit_predict(gpu_data).get()
                else:
                    db = DBSCAN(eps=eps_val, min_samples=min_samples_val)
                    clusters = db.fit_predict(normalized_data)
                
                non_outlier_values = data[clusters != -1]
                
                if len(non_outlier_values) > 0:
                    result['outlierRange'] = {'start': float(np.min(non_outlier_values)), 'end': float(np.max(non_outlier_values)), 'startInclusive': True, 'endInclusive': True}
                else:
                    result['outlierFunction'] = "iqr"
                    q1, q3, iqr = result['staticDict']['q1'], result['staticDict']['q3'], result['staticDict']['iqr']
                    result['outlierRange'] = {'start': float(q1 - 1.5 * iqr), 'end': float(q3 + 1.5 * iqr), 'startInclusive': True, 'endInclusive': True}
            else:
                result['outlierRange'] = {'start': float(data[0]), 'end': float(data[0]), 'startInclusive': True, 'endInclusive': True}

        else:
            result['distribution'] = "unknown"
            result['outlierFunction'] = "iqr"
            result['outlierParameters'] = {'factor': 1.5}
            q1, q3, iqr = result['staticDict']['q1'], result['staticDict']['q3'], result['staticDict']['iqr']
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            result['outlierRange'] = {'start': float(lower_bound), 'end': float(upper_bound), 'startInclusive': True, 'endInclusive': True}

        result['outlierFunctionStatus'] = True
        result['staticStatus'] = True
        
    except Exception as e:
        error_message = f"Execution error: {type(e).__name__} - {e}"
        result['staticStatus'] = False
        result['staticDict'] = error_message
        result['distributionStatus'] = False
        print(error_message)
        
    return result

def numeric_order_duplicate(df_column):
    """
    Analyze ordering and duplicates for a numeric column.

    Args:
        df_column: Numeric pandas Series.

    Returns:
        dict with duplicate and order analysis.
    """
    result = {
        'duplicateStatus': False,
        'duplicateFlag': None,
        'orderStatus': False,
        'orderType': None
    }
    
    try:
        column_types = detect_column_types(pd.DataFrame(df_column))
        columnNameList = column_types['columnTypes'].keys()
        columnName = list(columnNameList)[0]
        column_type = column_types['columnTypes'][columnName]['type']
        if column_type != 'numeric':
            raise ValueError("Input column must be numeric type")
        else:
            df_column = pd.to_numeric(df_column, errors='coerce')
            
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
        
    try:
        column_types = detect_column_types(pd.DataFrame(df_column))
        columnNameList = column_types['columnTypes'].keys()
        columnName = list(columnNameList)[0]
        column_type = column_types['columnTypes'][columnName]['type']

        if column_type != 'numeric':
            raise ValueError("Input column must be numeric type")
        else:
            df_column = pd.to_numeric(df_column, errors='coerce')
            
        if df_column.empty:
            raise ValueError("Input column is empty")
            
        if df_column.isna().all():
            raise ValueError("Input column contains only NA values")
            
        non_na_values = df_column.dropna()
        
        is_ascending = True
        is_descending = True
        prev_value = None
        
        for value in non_na_values:
            if prev_value is not None:
                if value < prev_value:
                    is_ascending = False
                if value > prev_value:
                    is_descending = False
                if not is_ascending and not is_descending:
                    break
            prev_value = value
        
        result['orderStatus'] = True
        if is_ascending and not is_descending:
            result['orderType'] = 'Ascending'
        elif is_descending and not is_ascending:
            result['orderType'] = 'Descending'
        else:
            result['orderType'] = 'Disorder'
            
    except Exception as e:
        result['orderStatus'] = False
        result['orderType'] = str(e)
        
    return result

def numeric_missing(df_column, count_rate_decimal=6, numeric_missing_values=[]):
    """
    Analyze missing values in a numeric column.

    Args:
        df_column: Numeric pandas Series.
        count_rate_decimal: Decimal places for rates.
        numeric_missing_values: Numeric placeholders representing missing values, e.g., [-999, -1, 0].

    Returns:
        dict with missing-value statistics.
    """
    result = {
        'missingStatus': False,
        'missingDict': None
    }
    try:
        if len(df_column) == 0:
            raise ValueError("Input column is empty")
            
        column_types = detect_column_types(pd.DataFrame(df_column))
        columnNameList = column_types['columnTypes'].keys()
        columnName = list(columnNameList)[0]
        column_type = column_types['columnTypes'][columnName]['type']

        if column_type != 'numeric':
            raise ValueError("Input column must be numeric type")
            
        missing_mask = df_column.isna()
        
        standard_missing_count = int(missing_mask.sum())
        total_count = len(df_column)
        standard_missing_indexes = [int(i) if isinstance(i, np.integer) else i 
                                  for i in df_column.index[missing_mask].tolist()]
        
        special_missing_list = []
        all_missing_indexes = standard_missing_indexes.copy()
        total_missing_count = standard_missing_count

        for value in numeric_missing_values:
            if value == 'nan':
                continue
                
            try:
                if pd.api.types.is_float_dtype(df_column):
                    if isinstance(value, str) and value.lower() == 'nan':
                        value = float('nan')
                    value_mask = np.isclose(df_column, value, rtol=1e-05, atol=1e-08)
                else:
                    value_mask = (df_column == value)
                
                value_count = int(value_mask.sum())
                
                if value_count > 0:
                    if isinstance(value, np.floating) or isinstance(value, float):
                        python_value = float(value)
                    elif isinstance(value, np.integer) or isinstance(value, int):
                        python_value = int(value)
                    elif value is None:
                        python_value = None
                    else:
                        continue  # Skip values that cannot be safely converted
                        
                    value_indexes = [int(idx) if isinstance(idx, np.integer) else idx 
                                   for idx in df_column.index[value_mask].tolist()]
                    all_missing_indexes.extend(value_indexes)
                    total_missing_count += value_count
                    
                    special_missing_list.append({
                        'numericMissingValue': python_value,
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
            'index': list(all_missing_indexes)
        }
        
        if special_missing_list:
            result_dict['numericMissingList'] = special_missing_list
        
        result['missingStatus'] = True
        result['missingDict'] = result_dict
        
    except Exception as e:
        result['missingStatus'] = False
        result['missingDict'] = str(e)
    
    return result