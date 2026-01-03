import sys
import os

from pydantic import BaseModel
from typing import List, Union, Literal

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def character_substring(df, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are a data analyst specialized in identifying semantic substring relationships between data columns. Your role involves:
- Identifying logical content containment relationships.
- Understanding semantic hierarchies.
- Recognizing natural data patterns.
- Validating relationship consistency.

Your core objectives are to:
1. Identify guaranteed substring relationships.
2. Ensure semantic validity of relationships.
3. Validate hierarchical consistency.
4. Only return definitionally certain relationships.
5. Apply strict content containment rules.
    '''

    class SubstringRelation(BaseModel):
        childColumn: str  # substring column
        parentColumn: str  # containing column

    class SubstringResult(BaseModel):
        substringList: Union[List[SubstringRelation], Literal["None"]]

    schema = SubstringResult.model_json_schema()

    userPrompt = '''
Task Description:
You will be provided with the data table's domain and description along with the semantic details of each column. Based on this information, your objective is to determine which pairs of columns should be used to validate data via a substring relationship (i.e. one column’s value is contained within another’s). First, analyze the column names' semantics in the context of the domain and description to decide whether such a content containment relationship is reasonable. Then, analyze the actual data to determine if the candidate relationship is truly valid. For example, if you initially think that an "ID" column is a substring of an "ID_number" column but the data shows that these columns represent different types of identifiers for different objects, then that candidate relationship should be discarded. You are constructing a data validation rule—not marking individual records as invalid.

Steps:

Step 1 – Identify Candidate Relationships Based on Column Name Semantics:
  - Review the provided table's domain, description, and semantic details for each column.
  - Determine candidate pairs where one column’s value is expected to be contained within another’s. For example:
      • Short forms within full forms (e.g., "id" within "id_number")
      • Parts within whole values (e.g., "first_name" within "full_name")
      • Codes within extended codes (e.g., "area_code" within "full_phone")
      • Base values within decorated values (e.g., "name" within "name_with_title")
  - Only consider candidates where the relationship is definitionally guaranteed and naturally expected from the column names.

Step 2 – Validate Candidate Relationships Theoretically:
  - Confirm that the candidate relationship is semantically and definitionally necessary based on the table's domain and description.
  - Ensure that the expected content containment follows a natural hierarchy that should logically apply to the dataset.
  - Do not include internal reasoning details in your final output.

Step 3 – Analyze Data to Validate Relationship Rationality:
  - Examine the actual data corresponding to the candidate columns.
  - Use the data not to flag individual records but to judge if the candidate substring relationship is truly intended. For example, if the data shows that the values in the two columns describe different identifiers or objects, then the candidate relationship should be discarded.
  - Your decision here is whether the candidate relationship, as defined by column name semantics, is supported by the overall data context.
  - Only retain relationships that are both semantically justified and validated by the data context.

Step 4 – Finalize the Relationship List:
  - For each approved relationship, return an entry with the following keys:
      • "childColumn": the column expected to be contained within another.
      • "parentColumn": the column expected to contain the child's value.
  - **Important:** Return a candidate relationship only if it is semantically sound (based on domain, description, and column names) and is validated as logical by the actual data.
  - If no valid, universally guaranteed substring relationships exist, return "None".

Return Format:
Return your result ONLY in the following JSON format:

{
    "substringList": [
        {
            "childColumn": "column_name1",
            "parentColumn": "column_name2"  // indicating that column_name1's content is expected to be contained in column_name2's content
        }
        // Additional valid relationships if applicable.
    ]
}

OR

{
    "substringList": "None"
}

Now, here is the table's domain, description, and column details:
    '''
    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    html_table = "<table border='1'>\n"
    html_table += "<tr>"
    for columnName in df.columns:
        html_table += f"<th>{columnName}</th>"
    html_table += "</tr>\n"
    
    html_table += "<tr>"
    for columnName in df.columns:
        columnData = list(df[columnName])
        columnData = set(columnData)
        html_table += f"<td>{str(columnData)}</td>"
    html_table += "</tr>\n"
    
    html_table += "</table>"

    userPrompt += "Here is the table:\n" + html_table
    if model != "api":
        llmResult = chat_api(user_prompt=userPrompt, provider="ollama", system_prompt=systemPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(user_prompt=userPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.1, model=None)

    substringList = llmResult['substringList']
    if llmResult['substringList'] == "None":
        return {"status": False, "substringList": None}
    
    substringList = []
    for item in llmResult['substringList']:
        if item["childColumn"] in list(df.columns) and item["parentColumn"] in list(df.columns):
            substringList.append(item)
    if substringList == []:
        return {"status": False, "substringList": None}
    else:
        return {"status": True, "substringList": substringList}