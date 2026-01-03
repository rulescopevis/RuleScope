from collections import defaultdict
import pandas as pd
import numpy as np
from dateutil.parser import parse
import re

def analyze_date_column(series, decimal_places=2):
    """
    Analyze a date column and return formatted statistics.
    """
    result = {
        'valueStatus': True,
        'valueList': []
    }
    
    try:
        def get_date_format_pattern():
            """Return date formats and their regex patterns."""
            return [
                # Standard date format YYYY-MM-DD
                ("%Y-%m-%d", r'^([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'),
                
                # Slash separated YYYY/MM/DD
                ("%Y/%m/%d", r'^([12]\d{3})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])$'),
                
                # European format DD-MM-YYYY
                ("%d-%m-%Y", r'^(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-([12]\d{3})$'),
                
                # European format with slash DD/MM/YYYY
                ("%d/%m/%Y", r'^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/([12]\d{3})$'),
                
                # Dot separated DD.MM.YYYY
                ("%d.%m.%Y", r'^(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.([12]\d{3})$'),
                
                # Dot separated YYYY.MM.DD
                ("%Y.%m.%d", r'^([12]\d{3})\.(0[1-9]|1[0-2])\.(0[1-9]|[12]\d|3[01])$'),
                
                # Compact format YYYYMMDD
                ("%Y%m%d", r'^([12]\d{3})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$'),
                
                # Standard format with time
                ("%Y-%m-%d %H:%M:%S", r'^([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\s([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$'),
                ("%Y/%m/%d %H:%M:%S", r'^([12]\d{3})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])\s([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$'),
                
                # ISO 8601 formats
                (None, r'^([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$'),
                (None, r'^([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)Z$'),
                (None, r'^([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)[+-]([01]\d|2[0-3]):([0-5]\d)$'),
                
                # Month abbreviation formats
                ("%d %b %Y", r'^(0[1-9]|[12]\d|3[01])\s(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s([12]\d{3})$'),
                ("%b %d, %Y", r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s(0[1-9]|[12]\d|3[01]),?\s([12]\d{3})$'),
                
                # Month abbreviation with time
                ("%d %b %Y %H:%M:%S", r'^(0[1-9]|[12]\d|3[01])\s(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s([12]\d{3})\s([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$'),
                
                # US format MM/DD/YY
                ("%m/%d/%y", r'^(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(\d{2})$'),
                
                # Time formats
                ("%H:%M:%S", r'^([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$'),
                ("%H:%M", r'^([01]\d|2[0-3]):([0-5]\d)$'),
                
                # Short date formats
                ("%d%b%y", r'^(0[1-9]|[12]\d|3[01])(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})$'),
                ("%b%y", r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})$'),
                ("%d %b", r'^(0[1-9]|[12]\d|3[01])\s(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$')
            ]

        def detect_date_format(date_str):
            """Detect the date string format and return the parsed object and patterns."""
            if pd.isna(date_str):
                return None, None, None, None
            
            date_formats = get_date_format_pattern()
            for fmt, pattern in date_formats:
                if re.match(pattern, str(date_str)):
                    try:
                        if fmt is None:  # ISO format
                            date_obj = parse(str(date_str), fuzzy=False)
                        else:
                            # Parse in strict mode and track the original format
                            date_obj = pd.to_datetime(str(date_str), format=fmt, exact=True)
                        return fmt, pattern, date_obj, fmt
                    except:
                        continue
            return None, None, None, None

        def standardize_date(date_str, target_format, target_pattern):
            """Convert dates to the target format."""
            if pd.isna(date_str):
                return None
            try:
                if target_format is not None:
                    try:
                        date_obj = pd.to_datetime(str(date_str), format=target_format, exact=True)
                        return date_obj.strftime(target_format)
                    except:
                        pass
                
                try:
                    date_obj = parse(str(date_str), fuzzy=False)
                    if target_format is None:
                        return date_obj.strftime("%Y-%m-%d %H:%M:%S")
                    return date_obj.strftime(target_format)
                except:
                    return None
            except:
                return None

        total_count = int(len(series))
        value_counts = defaultdict(lambda: {'value': None, 'count': 0, 'rate': 0})
        different_expressions = defaultdict(lambda: defaultdict(list))
        
        format_counts = defaultdict(int)
        date_objects = {}
        
        for value in series.dropna():
            fmt, pattern, date_obj, original_fmt = detect_date_format(str(value))
            if date_obj is not None:
                format_counts[(fmt, pattern)] += 1
                date_objects[str(value)] = (date_obj, original_fmt)
        
        main_format, main_pattern = max(format_counts.items(), key=lambda x: x[1])[0] if format_counts else (None, None)
        
        null_count = 0
        null_indices = []
        
        for idx, value in series.items():
            if pd.isna(value):
                null_count += 1
                null_indices.append(int(idx))
                continue
            
            value_str = str(value)
            if value_str in date_objects:
                date_obj, original_fmt = date_objects[value_str]
                value_counts[value_str]['value'] = value_str
                value_counts[value_str]['count'] += 1

        if null_count > 0:
            value_counts['null'] = {
                'value': None,
                'count': int(null_count),
                'rate': float(round(null_count / total_count * 100, decimal_places)),
                'index': [int(i) for i in null_indices]
            }

        for std_date, date_dict in value_counts.items():
            if date_dict['value'] is not None:
                date_dict['count'] = int(date_dict['count'])
                date_dict['rate'] = float(round(date_dict['count'] / total_count * 100, decimal_places))
                
                if std_date in different_expressions and different_expressions[std_date]:
                    date_dict['sameEntityList'] = [
                        {
                            'value': expr,
                            'count': int(len(indices)),
                            'rate': float(round(len(indices) / total_count * 100, decimal_places)),
                            'index': [int(i) for i in indices]
                        }
                        for expr, indices in different_expressions[std_date].items()
                    ]

        result.update({
            'mainFormat': main_format,
            'mainPattern': main_pattern,
            'valueList': list(value_counts.values())
        })

    except Exception as e:
        result['valueStatus'] = False
        result['valueList'] = str(e)

    return result

def date_order(series, format_main=None, format_pattern=None):
    """
    Detect ordering of a date series.

    Args:
        series: pandas Series containing date data.
        format_main: Primary date format.
        format_pattern: Regex pattern for the primary format.

    Returns:
        dict with detection status and order classification.
    """
    try:
        non_null_series = series.dropna()
        
        if len(non_null_series) == 0:
            return {
                'orderStatus': False,
                'order': 'No valid dates found in series'
            }
            
        if len(non_null_series) == 1:
            return {
                'orderStatus': False,
                'order': 'Only one date found in series'
            }
        
        dates = []
        for value in non_null_series:
            try:
                dates.append(pd.to_datetime(value))
            except:
                try:
                    std_date = analyze_date_column.standardize_date(str(value), format_main, format_pattern)
                    if std_date:
                        dates.append(pd.to_datetime(std_date))
                except:
                    continue
        
        if not dates:
            return {
                'orderStatus': True,
                'order': 'Disorder'
            }
            
        is_ascending = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
        if is_ascending:
            return {
                'orderStatus': True,
                'order': 'Ascending'
            }
            
        is_descending = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
        if is_descending:
            return {
                'orderStatus': True,
                'order': 'Descending'
            }
        
        return {
            'orderStatus': True,
            'order': 'Disorder'
        }
        
    except Exception as e:
        return {
            'orderStatus': False,
            'order': str(e)
        }

def date_missing(df_column, count_rate_decimal=6, special_missing_values=[]):
    """
    Analyze missing values in a date column.

    Args:
        df_column: DataFrame column.
        count_rate_decimal: Decimal places for rate calculations.
        special_missing_values: Custom missing-value markers, e.g., ['MISSING', 'N/A', 'Unknown'].

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

def date_duplicates(series, format_main=None, format_pattern=None):
    """
    Detect duplicates in a date series.

    Args:
        series: pandas Series containing date data.
        format_main: Primary date format.
        format_pattern: Regex pattern for the primary format.

    Returns:
        dict with detection status and duplicate flag.
    """
    try:
        non_null_series = series.dropna()
        
        if len(non_null_series) == 0:
            return {
                'duplicateStatus': False,
                'duplicateFlag': 'No valid dates found in series'
            }
            
        if len(non_null_series) != len(non_null_series.unique()):
            return {
                'duplicateStatus': True,
                'duplicateFlag': True
            }
        
        standardized_dates = []
        for value in non_null_series:
            try:
                date_obj = pd.to_datetime(value)
                standardized_dates.append(date_obj)
            except:
                try:
                    std_date = analyze_date_column.standardize_date(str(value), format_main, format_pattern)
                    if std_date:
                        date_obj = pd.to_datetime(std_date)
                        standardized_dates.append(date_obj)
                except:
                    continue
        
        if not standardized_dates:
            return {
                'duplicateStatus': False,
                'duplicateFlag': 'Failed to convert any dates'
            }
        
        unique_dates = set()
        for date in standardized_dates:
            date_str = date.strftime('%Y-%m-%d')
            if date_str in unique_dates:
                return {
                    'duplicateStatus': True,
                    'duplicateFlag': True
                }
            unique_dates.add(date_str)
        
        return {
            'duplicateStatus': True,
            'duplicateFlag': False
        }
        
    except Exception as e:
        return {
            'duplicateStatus': False,
            'duplicateFlag': str(e)
        }
    
