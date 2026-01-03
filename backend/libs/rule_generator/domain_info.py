import os
import sys

from pydantic import BaseModel
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def domainInfo(dataframe, model):
    if model != "api":
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert with comprehensive knowledge across all domains. Your role is to analyze sample data tables and determine the table domain along with a succinct explanation of the data table. Use your deep understanding of data semantics and column context when analyzing the table.
'''

    class DomainDescription(BaseModel):
        domain: str
        description: str


    class DomainDescriptionResponse(BaseModel):
        domainDescription: DomainDescription

    try:
        # Pydantic v2
        schema = DomainDescriptionResponse.model_json_schema()
    except AttributeError:
        # Pydantic v1
        schema = DomainDescriptionResponse.schema()

    userPrompt = '''
Task Description:
You are provided with a sample data table, including column names and sample data. Your mission is to precisely determine the domain of the data table and provide a concise explanation that captures its semantic meaning and the role of its columns.

Step 1: Domain Identification
- Analyze the column names and the underlying data semantics.
- Determine the specific domain of the data table using a few words to capture the field or subject area accurately.

Step 2: Data Table Explanation
- Write a succinct description of the data table.
- Explain the semantic meaning of the table and outline the roles and relationships of its columns.

Return your result ONLY in the following JSON format (do not include any extra notes or explanations):
{
    domainDescription:{
        "domain": "domain",
        "description": "description"
    }
}

Here is the sample data table:
'''

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
    try:
        if llmResult == {}:
            return {"result": False, "domainDescription": None}
        else:
            return {"result": True, "domainDescription": llmResult['domainDescription']}
    except Exception as e:
        return {"result": False, "domainDescription": None}

