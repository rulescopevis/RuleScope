import os
import sys
import json

from pydantic import BaseModel
from typing import List, Tuple, Union, Literal, Any, Dict
    
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def generate_lookup_List(parentColumn, childColumn, maxDiffValue=100):
    """
    Build a lookup list for parent and child columns.

    Args:
        parentColumn: pandas.Series, parent column values.
        childColumn: pandas.Series, child column values.
        maxDiffValue: int, maximum distinct parent values allowed; beyond this returns an empty list.

    Returns:
        list: lookup entries formatted as [{"parentValue": value, "childValueList": [{"value": value, "count": count}, ...]}, ...]
    """
    if not parentColumn.index.equals(childColumn.index):
        raise ValueError("Both Series must share the same index")
    
    unique_parent_values = parentColumn.dropna().nunique()
    if unique_parent_values > maxDiffValue:
        return []
    
    result = []
    
    import pandas as pd
    df = pd.DataFrame({
        'parent': parentColumn,
        'child': childColumn
    })
    
    for parent_value in sorted(df['parent'].dropna().unique()):
        child_df = df[df['parent'] == parent_value]
        
        child_value_counts = child_df['child'].value_counts(dropna=False).to_dict()
        
        child_value_list = [
            {
                "value": None if pd.isna(value) else value,
                "count": count
            }
            for value, count in sorted(child_value_counts.items(), key=lambda x: (pd.isna(x[0]), str(x[0]) if not pd.isna(x[0]) else ''))
        ]
        
        parent_dict = {
            "parentValue": parent_value,
            "childValueList": child_value_list
        }
        
        result.append(parent_dict)
    
    if df['parent'].isna().any():
        child_df = df[df['parent'].isna()]
        child_value_counts = child_df['child'].value_counts(dropna=False).to_dict()
        
        child_value_list = [
            {
                "value": None if pd.isna(value) else value,
                "count": count
            }
            for value, count in sorted(child_value_counts.items(), key=lambda x: (pd.isna(x[0]), str(x[0]) if not pd.isna(x[0]) else ''))
        ]
        
        parent_dict = {
            "parentValue": None,
            "childValueList": child_value_list
        }
        
        result.append(parent_dict)
    
    return result

def character_lookup(dataframe, domainDescription, model):
    if model == None:
        model1 = "qwen2.5:32b-instruct-q4_K_M"
        model2 = "qwen2.5:72b-instruct-q4_K_M"
    else:
        model1 = model
        model2 = model
    systemPrompt = '''
You are an expert data relationship analyzer working in two distinct phases:

Phase 1 - Relationship Identification:
  - Analyze column names semantically using the provided table domain and description.
  - Identify candidate lookup (mapping) relationships based on hierarchical and reference patterns.
  - The candidate relationships are intended to serve as data validation rules:
      if a row violates such a rule, that row is considered invalid.
  - Output candidate column pairs as "parent → child" relationships.

Phase 2 - Rule Generation:
  - Utilize the candidate relationships from Phase 1 along with provided mapping statistics.
  - Evaluate the semantic relationships and validate the observed mapping patterns.
  - Construct definitive column-to-column lookup rules as data validation criteria.
  - If a data row fails the rule, it will be flagged as invalid.

Your results must strictly follow the provided JSON formats.
    '''

    class Phase1Result(BaseModel):
        lookupList: Union[List[Tuple[str, str]], Literal["None"]]
        
    schema1 = Phase1Result.model_json_schema()

    userFirstPrompt = '''
Task Description – Phase 1:
You will be provided with the data table's domain, description, and detailed semantic information for each column.
Your goal is to analyze the column names and identify candidate mapping (lookup) relationships based on their semantic meaning.
These candidate relationships are intended to be used as data validation rules: if a row does not follow the rule, it is considered invalid.

Step 1 – Contextual Analysis:
  - Review the provided table domain and description.
  - Examine each column’s semantic details to understand the inherent meaning and role within the data.

Step 2 – Candidate Relationship Identification:
  - Identify column pairs that exhibit a clear hierarchical or reference relationship.
  - Consider the following valid relationship patterns:
      A. Hierarchical Relationships:
         • Example: organization (department) → sub_department
         • Example: geographic (country) → state
         • Example: product (category) → subcategory
      B. Reference Relationships:
         • Example: identity (id) → name
         • Example: code (code) → description
         • Example: key (key) → value
  - Validation Criteria:
      • The mapping must be one-to-one or one-to-many.
      • There must be an evident, logically derived parent-child connection.
      • The semantic connection should support its use as a data validation rule.
  - Exclude cases that are ambiguous, many-to-many, transactional, temporal, or involve calculated fields.

Return your Phase 1 result ONLY in the following JSON format:

{
    "lookupList": [
        [column_name1, column_name2],  // column_name1 (parent) maps to column_name2 (child)
        [column_name3, column_name4],
        ...
    ]
}

OR

{
    "lookupList": "None"
}

Here is the data table's domain, description, and data column names:
    '''

    userFirstPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userFirstPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    columnList = list(dataframe.columns)
    userFirstPrompt += 'columns: '
    for column in columnList:
        userFirstPrompt += column + ','
    userFirstPrompt = userFirstPrompt.strip(',')
    if model != "api":
        firstRoundResult = chat_api(user_prompt=userFirstPrompt, provider="ollama", system_prompt=systemPrompt, format=schema1, temperature=0.1, model=model1)
    else:
        firstRoundResult = chat_api(user_prompt=userFirstPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.1, model=None)

    lookupColumn = firstRoundResult['lookupList']
    if lookupColumn == "None":
        return {"status": False, "lookupList": None}
    history = [
        {"role": "user", "content": userFirstPrompt},
        {"role": "assistant", "content": json.dumps(firstRoundResult)}
    ]

    class Phase2Result(BaseModel):
        lookupResult: Union[List[Dict[str, Any]], Literal["None"]]

    # Generate schema
    schema2 = Phase2Result.model_json_schema()

    userSecondPrompt = '''
Task Description – Phase 2:
Using the candidate lookup relationships from Phase 1, you will now receive value-level mapping statistics along with an initial lookupList. Your task is twofold:
1. Determine, based on the provided data, whether lookup relationship verification is required.
2. If you decide that verification is needed, review the provided lookupList and adjust it if necessary. **Note:** Every mapping relationship in the lookupList must be expressed with actual values from the data table.

Steps:

Step 1 – Relationship Evaluation:
  - Review the candidate lookup relationships from Phase 1 alongside the provided mapping statistics.
  - For each candidate, analyze the mapping statistics which include entries such as:
        {
            "parentValue": <value>,
            "childValueList": [
                { "value": <child_value>, "count": <occurrence_count> },
                ...
            ]
        }
  - Evaluate whether the value distributions and mapping patterns consistently reflect a clear semantic relationship.

Step 2 – Rule Generation and LookupList Adjustment:
  - Confirm that the observed mapping pattern for each candidate is either one-to-one or one-to-many.
  - Ensure that these mapping patterns reflect a robust, domain-supported hierarchical or reference relationship.
  - Construct definitive lookup rules that can act as strict data validation criteria (i.e., if the lookup rule is not met for a row, that row is flagged as invalid).
  - Adjust the provided lookupList if necessary. **Ensure that all mapping relationships in the lookupList specify concrete values from the data table.**

Return your Phase 2 result ONLY in the following JSON format:

{
    "lookupResult": [
        {
            "parentColumnName": string,
            "childColumnName": string,
            "lookupList": [
                {
                    "parentValue": <value>,
                    "childValueList": [<value1>, <value2>, ...]
                },
                ...
            ]
        },
        ...
    ]
}

OR

{
    "lookupResult": "None"
}

Important Reminders:
- Use only the actual column values from the provided data table when constructing mapping relationships in the lookupList.
- The lookup rules must strictly reflect the specific value-level mappings observed in the data.
- If there is no clear, domain-supported candidate lookup mapping or if the provided data does not justify lookup relationship verification, return "None".


    '''
    
    for lookupPair in lookupColumn:
        parentColumn = lookupPair[0]
        childColumn = lookupPair[1]
        if parentColumn in columnList and childColumn in columnList:
            lookupList = generate_lookup_List(dataframe[parentColumn], dataframe[childColumn])
            if lookupList:
                userSecondPrompt += f'parentColumnName: {parentColumn}, childColumnName: {childColumn}, lookupList: {lookupList}'
                userFirstPrompt += "\n\n"
        else:
            userSecondPrompt += f'parentColumnName: {parentColumn}, childColumnName: {childColumn}'
            userSecondPrompt += "**Not in the data table.**"
    if model != "api":
        llmResult = chat_api(user_prompt=userSecondPrompt, provider="ollama", system_prompt=systemPrompt, history=history, format=schema2, temperature=0.1, model=model2)
    else:
        llmResult = chat_api(user_prompt=userSecondPrompt, provider="api", system_prompt=systemPrompt, history=history, format="json", temperature=0.1, model=None)

    try:
        if llmResult['lookupResult'] == "None":
            return {"status": False, "lookupList": None}
        
        lookupReturnResult = []
        for item in llmResult['lookupResult']:
            if item["parentColumnName"] in columnList and item["childColumnName"] in columnList:
                lookupReturnResult.append(item)
    except:
        return {"status": False, "lookupList": None}
    if lookupReturnResult == []:
        return {"status": False, "lookupList": None}
    else:
        return {"status": True, "lookupList": lookupReturnResult}