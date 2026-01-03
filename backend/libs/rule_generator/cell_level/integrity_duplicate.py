import os
import sys

from typing import List, Dict

from pydantic import BaseModel
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def missing_duplicate_flag(dataframe, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are a data validation analyzer that examines database schemas and determines appropriate validation rules based on both column-level and table-level context. Your role is to focus on the overall business purpose of the dataset, the table's domain, and the semantic meaning of each column.
    '''

    # ollama json mode

    class MissingAndDuplicateValueFlagList(BaseModel):
        missingValueFlag: List[str]
        specialMissingValueDict: Dict[str, List[float]]
        duplicateFlag: List[str]

    schema = MissingAndDuplicateValueFlagList.model_json_schema()

    userPrompt = '''
Task Description:
You are provided with a table description, column names, and sample data. Based on this information, analyze the domain context, table usage, and the semantic meaning of each column. Determine which columns require missing value checks (only flagging those where a missing value makes the entire row invalid) and duplicate checks (only flagging those where duplicates indicate an error). Additionally, for columns flagged for missing values, identify any special or exceptional values (for example, in an "age" column, a value like -1 may denote a missing value) based on both the column semantics and data patterns. Only record a column in the specialMissingValueDict if it is also flagged for missing values.

Step 1: Domain, Table Description & Data Context Analysis
- Review the table’s overall business purpose, provided table description, and sample data.
- Understand the domain and the intended use of each column.

Step 2: Semantic and Group Analysis
- Identify groups of semantically related columns (e.g., longitude/latitude, first_name/last_name, street/city/state/zip, start_date/end_date).
- Determine each column’s semantic role and verify expected relationships using data patterns.

Step 3: Missing Value Analysis Standard
- Flag a column for missing value validation ONLY when its absence renders the entire row invalid or prevents the row from fulfilling its intended purpose.
- Do not flag a column if a missing entry results only in an incomplete record that still meets its intended purpose.

Step 4: Duplicate Value Analysis Standard
- Assess each column to determine whether it is expected to uniquely identify a record.
- Flag a column for duplicate validation only if duplicate values indicate an error in the row (e.g., duplicate user IDs in a user information table).
- Do not flag columns for duplicate values if duplicates are acceptable given the dataset’s context.

Step 5: Special Missing Value Rules
- For each column flagged in Step 3, analyze the data and semantic context to determine if any special values (e.g., a value like -1 in an "age" column) represent a valid missing state.
- Only include a column in specialMissingValueDict if it is flagged for missing value validation and special missing values are detected.

Return your result ONLY in the following JSON format (do not include any additional notes or explanations):

{
    "missingValueFlag": [
        "column_name1",
        "column_name2"
    ],
    "specialMissingValueDict": {
        "column_name1": ["special_value1", "special_value2"],
        "column_name2": ["special_value3"]
    },
    "duplicateFlag": [
        "column_name1",
        "column_name2"
    ]
}

OR, if no validation checks are required, return:

{
    "missingValueFlag": [],
    "specialMissingValueDict": {},
    "duplicateFlag": []
}

Here is the table description and the column names along with sample column data for your inference:\n\n
    '''
    userPrompt += "domain: " + domainDescription['domain'] + "\n"
    userPrompt += "description: " + domainDescription['description'] + "\n\n"
    html_table = "<table border='1'>\n"
    html_table += "<tr>"
    for columnName in dataframe.columns:
        html_table += f"<th>{columnName}</th>"
    html_table += "</tr>\n"
    
    html_table += "<tr>"
    for columnName in dataframe.columns:
        columnData = list(dataframe[columnName])
        columnData = set(columnData)
        html_table += f"<td>{str(columnData)}</td>"
    html_table += "</tr>\n"
    
    html_table += "</table>"
    
    userPrompt += html_table

    if model != "api":
        llmResult = chat_api(user_prompt=userPrompt, provider="ollama", system_prompt=systemPrompt, format=schema, temperature=0.2, model=model)
    else:
        llmResult = chat_api(user_prompt=userPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.2, model=None)
    if llmResult == {}:
        return {"result": False, "missingValueDict": None}
    else:
        return {"result": True, "missingValueFlag": llmResult['missingValueFlag'], "specialMissingValueDict": llmResult['specialMissingValueDict'], "duplicateFlag": llmResult['duplicateFlag']}
