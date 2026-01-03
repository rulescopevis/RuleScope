import re
import os
import sys

from pydantic import BaseModel

# Get parent directory of parent directory
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def refine_format_character(formatList, validFlag, selectValue, model):
    if model != "api":
        model = "qwen2.5:14b-instruct-q4_K_M"
        
    # Add data validation logic
    validList = []
    invalidList = []
    
    # Classify data into validList and invalidList
    for value in selectValue:
        if re.match(formatList[0], value):
            validList.append(value)
        else:
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
            "refineFormat": None
        }

    # Use processValue instead of original selectValue
    refineStatus = True
    refineFormat = None
    for value in processValue:
        matched = False
        
        for format in formatList:
            if re.match(format, value):
                matched = True
                if format == formatList[0]:
                    refineFormat = format
                else:
                    refineFormat = f"{formatList[0]}|{format}"
                break

        if not matched:  # If current value doesn't match any format
            refineStatus = False
            break  # Stop the process once a value fails to match

    # Finally verify all values can match refineFormat
    if refineStatus and refineFormat:
        for value in processValue:
            if not re.match(refineFormat, value):
                refineStatus = False
                break

    if refineStatus == False:    
        systemPrompt = '''
        You are an expert in format validation and regex creation. Based on the provided data, generate an improved regular expression (regex) that accurately validates the desired format.
        '''

        class refineFormat(BaseModel):
            refineFormat: str

        schema = refineFormat.model_json_schema()

        userPrompt = '''
        There is an existing validation rule for the format, but the following data does not match it. Please refine the regex so that the provided data is recognized as a valid format.

        Return your result in JSON format with the following structure:

        {
            "refineFormat": "regex"
        }
        '''

        userPrompt += f"Data: {str(processValue)}\n validation rule(format): {formatList[0]}"

        if model != "api":
            llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
        else:
            llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

        refineStatus = True
        refineFormat = llmResult["refineFormat"]

        result = {
            "refineStatus": refineStatus,
            "refineFormat": refineFormat
        }
    else:
        systemPrompt = '''
        You are an expert in format validation and regex creation. Your task is to refine and enforce stricter validation rules on regular expressions.
        '''

        userPrompt = '''
        The currently provided format regex successfully validates the provided data, meaning the data is considered valid. However, we now need to make the regex stricter so that the current data is judged as invalid. Please create a refined version of the regex that does not match the provided data.

        Return your result in JSON format with the following structure:

        {
            "refineFormat": "regex"
        }
        '''
        userPrompt += f"Data: {str(processValue)}\n validation rule(format): {formatList[0]}"

        if model != "api":
            llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
        else:
            llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

        refineStatus = True
        refineFormat = llmResult["refineFormat"]

        result = {
            "refineStatus": refineStatus,
            "refineFormat": refineFormat
        }
    
    return result