import os
import sys
from typing import List, Union

from pydantic import BaseModel

# Ensure the parent directory is available for locating shared helpers
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def duplicate_duplicate_multi(dataframe, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert in data quality and uniqueness validation with deep domain expertise. Your task is to analyze the provided table details and determine which columns—or minimal combinations of columns—should be used as a composite key that guarantees no two records share the same set of values. The chosen composite key must uniquely identify each record either inherently or via domain-specific constraints, and each candidate tuple must contain no more than three columns.
'''

    class MultipleDuplicateColumnsList(BaseModel):
        multipleDuplicateColumnsList: Union[List[List[str]], str]

    schema = MultipleDuplicateColumnsList.model_json_schema()

    userPrompt = '''
Task Description:
You will be provided with the table's domain, description, and details regarding each column’s semantics. Your goal is to determine which columns should be combined for duplicate validation (i.e., to form a composite key) ensuring that every record is unique.

Steps:

Step 1 – Review Table Context:
   - Read the provided Table Domain and Description to understand the overall context and the specific business or operational rules.
   - Analyze the semantic meanings of each column using the additional details provided.

Step 2 – Examine Column Relationships:
   - Evaluate the relationships among columns based on their names, sample data, and documented semantics.
   - Determine whether a single column is sufficient to enforce uniqueness or if a composite key is necessary.

Step 3 – Identify Minimal Composite Key(s):
   - Identify candidate composite key tuple(s) using the minimal set of columns needed to ensure uniqueness.
   - Each composite key candidate should contain one, two, or three columns only.
   - If more than three columns seem necessary, propose multiple candidate tuples—each with no more than three columns—that collectively enforce uniqueness.
   - **Important:** Every column name in your composite key candidate must be one of the columns provided in the input data table. Do not include any extraneous or non-existent column names. Also, ensure that within each candidate, there are no duplicate column names.

Step 4 – Output Construction:
   - Return the candidate composite key tuple(s) exactly in the JSON format specified below.
   - If no valid uniqueness constraint can be inferred from the provided information, return "None".

Return Format:
Return your answer ONLY in the following JSON format (do not include any extra notes or explanations):

{
    "multipleDuplicateColumnsList": [["columnName1", "columnName2", ...], ["columnName3", "columnName4", ...], ...]
}

OR, if no valid composite key can be inferred:

{
    "multipleDuplicateColumnsList": "None"
}

Now, here is the table information:
'''
    userPrompt += "domain: " + domainDescription['domain'] + "\n"
    userPrompt += "description: " + domainDescription['description'] + "\n\n"

    html_table = "<table border='1'>\n"
    html_table += "<tr>"
    for columnName in dataframe.columns:
        html_table += f"<th>{columnName}</th>"
    html_table += "</tr>\n"
    
    # Add a row showing unique values per column
    html_table += "<tr>"
    for columnName in dataframe.columns:
        columnData = list(dataframe[columnName])
        columnData = set(columnData)
        html_table += f"<td>{str(columnData)}</td>"
    html_table += "</tr>\n"
    
    html_table += "</table>"

    userPrompt += "Here is the table:\n" + html_table
    if model != "api":
        multipleDuplicateResult = chat_api(user_prompt=userPrompt, provider="ollama", system_prompt=systemPrompt, format=schema, temperature=0.1, model=model)
    else:
        multipleDuplicateResult = chat_api(user_prompt=userPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.1, model=None)
    multipleDuplicateColumnsList = []
    if multipleDuplicateColumnsList == "None":
        return {"status": False, "multipleDuplicateColumnsList": None}
    for item in multipleDuplicateResult['multipleDuplicateColumnsList']:
        addFlag = True
        for column in item:
            if column not in dataframe.columns:
                addFlag = False
                break
        if len(item) < 2:
            addFlag = False
        if addFlag:
            multipleDuplicateColumnsList.append(item)
    if multipleDuplicateColumnsList == []:
        return {"status": False, "multipleDuplicateColumnsList": None}
    else:
        return {"status": True, "multipleDuplicateColumnsList": multipleDuplicateColumnsList}