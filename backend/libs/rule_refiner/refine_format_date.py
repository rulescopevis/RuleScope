import os
import sys
from pydantic import BaseModel
from datetime import datetime

# Get parent directory of parent directory
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def refine_format_date(datePattern, validFlag, selectValue, model):
    if model != "api":
        model = "qwen2.5:14b-instruct-q4_K_M"
    # Add data validation logic
    validList = []
    invalidList = []
    
    # Classify data into validList and invalidList
    for value in selectValue:
        try:
            datetime.strptime(value, datePattern[0])
            validList.append(value)
        except ValueError:
            invalidList.append(value)
    
    # Select data list to use based on validFlag
    if validFlag:
        processValue = invalidList
    else:
        processValue = validList
    
    # If processing list is empty, return failure status
    if not processValue:
        return {
            "refineStatus": False,
            "refinePattern": None
        }

    if validFlag:
        refineStatus = True  # Initialize status as True
        refinePattern = None
        
        for value in processValue:  # Use processValue instead of selectValue
            matched = False  # Mark if current value matches any format
            
            for date_format in datePattern:
                try:
                    # Try parsing date with current format
                    datetime.strptime(value, date_format)
                    matched = True
                    # If match successful
                    if date_format == datePattern[0]:
                        refinePattern = date_format
                    else:
                        # For date formats, we don't need to merge, but choose a more generic format
                        refinePattern = date_format
                    break
                except ValueError:
                    continue
            
            if not matched:  # If current value doesn't match any format
                refineStatus = False
                break

        # Finally verify all values can match refineFormat
        if refineStatus and refinePattern:
            for value in processValue:
                try:
                    datetime.strptime(value, refinePattern)
                except ValueError:
                    refineStatus = False
                    break

        if refineStatus == False:
            systemPrompt = '''
            You are an expert in date format validation. Based on the provided data, generate an improved date format pattern that accurately validates the desired format.
            '''

            class refinePattern(BaseModel):
                refinePattern: str

            schema = refinePattern.model_json_schema()

            userPrompt = '''
            There is an existing validation rule for the date format, but the following data does not match it. Please refine the date format pattern so that the provided data is recognized as a valid format.

            Return your result in JSON format with the following structure:

            {
                "refinePattern": "date_format_pattern"
            }

            Note: Use Python's datetime format patterns (e.g., %Y-%m-%d, %d/%m/%Y, etc.)
            '''

            userPrompt += f"Data: {str(processValue)}\n validation rule(format): {datePattern[0]}"

            if model != "api":
                llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
            else:
                llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

            refineStatus = True
            refinePattern = llmResult["refinePattern"]

            result = {
                "refineStatus": refineStatus,
                "refinePattern": refinePattern
            }
        else:
            result = {
                "refineStatus": refineStatus,
                "refinePattern": refinePattern
            }
    else:
        systemPrompt = '''
        You are an expert in date format validation. Your task is to refine and enforce stricter validation rules on date formats.
        '''

        class refinePattern(BaseModel):
            refinePattern: str

        schema = refinePattern.model_json_schema()

        userPrompt = '''
        The currently provided date format pattern successfully validates the provided data, meaning the data is considered valid. However, we now need to make the format stricter so that the current data is judged as invalid. Please create a refined version of the date format that does not match the provided data.

        Return your result in JSON format with the following structure:

        {
            "refinePattern": "date_format_pattern"
        }

        Note: Use Python's datetime format patterns (e.g., %Y-%m-%d, %d/%m/%Y, etc.)
        '''
        
        userPrompt += f"Data: {str(processValue)}\n validation rule(format): {datePattern[0]}"

        if model != "api":
            llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
        else:
            llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

        refineStatus = True
        refinePattern = llmResult["refinePattern"]

        result = {
            "refineStatus": refineStatus,
            "refinePattern": refinePattern
        }

    return result