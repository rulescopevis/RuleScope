import os
import sys

from pydantic import BaseModel
from typing import Union, Literal, List
from enum import Enum

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def date_compareRelations(columnList, domainDescription, model):
    if model == None:
        model = "qwen2.5:14b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert analyst specializing in temporal relationships and business process flows. Your role involves:
- Analyzing temporal dependencies in business processes
- Determining appropriate sequential relationships
- Validating time-based constraints and ensuring process flow integrity
- Handling time-related comparisons with precision

Your core objectives are to:
1. Identify valid temporal relationships between events.
2. Apply appropriate strict (<, >) versus non-strict (<=, >=) time comparisons.
3. Maintain temporal consistency in business process flows.
4. Respect business rules, regulatory obligations, and SLAs.
5. Accurately handle comparisons involving timestamps and durations.

    '''

    class TimeCompareRelationType(str, Enum):
        LARGER = "larger"
        LARGER_EQUAL = "larger_equal"
        EQUAL = "equal"
        SMALLER = "smaller"
        SMALLER_EQUAL = "smaller_equal"
        NOT_EQUAL = "not_equal"

    class DateComparison(BaseModel):
        column1: str
        column2: str
        compareRelation: TimeCompareRelationType

    class DateCompareResult(BaseModel):
        dateCompareList: Union[List[DateComparison], Literal["None"]]

    schema = DateCompareResult.model_json_schema()

    userPrompt = '''
Task Description:
You will be provided with the data table's domain and description along with the semantic details of each column. Based on this information, your task is to determine which pairs of columns require valid temporal comparison relationships. Use the table's domain, description, and each column's semantic meaning to decide the columns that should be compared.

Steps:

Step 1 – Identify Candidate Relationships:
  - Analyze the provided table domain, description, and the semantic details of each column.
  - Determine candidate pairs based on inherent temporal or sequential ordering implied by the domain. For example, in a business process, columns like "create_time", "approve_time", and "complete_time" should follow a chronological order.
  - Only consider comparisons where the relationship is defined by the data's semantics, with compatible time formats and clear sequential relevance.

Step 2 – Validate Relationship Eligibility:
  - Confirm that each candidate relationship is temporally logical and guaranteed by definition or formal business rules.
  - Exclude any comparisons that involve columns with incompatible time concepts (e.g., comparing a timestamp with a duration or mismatched time zones without conversion) or that show ambiguous sequencing.
  - **Self-Validation Requirement:** Internally verify and ensure you can semantically justify why the relationship holds (i.e., why "column1 compareRelation column2") without including this explanation in the final output.

Step 3 – Finalize the Relationship List:
  - For each valid relationship, specify one of the following comparison types:
      • "larger": strictly greater than (>)
      • "larger_equal": greater than or equal to (≥)
      • "equal": exactly equal to (=)
      • "smaller": strictly less than (<)
      • "smaller_equal": less than or equal to (≤)
      • "not_equal": not equal to (≠)  // Use only when mathematically or definitionally guaranteed.
  - **Important:** Ensure that each final relationship is returned in the correct order, following the format: **column1 compareRelation column2**.
  - If no universally valid temporal relationships exist, return a null result.

Return Format:
Return your result ONLY in the following JSON format:

{
    "dateCompareList": [
        {
            "column1": "column_name1",
            "column2": "column_name2",
            "compareRelation": "relation_type"  // larger, larger_equal, equal, smaller, smaller_equal, not_equal
        }
        // Additional valid comparisons if applicable.
    ]
}

OR

{
    "dateCompareList": "None"
}

Requirements:
1. Default to strict sequential ordering unless specifically required otherwise by business rules.
2. Return "None" if no valid or universally guaranteed relationships can be identified.
3. Validate all relationships for temporal consistency and unit compatibility.
4. Use internal semantic validation to confirm your logic (do not include this reasoning in the final output).

Now, here is the table's domain, description, and column details:


    '''
    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'columns: '
    for column in columnList:
        userPrompt += column + ','
    userPrompt = userPrompt.strip(',')
    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    if llmResult['dateCompareList'] == "" or llmResult['dateCompareList'] == None:
        return {"status": False, "dateCompareList": None}
    
    dateCompareList = []
    for item in llmResult['dateCompareList']:
        if item["column1"] in columnList and item["column2"] in columnList:
            dateCompareList.append(item)
    if dateCompareList == []:
        return {"status": False, "dateCompareList": None}
    else:
        return {"status": True, "dateCompareList": dateCompareList}
