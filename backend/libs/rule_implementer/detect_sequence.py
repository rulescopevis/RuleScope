import pandas as pd
import numpy as np

def is_empty_sequence_value(value) -> bool:
    """Return True when the provided value should break sequence detection."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return pd.isna(value)

def detect_sequence(df, columnName, orderCondition, sequenceRule, tableDict):
    """
    Detect whether the sequence in a data column conforms to the rules
    
    Parameters:
        df (pandas.DataFrame): Data frame to be checked
        columnName (str): Column name to be checked
        orderCondition (dict): Sort condition
        sequenceRule (list): List of sequence rules, each rule is a dictionary
            containing 'value' and 'allowed_next' keys
        tableDict (dict): Table dictionary containing column format information
    
    Returns:
        list: List of index pairs that do not conform to sequence rules, each element is a dictionary containing currentIndex and nextIndex
    """
    try:
    # Parameter validation
        if not isinstance(sequenceRule, list):
            raise ValueError("sequenceRule must be a list")
        
        if len(df) < 2:
            return []
        
        # Create data copy to avoid modifying original data
        df_copy = df.copy()
        
        # Convert numeric types to strings
        if pd.api.types.is_numeric_dtype(df_copy[columnName]):
            df_copy[columnName] = df_copy[columnName].astype(str)
        
        # Build sort conditions
        sort_columns = []
        sort_ascending = []
        
        for i in range(1, 4):
            column_key = f"firstOrderColumn" if i == 1 else f"secondOrderColumn" if i == 2 else "thirdOrderColumn"
            type_key = f"firstOrderType" if i == 1 else f"secondOrderType" if i == 2 else "thirdOrderType"
            
            if column_key in orderCondition:
                sort_columns.append(orderCondition[column_key])
                sort_ascending.append(orderCondition[type_key].lower() == "asc")
        
        if orderCondition.get('dateColumns', []) != []:
            for col in orderCondition['dateColumns']:
                try:
                    date_format = tableDict[col]['mainFormat']
                    df_copy[col] = pd.to_datetime(df_copy[col], format=date_format)   
                except (KeyError, ValueError):
                    continue

        # Get sorted data
        sorted_indices = df_copy.sort_values(by=sort_columns, ascending=sort_ascending).index
        sorted_values = df_copy.loc[sorted_indices, columnName]
        
        # Convert rules to dictionary form, and ensure values in rules are also string type
        rule_dict = {}
        for rule in sequenceRule:
            # Special handling for null values
            if pd.isna(rule['value']):
                rule_key = np.nan
            else:
                rule_key = str(rule['value'])  # Convert to string
                
            # Convert values in allowed_next to strings
            allowed_next_str = []
            for val in rule['allowed_next']:
                if pd.isna(val):
                    allowed_next_str.append(np.nan)
                else:
                    allowed_next_str.append(str(val))
            
            rule_dict[rule_key] = allowed_next_str
        
        outlier_pairs = []

        # Traverse sorted data, check if subsequent values of each value conform to rules
        for i in range(len(sorted_values)-1):
            current_idx = sorted_indices[i]
            next_idx = sorted_indices[i+1]
            current_val = sorted_values.iloc[i]
            next_val = sorted_values.iloc[i+1]

            # Sequences across null values are not detected
            if is_empty_sequence_value(current_val) or is_empty_sequence_value(next_val):
                continue
            
            # Whether current value is in rules (including null values)
            current_key = np.nan if pd.isna(current_val) else current_val
            
            if current_key in rule_dict:
                allowed_next = rule_dict[current_key]
                # Check if next value is in allowed list
                next_matches = False
                for allowed_val in allowed_next:
                    if pd.isna(allowed_val) and pd.isna(next_val):
                        next_matches = True
                        break
                    elif not pd.isna(allowed_val) and allowed_val == next_val:
                        next_matches = True
                        break
                
                if not next_matches:
                    outlier_pair = {
                        "currentIndex": int(current_idx),
                        "nextIndex": int(next_idx),
                        "sortCurrentIndex": int(i),
                        "sortNextIndex": int(i + 1)
                    }
                    outlier_pairs.append(outlier_pair)
    except Exception:
        return []
    
    return outlier_pairs

def detect_sequence_valid_pairs(df, columnName, orderCondition, sequenceRule, tableDict):
    """
    Return list of index pairs that conform to sequence rules
    
    Parameters:
        df (pandas.DataFrame): Data frame to be checked
        columnName (str): Column name to be checked
        orderCondition (dict): Sort condition
        sequenceRule (list): List of sequence rules, each rule is a dictionary
            containing 'value' and 'allowed_next' keys
        tableDict (dict): Table dictionary containing column format information
    
    Returns:
        list: List of index pairs that conform to sequence rules, each element is a dictionary containing currentIndex and nextIndex
    """
    
    # Parameter validation
    if not isinstance(sequenceRule, list):
        raise ValueError("sequenceRule must be a list")
    
    if len(df) < 2:
        return []
    
    # Create data copy to avoid modifying original data
    df_copy = df.copy()
    
    # Convert numeric types to strings
    if pd.api.types.is_numeric_dtype(df_copy[columnName]):
        df_copy[columnName] = df_copy[columnName].astype(str)
    
    # Build sort conditions
    sort_columns = []
    sort_ascending = []
    
    for i in range(1, 4):
        column_key = f"firstOrderColumn" if i == 1 else f"secondOrderColumn" if i == 2 else "thirdOrderColumn"
        type_key = f"firstOrderType" if i == 1 else f"secondOrderType" if i == 2 else "thirdOrderType"
        
        if column_key in orderCondition:
            sort_columns.append(orderCondition[column_key])
            sort_ascending.append(orderCondition[type_key].lower() == "asc")
    
    if orderCondition.get('dateColumns', []) != []:
        for col in orderCondition['dateColumns']:
            try:
                date_format = tableDict[col]['mainFormat']
                df_copy[col] = pd.to_datetime(df_copy[col], format=date_format)   
            except (KeyError, ValueError):
                continue

    # Get sorted data
    sorted_indices = df_copy.sort_values(by=sort_columns, ascending=sort_ascending).index
    sorted_values = df_copy.loc[sorted_indices, columnName]
    
    # Convert rules to dictionary form, and ensure values in rules are also string type
    rule_dict = {}
    for rule in sequenceRule:
        # Special handling for null values
        if pd.isna(rule['value']):
            rule_key = np.nan
        else:
            rule_key = str(rule['value'])
            
        # Convert values in allowed_next to strings
        allowed_next_str = []
        for val in rule['allowed_next']:
            if pd.isna(val):
                allowed_next_str.append(np.nan)
            else:
                allowed_next_str.append(str(val))
        
        rule_dict[rule_key] = allowed_next_str
    
    valid_pairs = []

    # Traverse sorted data, check if subsequent values of each value conform to rules
    for i in range(len(sorted_values)-1):
        current_idx = sorted_indices[i]
        next_idx = sorted_indices[i+1]
        current_val = sorted_values.iloc[i]
        next_val = sorted_values.iloc[i+1]

        # Sequences across null values are not detected
        if is_empty_sequence_value(current_val) or is_empty_sequence_value(next_val):
            continue
        
        # Whether current value is in rules (including null values)
        current_key = np.nan if pd.isna(current_val) else current_val
        
        if current_key in rule_dict:
            allowed_next = rule_dict[current_key]
            # Check if next value is in allowed list
            for allowed_val in allowed_next:
                if pd.isna(allowed_val) and pd.isna(next_val):
                    valid_pair = {
                        "currentIndex": int(current_idx),
                        "nextIndex": int(next_idx),
                        "sortCurrentIndex": int(i),
                        "sortNextIndex": int(i + 1)
                    }
                    valid_pairs.append(valid_pair)
                    break
                elif not pd.isna(allowed_val) and allowed_val == next_val:
                    valid_pair = {
                        "currentIndex": int(current_idx),
                        "nextIndex": int(next_idx),
                        "sortCurrentIndex": int(i),
                        "sortNextIndex": int(i + 1)
                    }
                    valid_pairs.append(valid_pair)
                    break
    
    return valid_pairs