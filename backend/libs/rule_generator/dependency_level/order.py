import os
import sys

from pydantic import BaseModel
from typing import Union, Literal

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def table_order_condition(sampleDataframe, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are a specialized data analyst assistant with in-depth expertise in data sorting and sequential analysis. You possess comprehensive domain knowledge and understand that not all datasets require explicit ordering. Your primary task is to evaluate the provided dataset: first determine if the data inherently follows a continuous, time-based, or event-sequential order; only then establish ordering conditions for effective difference and event sequence analysis. If the dataset does not exhibit a clear sequential or event-based pattern, do not produce ordering conditions. In that case, return "None".
    '''

    class OrderCondition(BaseModel):
        firstOrderColumn: Union[str, Literal["None"]]
        firstOrderType: Union[str, Literal["None"]]
        secondOrderColumn: Union[str, Literal["None"]]
        secondOrderType: Union[str, Literal["None"]]
        thirdOrderColumn: Union[str, Literal["None"]]
        thirdOrderType: Union[str, Literal["None"]]

    class TableOrderCondition(BaseModel):
        tableOrderCondition: Union[OrderCondition, Literal["None"]]
    

    schema = TableOrderCondition.model_json_schema()

    userPrompt = '''
Task Description:
You are provided with a dataset along with its domain and description. Your task is to analyze the dataset to determine the need for sorting by evaluating if it exhibits a continuous, time-based, or event-sequential order. Establish up to three ordering conditions if a clear sequential pattern exists. If the dataset does not inherently require ordering, return "None".

Step 1: Domain, Dataset Description, and Ordering Necessity Identification
- Use the provided domain and dataset description to understand the data’s context and intended use.
- Critically assess whether the dataset is meant to record sequential events or time-based progress. Confirm that adjacent rows are designed to follow a continuous sequence (either by time or by explicit event progression).
- If there is any uncertainty or if the dataset does not exhibit clearly defined time-series or event-based characteristics (e.g., the records are not intrinsically sequential), then return "None". Under no circumstances should ordering be applied if the dataset lacks an inherent sequential or event-based structure.
- Only if you are 100% certain that a valid sequential order exists based on the domain and dataset description, then identify all columns that could potentially be used for ordering. These may include grouping (categorical) fields—provided they are explicitly defined for segmenting sequential events—and sequential (time or numeric) fields.

Step 2: Data Value Assessment
- Rigorously examine the actual data values in the candidate columns identified in Step 1.
- Validate that the actual values support a strict, coherent, and continuous ordering. For example, if a column contains values like "Monday" and "Tuesday", first confirm that these values follow a recognized standard sequence; if they appear arbitrarily or inconsistently, exclude them.
- Discard any candidate that shows random ordering, inconsistent formats, or lacks a clear progression.
- If no candidate column can be verified to produce a valid continuous sequence after this check, then return "None".

Step 3: Multi-Level Ordering Determination (Maximum Three Levels)
- From the remaining valid columns, select and prioritize up to three based on their intrinsic roles:
  • Primary Ordering: First check if there exists a categorical field that represents grouping (for example, a column that denotes a location, detection point, or any explicit grouping indicator). Since subsequent sequence and difference analysis require that records belong to the same group, such grouping fields should be prioritized as the first ordering condition. If no suitable grouping column exists, then select a time-based or numeric field as the primary ordering column.
  • Secondary Ordering: If a grouping column has been selected, choose an additional ordering field—typically a time-based or numeric field—that refines the sequence within each group. If no grouping column was selected, then treat the next most reliable ordering column as secondary.
  • Tertiary Ordering: Optionally, select a third field if it further clarifies the sequence.
- If more than three valid ordering columns are available, apply strict relevance criteria and hierarchical relationships, ensuring that only fields enhancing the logical grouping and continuous progression are selected.
- Do not include any field that could disrupt the logical grouping or continuous sequence.

Step 4: Order Direction Determination
- For each selected ordering condition, determine the sort direction by considering the field’s inherent properties:
  • Use Ascending (ASC) if the field is defined in a naturally incremental order (e.g., historical time progression, cumulative totals, or inherently ordered categorical data).
  • Use Descending (DESC) if the field indicates a countdown, depletion, or remaining values. Specifically, if the column name or context includes indicators like "clock", "timer", or similar, always assign DESC.
- Confirm that the chosen direction is fully compatible with the field’s sequential nature. If any ambiguity exists, do not use the field.

Return your result ONLY in the following JSON format (do not include any additional notes or explanations):

{
    "tableOrderCondition": {
        "firstOrderColumn": "column name/None",
        "firstOrderType": "Asc/Desc/None",
        "secondOrderColumn": "column name/None",
        "secondOrderType": "Asc/Desc/None",
        "thirdOrderColumn": "column name/None",
        "thirdOrderType": "Asc/Desc/None"
    }
}

OR, if no valid sorting condition exists or the dataset does not strictly require ordering:

{
    "tableOrderCondition": "None"
}

Follow these steps strictly. If there is any doubt regarding the necessity or coherence of ordering, return "None".
    '''

    userPrompt += "domain: " + domainDescription['domain'] + "\n"
    userPrompt += "description: " + domainDescription['description'] + "\n\n"
    html_table = "<table border='1'>\n"
    html_table += "<tr>"
    for columnName in sampleDataframe.columns:
        html_table += f"<th>{columnName}</th>"
    html_table += "</tr>\n"
    
    html_table += "<tr>"
    for columnName in sampleDataframe.columns:
        columnData = list(sampleDataframe[columnName])
        columnData = set(columnData)
        html_table += f"<td>{str(columnData)}</td>"
    html_table += "</tr>\n"
    
    html_table += "</table>"
    
    userPrompt += html_table

    if model != "api":
        llmResult = chat_api(user_prompt=userPrompt, provider="ollama", system_prompt=systemPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(user_prompt=userPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.1, model=None)
    if llmResult["tableOrderCondition"] == "None":
        return {"result": False, "tableOrderCondition": None}
    else:
        return {"result": True, "tableOrderCondition": llmResult['tableOrderCondition']}
