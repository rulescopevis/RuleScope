import pandas as pd

def refine_missing_value(missingDetectFlag, specialMissingValueList, validFlag, selectValue):
    """
    Function to refine missing value detection settings

    Inputs:
        - missingDetectFlag (bool): Flag indicating if missing value detection is enabled
        - specialMissingValueList (list): List of special values considered as missing
        - validFlag (bool): Flag indicating if the current operation is valid
        - selectValue: The value being selected

    Returns:
        dict: A dictionary containing:
            - refineMissingValueStatus (bool): Status of the refinement operation
            - missingDetectFlag (bool): Updated missing detection flag
            - specialMissingValueList (list): Updated list of special missing values
    """
    # Initialize valid and invalid value lists
    validList = []
    invalidList = []
    
    # Check if each value is missing
    for value in selectValue:
        is_missing = False
        # Use pandas isna function to check for missing values
        if pd.isna(value):  # Keep empty string check as pd.isna won't treat empty strings as missing
            is_missing = True
        # Check special missing value list
        elif value in specialMissingValueList:
            is_missing = True
            
        if is_missing:
            invalidList.append(value)
        else:
            validList.append(value)
    
    # Select value list to process based on validFlag
    if validFlag:
        processValue = invalidList
        if not invalidList:  # If no invalid values
            return {
                "refineStatus": False,
                "missingDetectFlag": missingDetectFlag,
                "specialMissingValueList": specialMissingValueList
            }
    else:
        processValue = validList
        if not validList:  # If no valid values
            return {
                "refineStatus": False,
                "missingDetectFlag": missingDetectFlag,
                "specialMissingValueList": specialMissingValueList
            }

    # Initialize refinement operation status
    refineMissingValueStatus = True
    refineSpecialMissingValueList = specialMissingValueList.copy()

    # Use the first value in processValue for processing
    # value_to_process = processValue[0]

    if validFlag:
        # When operation is valid
        if missingDetectFlag:
            # If missing value detection is enabled, disable it
            missingDetectFlag = False
        else:
            for value_to_process in processValue:
                # If missing value detection is disabled, try to remove values from special list
                if value_to_process in specialMissingValueList:
                    refineSpecialMissingValueList.remove(value_to_process)
                else:
                    refineMissingValueStatus = False
    else:
        # When operation is invalid
        if missingDetectFlag:
            for value_to_process in processValue:
                # If missing value detection is enabled, add values to special list
                refineSpecialMissingValueList.append(value_to_process)
        else:
            # If missing value detection is disabled, enable it and add selected values to special list
            missingDetectFlag = True
            for value_to_process in processValue:
                # Only add to special list if value is not a pandas detectable missing value
                if not pd.isna(value_to_process):
                    refineSpecialMissingValueList.append(value_to_process)

    return {
        "refineStatus": refineMissingValueStatus,
        "missingDetectFlag": missingDetectFlag,
        "specialMissingValueList": refineSpecialMissingValueList
    }
