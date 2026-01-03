import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal

# Add the project root directory to the import search path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def character_format(dataList, columnName, domainDescription, model):
    if model is None:
        model = "qwen2.5:14b-instruct-q4_K_M"
    systemPrompt = '''
You are a regex pattern generator specialized in creating precise and practical regular expressions following Python's re module syntax. You analyze the dataset's domain, data column name, data description, and sample data values to determine if the column should conform to a strict format—one which, if not met, indicates erroneous data. If such a strict format exists, generate regex pattern(s) accordingly; otherwise, return "None".
    '''

    class FormatList(BaseModel):
        Format: Union[List[str], Literal["None"]]

    schema = FormatList.model_json_schema()

    userPrompt = '''
Task Description:
You are provided with information about a data column, including its name, sample data values, and the overall dataset’s domain and description. Your mission is to determine whether the column is expected to conform to a specific strict format (where any deviation is considered incorrect). If so, generate precise regex pattern(s) that accurately match the valid format. If not, return "None".

Step 1: Requirements Analysis
- Examine the column name for semantic cues.
- Review the provided dataset's domain and description to determine if the column should meet a strict, predefined format.
- Analyze the sample data values to identify consistent structural patterns (e.g., fixed-length IDs, formatted numbers, or standard addresses).
- Decide whether the data is meant to follow this specific format (i.e., data not matching the format is erroneous). If no strict format is required, return "None".

Step 2: Format and Component Requirements
- Use only the specified regex components:
  • Character classes: [A-Z], [a-z], [0-9]
  • Groups with alternation: (pattern1|pattern2|...)
  • Quantifiers: *, +, ?, {n}, {n,m}
  • Anchors: ^ and $
  • Space characters and literal strings for common abbreviations (e.g., St, Ave, Rd)
- Ensure that all patterns are compatible with Python's re module.

Step 3: Pattern Design Rules
- For columns with explicit, strict formats (e.g., fixed-length IDs, structured numbers, or addresses), provide precise patterns that match only the valid format.
- Avoid overly broad patterns; each pattern must capture a distinctly different data format where deviations are considered errors.
- Do not generate multiple patterns that are logically equivalent.
- Order patterns from the most precise to the least precise.
- For address-related fields, ensure patterns account for:
  • Street numbers (allowing 1-4 digits)
  • Common street type abbreviations (e.g., St, Street, Ave, Avenue)
  • Ordinal indicators (e.g., 1st, 2nd, 3rd)
- For ID or code fields, generate only patterns that exactly match the strict format shown in the examples.

Step 4: Return Value Rules
- If the analysis indicates that the column must adhere to a specific strict format, return the precise regex pattern(s) in an array.
- If the column does not require a strict format or if no consistent regex pattern can be derived, return "None".

Return your result ONLY in the following JSON format (do not include any additional notes or explanations):

{
    "pattern": ["best_pattern", "alternative_pattern", ...]
}

OR

{
    "pattern": "None"
}


    '''

    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'column name:' + columnName + '\n\n column data: '
    userPrompt += str(list(dataList))

    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    if llmResult is None or "pattern" not in llmResult:
        return {"status": False, "characterFormat": None}
    characterPattern = llmResult['pattern']
    if characterPattern == "None":
        return {"status": False, "characterFormat": None}
    else:
        return {"status": True, "characterFormat": characterPattern}

