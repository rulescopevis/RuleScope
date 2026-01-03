import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal
from enum import Enum

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def numeric_compareRelations(columnList, domainDescription, model):
    if model == None:
        model = "qwen2.5:72b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert analyst specializing in mathematical relationships and data semantics. Your role is to:
- Identify and establish only mathematically or definitionally guaranteed relationships.
- Validate definitional necessities with strict unit and type consistency.
- Recognize metric hierarchies and enforce universal, exception-free rules.

Your core objectives:
1. Derive relationships that are mathematically or definitionally necessary.
2. Avoid basing conclusions on mere correlations or heuristic patterns.
3. Maintain strict compatibility regarding units and data types.
4. Default to "None" when any uncertainty exists.
5. Identify only those relationships that are universally true and free from exceptions.
    '''
    
    class CompareRelationType(str, Enum):
        LARGER = "larger"
        LARGER_EQUAL = "larger_equal"
        EQUAL = "equal"
        SMALLER = "smaller"
        SMALLER_EQUAL = "smaller_equal"
        NOT_EQUAL = "not_equal"

    class NumericComparison(BaseModel):
        column1: str
        column2: str
        compareRelation: CompareRelationType

    class NumericCompareResult(BaseModel):
        numericCompareList: Union[List[NumericComparison], Literal["None"]]

    schema = NumericCompareResult.model_json_schema()
    
    userPrompt = '''
Task Description:
You will be provided with the data table's domain and description along with the semantic details of each column. Based on this information, your objective is to determine which pairs of columns require numerical comparison relationships that are mathematically or definitionally guaranteed. Use the table's domain, description, and each column's semantic meaning to decide which columns should be compared.

Steps:

Step 1 – Identify Candidate Relationships:
  - Analyze the provided table domain, description, and semantic details for each column.
  - Determine candidate pairs based on inherent mathematical or definitional ordering implied by the domain.
  - For time-related data especially, evaluate the typical progression (e.g., events usually follow a natural sequence) but note that some contexts may require reversed relationships (e.g., descending order for countdowns). Use domain context to decide the appropriate direction.
  - Only consider candidates where the relationship is defined by the data's semantics, with fully compatible units and types, and is universally true. Discard any cases with unit conflicts, type mismatches, or semantic ambiguity.

Step 2 – Validate Relationship Eligibility:
  - Confirm that each candidate relationship is mathematically necessary and based on formal definitions.
  - Exclude any relationships based solely on observed correlations or domain-specific heuristics.
  - **Self-Validation Requirement:** Internally verify and ensure that the chosen comparison operator conforms to the expected order defined by the domain and the column semantics. This is crucial in cases where a reversal might occur—verify that the operator logically supports a relationship of the form: **column1 compareRelation column2**.
  - Do not include any of your internal reasoning in the final JSON output.

Step 3 – Finalize the Relationship List:
  - For every approved relationship, specify it using one of the following comparison types:
      • "larger": strictly greater than (>)
      • "larger_equal": greater than or equal to (≥)
      • "equal": exactly equal to (=)
      • "smaller": strictly less than (<)
      • "smaller_equal": less than or equal to (≤)
      • "not_equal": not equal to (≠)  // Use only when mathematically guaranteed.
  - **Important:** Ensure that each relationship is returned with the correct ordering, following the format: **column1 compareRelation column2**.
  - If no valid, universally guaranteed relationships exist, return a null result.

Return Format:
Return your result ONLY in the following JSON format:

{
    "numericCompareList": [
        {
            "column1": "column_name1",
            "column2": "column_name2",
            "compareRelation": "relation_type"  // larger, larger_equal, equal, smaller, smaller_equal, not_equal
        }
        // Additional valid comparisons if applicable.
    ]
}

OR:

{
    "numericCompareList": "None"
}

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

    if llmResult['numericCompareList'] == "None":
        return {"status": False, "numericCompareList": None}
    
    numericCompareList = []
    for item in llmResult['numericCompareList']:
        if item["column1"] in columnList and item["column2"] in columnList:
            numericCompareList.append(item)
    if numericCompareList == []:
        return {"status": False, "numericCompareList": None}
    else:
        return {"status": True, "numericCompareList": numericCompareList}
