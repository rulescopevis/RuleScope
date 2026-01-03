import pandas as pd
import numpy as np

def detect_formula_numeric(variableList, operationList):
    """
    Detect whether the data conforms to the specified calculation relationship
    
    Args:
        variableList: List of variables or numeric values participating in the calculation, can be column_name or specific values
        operationList: List of operators, including "+", "-", "*", "/", "=" etc.
    
    Returns:
        List of row indices that do not satisfy the calculation relationship
    """
    
    def evaluate_expression(variables, operations, idx):
        """Calculate the value of the expression"""
        # Get the value of the first variable
        if isinstance(variables[0], pd.Series):
            result = variables[0][idx]
        else:
            result = float(variables[0])
            
        # Process all operations before the equal sign
        equal_pos = operations.index("=")
        for i in range(equal_pos):
            next_value = variables[i+1]
            if isinstance(next_value, pd.Series):
                next_value = next_value[idx]
            else:
                next_value = float(next_value)
                
            if operations[i] == "+":
                result += next_value
            elif operations[i] == "-":
                result -= next_value
            elif operations[i] == "*":
                result *= next_value
            elif operations[i] == "/":
                if next_value == 0:  # Handle division by zero case
                    return None
                result /= next_value
                
        # Get the value on the right side of the equal sign
        expected_result = variables[equal_pos+1]
        if isinstance(expected_result, pd.Series):
            expected_result = expected_result[idx]
        else:
            expected_result = float(expected_result)
            
        return abs(result - expected_result) < 1e-10  # Compare with decimal precision
    
    # Get index of all Series
    series_list = [var for var in variableList if isinstance(var, pd.Series)]
    if not series_list:
        return []
    df_index = series_list[0].index
    
    # Initialize result list
    invalid_index = []
    
    # Iterate through each row to check calculation relationship
    for idx in df_index:
        # Check if there are null values
        has_null = False
        for var in variableList:
            if isinstance(var, pd.Series):
                if pd.isna(var[idx]):
                    has_null = True
                    break
        
        if has_null:
            continue
            
        # Check calculation relationship
        if not evaluate_expression(variableList, operationList, idx):
            invalid_index.append(idx)
            
    return invalid_index