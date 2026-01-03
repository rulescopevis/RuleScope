import pandas as pd
import signal
from contextlib import contextmanager

from pydantic import BaseModel
from typing import List, Union, Literal, Any, Dict

import os
import sys
    
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api
from rule_generator.dependency_level.generate_condition_list import generate_multiple_condition_list

def calculate_multiple_constraint_similarity(condition_data):
    """Compute average similarity for multi-condition constraints (0-100)."""
    if isinstance(condition_data, dict):
        condition_list = condition_data.get('conditionAndLogicList', [])
    else:
        condition_list = condition_data
        
    if not condition_list or len(condition_list) <= 1:
        return 0

    def calculate_equality_similarity(value1, value2):
        """Calculate similarity for two EqualityBased constraints."""
        if not value1 and not value2:
            return 100
        if not value1 or not value2:
            return 0
            
        set1 = set(str(x) if pd.isna(x) else x for x in value1)
        set2 = set(str(x) if pd.isna(x) else x for x in value2)
        denominator = min(len(set1), len(set2))
        common = set1 & set2
        return len(common) * 100 / denominator

    def calculate_range_similarity(range1, range2):
        """Calculate similarity for two RangeBased constraints."""
        if not range1 and not range2:
            return 100
        if not range1 or not range2:
            return 0
            
        overlap_start = max(range1['start'], range2['start'])
        overlap_end = min(range1['end'], range2['end'])
        
        if overlap_start > overlap_end:
            return 0
            
        overlap_length = overlap_end - overlap_start
        original_length = min(
            range1['end'] - range1['start'],
            range2['end'] - range2['start']
        )
        
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
                
            constraint_similarities = {}
            for col in condition1['constraintColumnValue'].keys():
                constraint1 = condition1['constraintColumnValue'][col]
                constraint2 = condition2['constraintColumnValue'][col]
                
                if isinstance(constraint1, dict) and 'start' in constraint1:
                    similarity = calculate_range_similarity(constraint1, constraint2)
                else:
                    similarity = calculate_equality_similarity(constraint1, constraint2)
                constraint_similarities[col] = similarity
            
            if constraint_similarities:
                max_similarity = max(constraint_similarities.values())
                condition_similarities.append(max_similarity)
        
        if condition_similarities:
            avg_similarity = sum(condition_similarities) / len(condition_similarities)
            total_similarity += avg_similarity
            count += 1

    return total_similarity / count if count > 0 else 0

def condition_logic_multiple(dataframe, tableDict, domainDescription, model):
    """Analyze multi-column condition and constraint relationships."""
    if model == None:
        model = "qwen2.5:72b-instruct-q4_K_M"
    columnSystemPrompt = '''
You are an expert data analyst specializing in identifying complex semantic relationships in data structures. With deep domain expertise and a strong grasp of business logic, your task is to analyze relationships among multiple columns in data tables. You must identify valid condition-constraint relationships based on semantic meaning, domain rules, and logical dependencies.

Key Points:
1. A "condition" is defined as one or a combination of columns whose specific value(s) or range(s) act as a trigger.
2. A "constraint" is defined as one or a combination of columns whose values are uniquely determined by the corresponding condition.
3. For a valid multi-column condition-constraint relationship, the columns must be evaluated as composites using an "AND" logic:
   - A composite condition consists of two or more condition columns that together define the triggering state.
   - A composite constraint consists of two or more constraint columns that together define the resulting outcome.
4. The relationship is valid if the composite condition uniquely determines the composite constraint, and at least one of the groups (condition or constraint) comprises two or more columns.
5. When the composite condition holds true (i.e., equals a specific value or falls within a defined range), it must uniquely determine the composite constraint.
    '''

    columnUserPrompt = '''
Task Description:
You will be provided with the data table's Domain, Description, and column details. Using this information and the semantic meaning of each column, your goal is to determine which columns require multi-column constraint and logic validation. In other words, identify valid condition-constraint relationships based on the table's domain and the underlying business logic.

Steps:

Step 1 – Understand Table Context:
   - Review the provided Table Domain and Description to capture the overall context and domain-specific rules.
   - Analyze each column's semantic meaning and determine which columns might be involved in conditional or constraint logic.

Step 2 – Examine Column Relationships:
   - Evaluate the provided column names (and sample data if available) to hypothesize potential condition and corresponding constraint columns.
   - Consider domain patterns such as multiple status indicators, hierarchical classifications, or complex business rules (e.g., workflows or role permissions) that may require composite validation.

Step 3 – Validate Condition-Constraint Relationships:
   - Ensure that any candidate relationship meets the criteria: a composite condition (columns combined with AND logic) should uniquely determine a composite constraint.
   - Confirm that at least one of the groups (either condition or constraint) consists of two or more columns.

Step 4 – Construct the Output:
   - Return the candidate multi-column condition-constraint relationships exactly in the JSON format shown below.
   - If no valid multiple condition-constraint relationship is identified, return "None".

Return Format:
Return your result ONLY in the following JSON format (do not include any extra notes or explanations):

{
    "conditionLogicColumnList": [
        {
            "conditionColumns": [<column1>, <column2>, ...],
            "constraintColumns": [<column1>, <column2>, ...]
        },
        ...
    ]
}

OR, if no valid relationship is found:

{
    "conditionLogicColumnList": "None"
}

Here is the table information:
    '''

    class ColumnDependency(BaseModel):
        conditionColumns: List[str]
        constraintColumns: List[str]

    class ColumnLogicResult(BaseModel):
        conditionLogicColumnList: Union[List[ColumnDependency], Literal["None"]]

    schemaColumns = ColumnLogicResult.model_json_schema()

    columnUserPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    columnUserPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    columnUserPrompt += '\ncolumns: ' + ', '.join(dataframe.columns)
    
    if model != "api":
        multipleConditionColumnResult = chat_api(
            provider="ollama",
            user_prompt=columnUserPrompt,
            system_prompt=columnSystemPrompt,
            format=schemaColumns,
            temperature=0.1,
            model=model
        )
    else:
        multipleConditionColumnResult = chat_api(
            provider="api",
            user_prompt=columnUserPrompt,
            system_prompt=columnSystemPrompt,
            format="json",
            temperature=0.1,
            model=None
        )

    if multipleConditionColumnResult['conditionLogicColumnList'] == 'None' or not multipleConditionColumnResult['conditionLogicColumnList']:
        return {"status": False, "conditionLogicColumnList": None}


    multipleConditionSystemPrompt = '''
You are an expert data analyst and rule engine specialist. Your mission is to validate complex composite condition-constraint mappings by integrating semantic clues with rigorous statistical analyses.

Your responsibilities include:
1. Validating data types, semantic patterns, and statistical distributions.
2. Determining if a unique, exclusive composite condition-constraint mapping exists using both semantic clues and statistical measures (P1, P5, P10, P90, P95, and P99).
3. For RangeBased mappings, critically assessing provided ranges against statistical boundaries to detect outliers or dirty data, then deriving and returning a robust range that reflects the true data distribution.
4. Ensuring that every unique composite condition (where condition columns are combined with AND logic) maps to one unique composite constraint (where constraint columns are combined with AND). A composite relationship must involve either:
   - Two or more condition columns that together determine the outcome, or
   - Two or more constraint columns that are together determined by the condition.
   (It is acceptable for both groups to be composite.)
5. For EqualityBased mappings, always return the literal keys "conditionValue" and "constraintValue" as lists.
6. Output your answer strictly in the JSON format specified below.

All outputs must strictly adhere to the given schema.
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

    multipleConditionUserPrompt = '''
Task Description:
Analyze the provided input and determine whether a strict, valid composite condition-constraint mapping exists. In this mapping, you will identify a composite condition—one or more condition columns combined with AND logic—that uniquely determines a composite constraint (one or more constraint columns combined with AND logic).

Steps:

Step 1 – Semantic Analysis:
   - Examine the provided column names and their semantic implications.
   - Hypothesize which columns can serve as condition columns and which can serve as constraint columns.
   - Determine if the composite condition is capable of uniquely determining the composite constraint.

Step 2 – Statistical Evaluation:
   - For RangeBased mappings, utilize the statistical percentiles (P1, P5, P10, P90, P95, and P99) to assess whether the provided range has been skewed by outliers or dirty data.
   - If necessary, derive and return a robust range that accurately reflects the underlying data distribution.

Step 3 – Validate Composite Exclusiveness:
   - Confirm that each unique composite condition (formed using AND logic across the condition columns) maps to one unique composite constraint (formed using AND logic across the constraint columns).
   - Reject the mapping if a composite condition maps to multiple distinct composite constraints or if the relationship appears to be partial.

Step 4 – Construct the Output:
   - For EqualityBased mappings, always output both "conditionValue" and "constraintValue" as lists—even if there is only a single element.
   - Adhere strictly to the JSON format specified below.

Return Format:
Return your result in the exact JSON format shown:

{
   "conditionLogicColumnDict": {
       "conditionColumns": ["<column name>", "<column name>", ...],
       "constraintColumns": ["<column name>", "<column name>", ...],
       "columnType": {
           "<column name>": "EqualityBased" or "RangeBased",
           ...
       },
       "conditionAndLogicList": [
           {
               "conditionColumnValue": [ 
                   { "<column name>": [value1, value2, ...] } 
                   // OR for RangeBased: { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } }
               ],
               "constraintColumnValue": [ 
                   { "<column name>": [value1, value2, ...] } 
                   // OR for RangeBased: { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } }
               ]
           }
           // Additional mappings, if any...
       ]
   }
}

If no valid composite mapping exists, return:

{
   "conditionLogicColumnDict": "None"
}

Input Format:
The input will follow this exact structure:

{
    "conditionColumns": ["<column name>", "<column name>", ...],
    "constraintColumns": ["<column name>", "<column name>", ...],
    "columnType": {
         "<column name>": "EqualityBased" or "RangeBased",
         ...
    },
    "conditionList": [
         {
              "conditionColumnValue": [
                     { "<column name>": [value1, value2, ...] }
                     // OR for RangeBased:
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
                     } }
              ],
              "constraintColumnValue": [
                     { "<column name>": [value1, value2, ...] }
                     // OR for RangeBased:
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
                     } }
              ]
         },
         // Additional condition mappings...
    ]
}

Summary:
Combine semantic insights with detailed statistical analysis (using P1, P5, P10, P90, P95, and P99) to validate the composite condition-constraint mapping. For RangeBased mappings, derive robust ranges that account for potential outlier influence. Ensure that every unique composite condition (formed using AND across condition columns) uniquely maps to its composite constraint (formed using AND across constraint columns). Output your answer strictly in the prescribed JSON format.


    '''
    multipleConditionLogicColumnList = []
    for item in multipleConditionColumnResult['conditionLogicColumnList']:
        if item == {'conditionColumns': ['eventName', 'eventSec'], 'constraintColumns': ['subEventName', 'subEventId']}:
            continue
        rangeBasedCount = 0
        equalityBasedCount = 0
        for column in item['conditionColumns']:
            if tableDict[column]['type'] == "numeric" or tableDict[column]['type'] == "datetime":
                rangeBasedCount += 1
            elif tableDict[column]['type'] == "character":
                equalityBasedCount += 1
        constraint_has_range = any(
            tableDict[column]['type'] in ["numeric", "datetime"] 
            for column in item['constraintColumns']
        )
        
        if rangeBasedCount > 1 or equalityBasedCount == 0 or (rangeBasedCount > 0 and constraint_has_range):
            continue
            
        conditionColumns = item['conditionColumns']
        constraintColumns = item['constraintColumns']
        typeDict = {
            'conditionColumnList': conditionColumns,
            'constraintColumnList': constraintColumns,
            'columnType': {columnName: tableDict[columnName]['type'] for columnName in conditionColumns + constraintColumns}
        }

        conditionList = execute_with_timeout(
            generate_multiple_condition_list,
            args=(dataframe, typeDict),
            timeout=180
        )
        
        if conditionList is None:
            conditionList = []
            continue
            
        try:
            similarity = calculate_multiple_constraint_similarity(conditionList)
        except Exception as e:
            continue
        
        if similarity > 90:
            continue
            
        conditionWithDataUserPrompt = multipleConditionUserPrompt + "condition column name: " + str(conditionColumns) + "constraint column name: " + str(constraintColumns) + "conditionValueList: " + str(conditionList)
        if model != "api":
            multipleConditionDict = chat_api(user_prompt=conditionWithDataUserPrompt, provider="ollama", system_prompt=multipleConditionSystemPrompt, format=schemaCondition, temperature=0.1, model=model, max_tokens=4096)
        else:
            multipleConditionDict = chat_api(user_prompt=conditionWithDataUserPrompt, provider="api", system_prompt=multipleConditionSystemPrompt, format="json", temperature=0.1, model=None, max_tokens=4096)
        if multipleConditionDict == '' or multipleConditionDict['conditionLogicColumnDict'] == 'None':
            continue
        else:
            multipleConditionLogicColumnList.append(multipleConditionDict['conditionLogicColumnDict'])
    finalMultipleConditionLogicColumnList = []
    if multipleConditionLogicColumnList == []:
        return {"status": False, "multipleConditionLogicColumnList": None}
    for item in multipleConditionLogicColumnList:
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
            finalMultipleConditionLogicColumnList.append(item)
    if finalMultipleConditionLogicColumnList == []:
        return {"status": False, "multipleConditionLogicColumnList": None}
    else:
        return {"status": True, "multipleConditionLogicColumnList": finalMultipleConditionLogicColumnList}

class TimeoutException(Exception):
    """Raised when an operation exceeds the allotted time limit."""

@contextmanager
def time_limit(seconds):
    """Context manager enforcing a time limit for a block."""
    import platform
    
    if platform.system() != 'Windows':
        def signal_handler(signum, frame):
            raise TimeoutException("Operation timed out")
        
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
    else:
        import threading
        import time
        
        timeout_event = threading.Event()
        
        def timeout_handler():
            timeout_event.set()
            current_frame = sys._getframe().f_back
            while current_frame and current_frame.f_code.co_name != 'time_limit':
                current_frame = current_frame.f_back
            if current_frame:
                current_frame.f_locals['_timed_out'] = True
        
        timer = threading.Timer(seconds, timeout_handler)
        timer.daemon = True
        timer.start()
        
        _timed_out = False
        
        try:
            start_time = time.time()
            yield
            if timeout_event.is_set() or _timed_out:
                elapsed = time.time() - start_time
                raise TimeoutException(f"Operation timed out after {elapsed:.1f} seconds (limit {seconds} seconds)")
        finally:
            timer.cancel()
            if timeout_event.is_set() or _timed_out:
                elapsed = time.time() - start_time
                raise TimeoutException(f"Operation timed out after {elapsed:.1f} seconds (limit {seconds} seconds)")

def _worker_process(func, args, kwargs, result_queue):
    try:
        result = func(*args, **kwargs)
        result_queue.put(result)
    except Exception as e:
        result_queue.put(Exception(f"Execution failed: {str(e)}"))

def execute_with_timeout(func, args=(), kwargs={}, timeout=180):
    """Execute a function in a subprocess with a timeout."""
    import multiprocessing
    
    result_queue = multiprocessing.Queue()
    
    process = multiprocessing.Process(
        target=_worker_process, 
        args=(func, args, kwargs, result_queue)
    )
    process.daemon = True

    process.start()
    
    process.join(timeout)
    
    if process.is_alive():
        process.terminate()
        process.join()
        return None
    
    if not result_queue.empty():
        result = result_queue.get()
        if isinstance(result, Exception):
            return None
        return result
    
    return None
