import pandas as pd
import numpy as np
from dateutil.parser import parse, ParserError
import re
import os
import sys

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

def is_date(string):
    try:
        parse(string)
        return True
    except (ValueError, TypeError, ParserError):
        return False

def is_potential_datetime(value):
    if isinstance(value, (int, float)):
        str_value = str(int(value))
        # Only match 8-digit (YYYYMMDD) or 14-digit (YYYYMMDDHHMMSS) numbers
        return (len(str_value) == 8 and 1900 <= int(str_value[:4]) <= 2100) or \
               (len(str_value) == 14 and 1900 <= int(str_value[:4]) <= 2100)
    elif isinstance(value, str):
        # Handle 6-digit numeric dates (YYYYMM format)
        if value.isdigit() and len(value) == 6:
            year = int(value[:4])
            month = int(value[4:])
            return 1900 <= year <= 2100 and 1 <= month <= 12
        # Common date and time patterns
        datetime_patterns = [
            r'\d{4}-\d{2}-\d{2}',                    # YYYY-MM-DD
            r'\d{4}/\d{1,2}/\d{1,2}',                    # YYYY/MM/DD
            r'\d{2}-\d{2}-\d{4}',                    # DD-MM-YYYY
            r'\d{2}/\d{2}/\d{4}',                    # DD/MM/YYYY
            r'\d{2}\.\d{2}\.\d{4}',                  # DD.MM.YYYY
            r'\d{4}\.\d{2}\.\d{2}',                  # YYYY.MM.DD
            r'\d{8}',                                # YYYYMMDD
            r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}',        # 1 Jan 2023, 01 Jan 2023
            r'[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}',      # Jan 1, 2023, Jan 01 2023
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',    # YYYY-MM-DD HH:MM:SS
            r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}',    # YYYY/MM/DD HH:MM:SS
            r'\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}',    # DD-MM-YYYY HH:MM:SS
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',    # DD/MM/YYYY HH:MM:SS
            r'\d{14}',                               # YYYYMMDDHHMMSS
            r'\d{2}:\d{2}:\d{2}',                    # HH:MM:SS
            r'\d{2}:\d{2}',                          # HH:MM
            r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}',  # 1 Jan 2023 12:34:56
            r'[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}\s+\d{2}:\d{2}:\d{2}',  # Jan 1, 2023 12:34:56
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO 8601: YYYY-MM-DDTHH:MM:SS
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', # ISO 8601 with Z
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}',  # ISO 8601 with timezone
            r'\d{2}[A-Za-z]{3}\d{4}:\d{2}:\d{2}:\d{2}',  # 01JAN2023:12:34:56
            r'\d{1,2}/\d{1,2}/\d{2}',                # M/D/YY or MM/DD/YY
            r'\d{1,2}-\d{1,2}-\d{2}',                # M-D-YY or MM-DD-YY
            r'\d{2}[A-Za-z]{3}\d{2}',                # DDMMMYY
            r'[A-Za-z]{3}\d{2}',                     # MMMYY
            r'\d{1,2}\s+[A-Za-z]{3}',                # 1 Jan, 01 Jan
            r'[A-Za-z]{3}\s+\d{1,2}',                # Jan 1, Jan 01
        ]
        # Extra validation for purely numeric strings
        if value.isdigit():
            if len(value) == 8:
                year = int(value[:4])
                month = int(value[4:6])
                day = int(value[6:8])
                return (1900 <= year <= 2100) and (1 <= month <= 12) and (1 <= day <= 31)
            elif len(value) == 14:
                year = int(value[:4])
                month = int(value[4:6])
                day = int(value[6:8])
                hour = int(value[8:10])
                minute = int(value[10:12])
                second = int(value[12:14])
                return (1900 <= year <= 2100) and (1 <= month <= 12) and (1 <= day <= 31) and \
                       (0 <= hour <= 23) and (0 <= minute <= 59) and (0 <= second <= 59)
            
        return any(re.match(pattern, value) for pattern in datetime_patterns)
    return False

def detect_column_types(df):
    columnTypeDict = {}
    for column in df.columns:
        columnTypeDict[column] = {}
        sample = df[column]
        sample = sample.replace('', np.nan).dropna()
        if len(sample) > 100:
            sample = sample.sample(100)
        
        if sample.empty:
            columnTypeDict[column]['type'] = 'unknown'
            continue
            
        # Check for boolean types first
        if sample.dtype == 'bool' or (
            sample.apply(lambda x: isinstance(x, bool)).all()):
            columnTypeDict[column]['type'] = 'bool'
            continue
        
        # Check for datetime-like types
        sample_clean = sample.replace('', np.nan).dropna()
        
        # Verify all non-null values are strings
        if sample_clean.apply(lambda x: isinstance(x, str)).all():
            # If all non-null values match datetime patterns, classify as datetime
            if sample_clean.apply(is_potential_datetime).all():
                columnTypeDict[column]['type'] = 'datetime'
                continue
            # If original data (including empty strings) is all strings, classify as character
            if sample.apply(lambda x: isinstance(x, str)).all():
                columnTypeDict[column]['type'] = 'character'
                continue
        
        # Check whether any non-empty value is a string
        has_string = any(isinstance(x, str) for x in sample if x != '' and x is not None and not pd.isna(x))
        
        if has_string:
            columnTypeDict[column]['type'] = 'character'
        else:
            # Only check numeric when no strings are present
            try:
                valid_values = [x for x in sample if x != '' and x is not None and not pd.isna(x)]
                _ = [float(x) for x in valid_values]
                columnTypeDict[column]['type'] = 'numeric'
            except (ValueError, TypeError):
                columnTypeDict[column]['type'] = 'character'
    
    return {'result': True, 'columnTypes': columnTypeDict}
