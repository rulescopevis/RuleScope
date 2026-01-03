import pandas as pd

from pydantic import BaseModel
from typing import List, Union, Literal, Any, Dict

import os
import sys
    
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api
from rule_generator.dependency_level.generate_condition_list import generate_condition_list

def calculate_constraint_similarity(condition_data):
    """Compute average similarity across constraint conditions (0-100)."""
    condition_list = condition_data.get('conditionAndLogicList', [])
    if not condition_list or len(condition_list) <= 1:
        return 0

    def calculate_equality_similarity(value1, value2):
        """Calculate similarity for two EqualityBased constraints."""
        if not value1 or not value2:
            return 0
        set1 = set(value1.values()) if isinstance(value1, dict) else set(value1)
        set2 = set(value2.values()) if isinstance(value2, dict) else set(value2)
        set1 = {str(x) if pd.isna(x) else x for x in set1}
        set2 = {str(x) if pd.isna(x) else x for x in set2}
        common = set1 & set2
        return len(common) * 100 / len(set1)

    def calculate_range_similarity(range1, range2):
        """Calculate similarity for two RangeBased constraints."""
        if not range1 or not range2:
            return 0
            
        overlap_start = max(range1['start'], range2['start'])
        overlap_end = min(range1['end'], range2['end'])
        
        if overlap_start > overlap_end:
            return 0
            
        overlap_length = overlap_end - overlap_start
        original_length = range1['end'] - range1['start']
        
        if original_length == 0:
            return 100 if range1['start'] == range2['start'] and range1['end'] == range2['end'] else 0
            
        if range1['startInclusive'] != range2['startInclusive'] and overlap_start in (range1['start'], range2['start']):
            overlap_length -= 0.000001
        if range1['endInclusive'] != range2['endInclusive'] and overlap_end in (range1['end'], range2['end']):
            overlap_length -= 0.000001
            
        return max(0, (overlap_length * 100) / original_length)

    total_similarity = 0
    count = 0

    for i, condition1 in enumerate(condition_list):
        condition_similarities = []
        
        for j, condition2 in enumerate(condition_list):
            if i == j:
                continue
                
            constraint1 = condition1['constraintColumnValue']
            constraint2 = condition2['constraintColumnValue']
            
            constraint1_value = constraint1[list(constraint1.keys())[0]]
            constraint2_value = constraint2[list(constraint2.keys())[0]]
            
            if isinstance(constraint1_value, dict) and 'start' in constraint1_value:
                similarity = calculate_range_similarity(constraint1_value, constraint2_value)
            else:
                similarity = calculate_equality_similarity(constraint1_value, constraint2_value)
                
            condition_similarities.append(similarity)
        
        if condition_similarities:
            avg_similarity = sum(condition_similarities) / len(condition_similarities)
            total_similarity += avg_similarity
            count += 1

    return total_similarity / count if count > 0 else 0

def condition_logic_simple(dataframe, tableDict, domainDescription, model):
    if model == None:
        model1 = "qwen2.5:72b-instruct-q4_K_M"
        model2 = "qwen2.5:72b-instruct-q4_K_M"
    else:
        model1 = model
        model2 = model
    class ColumnDependency(BaseModel):
        conditionColumn: str
        constraintColumn: str

    class ColumnLogicResult(BaseModel):
        conditionLogicColumnList: Union[List[ColumnDependency], Literal["None"]]

    schemaColumns = ColumnLogicResult.model_json_schema()

    columnSystemPrompt = '''
You are an expert data analyst specializing in identifying semantic relationships in data structures. Your core responsibility is to analyze column relationships in data tables and identify valid conditional dependencies based on business logic and domain knowledge.

Your key capabilities include:
1. Understanding table semantics and the underlying business context.
2. Identifying logical dependencies between columns.
3. Recognizing domain-specific patterns and constraints.
4. Analyzing hierarchical and spatial relationships.

Your responses must strictly follow the given JSON format, focusing on valid, practical business relationships that can be implemented in real systems.
    '''

    columnUserPrompt = '''
Task Description:
Analyze the provided table columns and, based on the domain description, identify conditional logical dependencies. These dependencies represent business rules where one column's value determines or constrains another’s. If a row does not fulfill such a dependency, that row should be considered invalid.

Step 1 – Identify Patterns:
  - Review the provided business context and domain description.
  - Focus on these specific relationship patterns:
      • Column Dependencies:
           - Status → Required Fields
           - Type → Attributes
           - Classification → Value Ranges
      • Spatial Rules:
           - Location → Coordinates
           - Region → Geographical Bounds
           - Hierarchy → Spatial Constraints
      • Business Logic:
           - Status Workflows
           - Type Constraints
           - Role Permissions
           - Classification Rules
      • Value Constraints:
           - Category → Numeric Ranges
           - Status → Time Limits
           - Type → Quantity Bounds
  - Only include relationships that are practical, valid, and implementable.

Step 2 – Evaluate and Validate:
  - Confirm each candidate dependency is backed by clear business logic and domain knowledge.
  - Use the table's primary purpose and the domain description to justify each dependency.
  - Disregard dependencies that are abstract, ambiguous, or lack sufficient business justification.
  - Return "None" if no valid conditional dependencies exist.

Return your results ONLY in the following JSON format:

{
    "conditionLogicColumnList": [
        {
            "conditionColumn": <column>,
            "constraintColumn": <column>
        },
        ...
    ]
}

OR

{
    "conditionLogicColumnList": "None"
}

Here is the domain description and the table columns:
    '''
    columnUserPrompt += "domain:" + domainDescription["domain"] + "\n"
    columnUserPrompt += "domainDescription:" + domainDescription["description"] + "\n"
    columnList = list(dataframe.columns)
    columnUserPrompt += 'columns: '
    for column in columnList:
        columnUserPrompt += column + ','
    columnUserPrompt = columnUserPrompt.strip(',')
    if model != "api":
        conditionColumnResult = chat_api(user_prompt=columnUserPrompt, provider="ollama", system_prompt=columnSystemPrompt, format=schemaColumns, temperature=0.1, model=model1)
    else:
        conditionColumnResult = chat_api(user_prompt=columnUserPrompt, provider="api", system_prompt=columnSystemPrompt, format="json", temperature=0.1, model=None)
    if conditionColumnResult['conditionLogicColumnList'] == 'None':
        return {"status": False, "conditionLogicColumnList": None}

    conditionSystemPrompt = '''
You are an expert data analyst and rule engine specialist. Your tasks are as follows:
1. Validate data types, semantic patterns, and statistical distributions.
2. Determine if a unique, exclusive condition-constraint mapping exists by integrating semantic clues with statistical measures (P1, P5, P10, P90, P95, and P99).
3. For RangeBased mappings:
   - Do not simply return the provided range.
   - Compare its boundaries with the supplied statistics to detect the influence of outliers or dirty data.
   - Derive and return a robust range that reflects the true data distribution.
4. Ensure each unique condition value maps to one unique constraint.
5. For EqualityBased mappings, always return the literal keys "conditionValue" and "constraintValue" as lists.
6. Output your conclusion strictly in the JSON format specified below.

All outputs must adhere exactly to the defined schema.
    '''

    class RangeValue(BaseModel):
        start: float
        end: float 
        startInclusive: bool
        endInclusive: bool

    class ColumnValue(BaseModel):
        root: Union[List[Any], RangeValue]

    class ConditionValuePair(BaseModel):
        conditionColumnValue: List[Dict[str, Union[List[str], RangeValue]]]
        constraintColumnValue: List[Dict[str, Union[List[str], RangeValue]]]

    class ConditionLogicColumn(BaseModel):
        conditionColumns: List[str]
        constraintColumns: List[str]
        columnType: Dict[str, Literal["EqualityBased", "RangeBased"]]
        conditionAndLogicList: List[ConditionValuePair]

    class ValidationResult(BaseModel):
        conditionLogicColumnDict: Union[ConditionLogicColumn, Literal["None"]]

    schemaCondition = ValidationResult.model_json_schema()

    conditionUserPrompt = '''
Task Description:
Analyze the two provided columns to determine if a strict, valid condition-constraint mapping exists. Your analysis must combine a semantic evaluation of the column names with a rigorous statistical analysis using the percentiles (P1, P5, P10, P90, P95, and P99). Your goal is to assess whether a unique and exclusive mapping exists between condition values and constraint values. If the mapping is valid, construct and return the corresponding rules in the specified JSON format. Otherwise, return "None".

Step 1 – Semantic and Consistency Check:
   - Evaluate whether the provided column names imply a meaningful, exclusive condition-constraint relationship.
   - Invalidate the mapping if the semantic cues are weak or if most condition values produce nearly identical constraint values.

Step 2 – Exclusiveness Verification:
   - Confirm that each unique condition value maps to one—and only one—unique constraint.
   - Reject the mapping if any condition maps to multiple distinct constraints or if RangeBased intervals overlap excessively.

Step 3 – Statistical Integrity and Range Verification:
   - For RangeBased mappings, compare the provided range boundaries with the statistical metrics (P1, P5, P10, P90, P95, and P99).
   - Assess if the provided range is skewed by outliers or dirty data.
   - Derive and return a robust range that accurately reflects the true data distribution.

Step 4 – Output Construction:
   - For EqualityBased mappings, return keys "conditionValue" and "constraintValue" as lists, even if they contain only one element.
   - For RangeBased mappings, include the derived robust range in the output.
   - Construct the complete mapping result strictly according to the JSON schema provided.

Input Format:
The input follows this exact structure:
{
    "conditionColumns": ["<column name>"],
    "constraintColumns": ["<column name>"],
    "columnType": {
         "<column name>": "EqualityBased" or "RangeBased",
         "<column name>": "EqualityBased" or "RangeBased",
         ...
    },
    "conditionList": [
         {
             "conditionColumnValue": [
                 { "<column name>": [value1, value2, ...] }
                 OR
                 { "<column name>": { 
                        "value": { 
                            "start": number, 
                            "end": number, 
                            "startInclusive": boolean, 
                            "endInclusive": boolean 
                        },
                        "staticInfo": { 
                            "min": number,
                            "max": number,
                            "median": number,
                            "std": number,
                            "P1": number, 
                            "P5": number, 
                            "P10": number, 
                            "P90": number, 
                            "P95": number, 
                            "P99": number 
                        } 
                   } 
                 }
             ],
             "constraintColumnValue": [
                 { "<column name>": [value1, value2, ...] }
                 OR
                 { "<column name>": { 
                        "value": { 
                             "start": number, 
                             "end": number, 
                             "startInclusive": boolean, 
                             "endInclusive": boolean 
                        },
                        "staticInfo": { 
                             "min": number,
                             "max": number,
                             "median": number,
                             "std": number,
                             "P1": number, 
                             "P5": number, 
                             "P10": number, 
                             "P90": number, 
                             "P95": number, 
                             "P99": number 
                        }
                    }
                 }
             ]
         },
         ...
    ]
}

Required Output Format:
{
   "conditionLogicColumnDict": {
       "conditionColumns": ["<column name>"],
       "constraintColumns": ["<column name>"],
       "columnType": {
            "<column name>": "EqualityBased" or "RangeBased",
            ...
       },
       "conditionAndLogicList": [
           {
               "conditionColumnValue": [ { "<column name>": [value1, value2, ...] } ]
               // OR for RangeBased: [ { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } } ],
               "constraintColumnValue": [ { "<column name>": [value1, value2, ...] } ]
               // OR for RangeBased: [ { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } } ]
           }
           // Additional mappings...
       ]
   }
}

If no valid mapping exists, return:

{
   "conditionLogicColumnDict": "None"
}


    '''
    
    conditionLogicColumnList = []
    firstRoundList = []
    for item in conditionColumnResult['conditionLogicColumnList']:
        if item['conditionColumn'] in list(dataframe.columns) and item['constraintColumn'] in list(dataframe.columns):
            firstRoundList.append(item)
    for item in firstRoundList:
        conditionColumn = item['conditionColumn']
        constraintColumn = item['constraintColumn']
        if tableDict[conditionColumn]['type'] == 'character' or tableDict[constraintColumn]['type'] == 'character':
            typeDict = {conditionColumn: tableDict[conditionColumn]['type'], constraintColumn: tableDict[constraintColumn]['type']}
            conditionList = generate_condition_list(dataframe[conditionColumn], dataframe[constraintColumn], typeDict)
        else:
            continue
        
        if conditionList == []:
            continue
            
        similarity = calculate_constraint_similarity(conditionList)
        conditionWithDataUserPrompt = conditionUserPrompt + "condition column name: " + conditionColumn + "constraint column name: " + constraintColumn + "conditionValueList: " + str(conditionList)
        if model != "api":
            conditionDict = chat_api(user_prompt=conditionWithDataUserPrompt, provider="ollama", system_prompt=conditionSystemPrompt, format=schemaCondition, temperature=0.1, model=model2)
        else:
            conditionDict = chat_api(user_prompt=conditionWithDataUserPrompt, provider="api", system_prompt=conditionSystemPrompt, format="json", temperature=0.1, model=None)
        if conditionDict == "" or conditionDict['conditionLogicColumnDict'] == 'None':
            continue
        else:
            conditionLogicColumnList.append(conditionDict['conditionLogicColumnDict'])
    
    finalConditionLogicColumnList = []
    if conditionLogicColumnList == []:
        return {"status": False, "conditionLogicColumnList": None}
    for item in conditionLogicColumnList:
        addFlag = True
        for column in item["conditionColumns"]:
            if column not in list(dataframe.columns):
                addFlag = False
                break
        for column in item["constraintColumns"]:
            if column not in list(dataframe.columns):
                addFlag = False
                break
        if addFlag:
            finalConditionLogicColumnList.append(item)

    if finalConditionLogicColumnList == []:
        return {"status": False, "conditionLogicColumnList": None}
    else:
        return {"status": True, "conditionLogicColumnList": finalConditionLogicColumnList}