from pydantic import BaseModel
from typing import List, Union, Literal, Dict
from enum import Enum

import os
import sys

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def refine_NL(originalValidationRule, naturalLanguage, model=None):
    """
    Adjusts the original validation rule based on the provided natural language description.

    Args:
        originalValidationRule: Original validation rule.
        naturalLanguage: Natural language description.
    Returns:
        refinedValidationRule: Updated validation rule.
    """

    if model != "api":
        model = "qwen2.5:32b-instruct-q4_K_M"

    ruleDescription = ''
    ruleFormat = ''

    if originalValidationRule["ruleType"] == "Missing":
        ruleDescription = "Checks for missing or anomalous data, encompassing both standard missing values (null values, np.nan) and domain-specific indicators (such as using -1 to denote missing value in sales volume datasets)."

        ruleFormat = '''
        refineResult: {
            "missingDetectFlag": True/False,
            "specialMissingValueList": ["special_value1", "special_value2"]
        }
        '''

        class MissingValueFlagList(BaseModel):
            missingValueFlag: bool
            specialMissingValueList: List[str]
        
        class RefineResult(BaseModel):
            refineResult: MissingValueFlagList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Duplicate":
        ruleDescription = "Checks for duplicate values in a column"

        ruleFormat = '''
        refineResult: {
            "duplicateDetectFlag": True/False,
        }
        '''

        class DuplicateDetectFlag(BaseModel):
            duplicateDetectFlag: bool
        
        class RefineResult(BaseModel):
            refineResult: DuplicateDetectFlag

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Format":
        ruleDescription = (
            "Checks for values in a column that are in a specified format. "
            "Return the regex patterns exactly as stated in the natural language; do not simplify, rewrite, or drop escapes."
        )

        ruleFormat = '''
        refineResult: {
            "format": ["regex1", "regex2", ...]
        }
        '''

        class Format(BaseModel):
            format: List[str]

        class RefineResult(BaseModel):
            refineResult: Format

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Type":
        ruleDescription = (
            "Checks or assigns the declared data type of a column."
            " Supported types: character, numeric, datetime."
            " Use the type explicitly inferred from the NL description."
        )

        ruleFormat = '''
        refineResult: {
            "type": "character" | "numeric" | "datetime"
        }
        '''

        class DeclaredType(BaseModel):
            type: Literal["character", "numeric", "datetime"]

        class RefineResult(BaseModel):
            refineResult: DeclaredType

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "DifferentDomain":
        # Stress that we always need a non-empty list when NL gives examples.
        ruleDescription = (
            "Checks for values in a column that belong to different domains."
            " If the natural language lists examples (e.g., 'Mars, Atlantis'),"
            " place all of them into differentDomainList as strings and do not leave it empty."
        )

        ruleFormat = '''
        refineResult: {
            "differentDomainList": [
                "value1",    // Values from different domains; use all examples from NL
                "value2"
            ]
        }
        '''

        class DifferentDomainList(BaseModel):
            differentDomainList: List[str]

        class RefineResult(BaseModel):
            refineResult: DifferentDomainList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "SameEntity":
        # Clarify direction: the value after "as the same entity as" is the main entity; other mentioned names go into sameEntityList.
        ruleDescription = (
            "Checks for values in a column that are different representations of the same entity."
            " Treat the name that follows 'as the same entity as <MAIN>' as mainEntity,"
            " and put all other mentioned names into sameEntityList."
            " Do not swap the main entity and its variants; preserve the string forms from NL."
        )

        ruleFormat = '''
        refineResult: {
        "sameEntityList": [
            {
                "mainEntity": "primary form of entity (the target mentioned after 'as the same entity as')",
                "sameEntityList": ["variant1", "variant2", ...] // all other names mentioned in NL
            },
            ...
        ]
        }
        '''

        class EntityMapping(BaseModel):
            mainEntity: str
            sameEntityList: List[str]

        class SameEntityList(BaseModel):
            sameEntityList: List[EntityMapping]

        class RefineResult(BaseModel):
            refineResult: SameEntityList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "ComputationalRelation":
        ruleDescription = (
            "Identifies computational/derived relationships across columns."
            " Return one or more formulas where variableList keeps operands in the order expressed in NL"
            " (all columns from columnsList plus any numeric constants), and operationList aligns positionally"
            " with variableList: len(operationList) = len(variableList) - 1 and the last operator is '='."
            " Place the result column last in variableList. Do not introduce columns outside columnsList;"
            " numeric constants are allowed."
        )

        ruleFormat = '''
        refineResult: {
            "formulaList": [
                {
                    "variableList": ["operand1", "operand2", ..., "result"],
                    "operationList": ["+"|"-"|"*"|"/", ... , "="]
                    // operationList length must be variableList length minus 1; last operator is '='
                },
                ...
            ]
        }
        '''

        class Formula(BaseModel):
            variableList: List[str]
            operationList: List[str]

        class FormulaList(BaseModel):
            formulaList: Union[List[Formula], Literal["None"]]

        class RefineResult(BaseModel):
            refineResult: FormulaList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Sequence":
        ruleDescription = "Examines transitions between consecutive data following sequential relations"

        ruleFormat = '''
        {
            refineResult: {
                "value": "value1", # Current value
                "allowed_next": ["value2", "value3"] # Allowed next values
            }
        }
        '''

        class SequenceRule(BaseModel):
            value: str
            allowed_next: List[str]

        class RefineResult(BaseModel):
            refineResult: SequenceRule

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Range":
        ruleDescription = "Checks for values in a column that are within a specified range"

        ruleFormat = '''
        refineResult: {
            "rangeList": [
                {
                "start": min_value,
                "end": max_value,
                "startInclusive": true_or_false,
                "endInclusive": true_or_false
                },
                ...
            ]
        }
        '''

        class RangeBoundary(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class RangeList(BaseModel):
            rangeList: List[RangeBoundary]

        class RefineResult(BaseModel):
            refineResult: RangeList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Statistical":
        ruleDescription = "Checks for outlier ranges in a column, similar to range but specific to outlier detection."

        ruleFormat = '''
        refineResult: {
            "outlierRange": {
                "start": number,
                "end": number,
                "startInclusive": boolean,
                "endInclusive": boolean
            }
        }
        '''

        class OutlierRange(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class OutlierWrapper(BaseModel):
            outlierRange: OutlierRange

        class RefineResult(BaseModel):
            refineResult: OutlierWrapper

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Difference":
        ruleDescription = "Checks for values in a column that the difference between adjacent data is within a specified range"

        ruleFormat = '''
        refineResult: {
            "start": min_value,
            "end": max_value,
            "startInclusive": true_or_false,
            "endInclusive": true_or_false
        }
        '''

        class DifferenceBoundary(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class Difference(BaseModel):
            difference: DifferenceBoundary

        class RefineResult(BaseModel):
            refineResult: DifferenceBoundary

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "RelativeDifference":
        ruleDescription = "Checks for values in a column that the relative difference between adjacent data is within a specified range"

        ruleFormat = '''
        refineResult: {
            "relativeDifference": { 
                "start": min_value,
                "end": max_value,
                "startInclusive": true_or_false,
                "endInclusive": true_or_false
            }
        }
        '''

        class RelativeDifferenceBoundary(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class RelativeDifference(BaseModel):
            relativeDifference: RelativeDifferenceBoundary

        class RefineResult(BaseModel):
            refineResult: RelativeDifference

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "DateFormat":
        ruleDescription = (
            "Checks for values in a column that are in a specified date format. "
            "Return the exact strftime pattern from the natural language (e.g., %Y-%m-%d %H:%M:%S); do not use placeholders like 'date_format'."
        )

        ruleFormat = '''
        refineResult: {
            "refinePattern": "date_format"
        }
        '''

        class RefinePattern(BaseModel):
            refinePattern: str

        class RefineResult(BaseModel):
            refineResult: RefinePattern

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Order":
        ruleDescription = "Checks ordering conditions across up to three columns with specified sort directions."

        ruleFormat = '''
        refineResult: {
            "orderCondition": {
                "firstOrderColumn": "col1",
                "firstOrderType": "Asc" | "Desc",
                "secondOrderColumn": "col2",
                "secondOrderType": "Asc" | "Desc",
                "thirdOrderColumn": "col3",
                "thirdOrderType": "Asc" | "Desc",
                "dateColumns": ["colX", ...]
            }
        }
        '''

        class OrderCondition(BaseModel):
            firstOrderColumn: str
            firstOrderType: Literal["Asc", "Desc"]
            secondOrderColumn: str
            secondOrderType: Literal["Asc", "Desc"]
            thirdOrderColumn: str
            thirdOrderType: Literal["Asc", "Desc"]
            dateColumns: List[str] = []

        class OrderWrapper(BaseModel):
            orderCondition: OrderCondition

        class RefineResult(BaseModel):
            refineResult: OrderWrapper

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Compare":
        ruleDescription = "Checks for the magnitude of values between two columns"

        ruleFormat = '''
        refineResult: {
            "numericCompareDict":
            {
                "column1": "column_name1",
                "column2": "column_name2",
                "compareRelation": "relation_type"  // larger, larger_equal, equal, smaller, smaller_equal, not_equal
                // column1 compareRelation column2
            }
        }
        '''

        class CompareRelationType(str, Enum):
            LARGER = "larger"
            LARGER_EQUAL = "larger_equal"
            EQUAL = "equal"
            SMALLER = "smaller"
            SMALLER_EQUAL = "smaller_equal"
            NOT_EQUAL = "not_equal"

        class CompareRelation(BaseModel):
            column1: str
            column2: str
            compareRelation: CompareRelationType

        class NumericCompareDict(BaseModel):
            numericCompareDict: Dict[str, CompareRelation]

        class RefineResult(BaseModel):
            refineResult: NumericCompareDict

        schema = RefineResult.model_json_schema()\
        
    elif originalValidationRule["ruleType"] == "Substring":
        ruleDescription = "Checks for substring relationship between two columns"

        ruleFormat = '''
        refineResult: {
            "substringList": {
            "childColumn": "column_name1",
            "parentColumn": "column_name2"  // childColumn is substring of parentColumn
            }
        }
        '''

        class Substring(BaseModel):
            childColumn: str
            parentColumn: str

        class SubstringList(BaseModel):
            substringList: List[Substring]

        class RefineResult(BaseModel):
            refineResult: SubstringList

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Lookup":
        ruleDescription = "Checks for mappings between columns, including both value-based dependencies where one value determines another"

        ruleFormat = '''
        refineResult: {
            "parentColumnName": "parent",
            "childColumnName": "child",
            "lookupList": [
                {
                    "parentValue": "A",
                    "childValueList": ["x", "y"]
                }
            ]
        }
        '''

        class LookupEntry(BaseModel):
            parentValue: str
            childValueList: List[str]

        class LookupPayload(BaseModel):
            parentColumnName: str
            childColumnName: str
            lookupList: List[LookupEntry]

        class RefineResult(BaseModel):
            refineResult: LookupPayload

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "Logical and condition":
        # Inclusive-by-default guidance avoids missing bounds when NL omits explicit inclusivity.
        ruleDescription = (
            "Checks for logical and condition between two columns."
            " Treat numeric ranges as inclusive on both ends (startInclusive=true, endInclusive=true)"
            " unless the natural language explicitly says exclusive/strictly/greater than/less than."
            " If text shows parentheses like (a, b), still set both inclusive unless the wording says otherwise."
        )

        ruleFormat = '''
        refineResult: {
        "conditionLogicColumnDict": {
            "conditionColumns": ["<column name>"],
            "constraintColumns": ["<column name>"],
            "columnType": {
                "<column name>": "EqualityBased" or "RangeBased",
                ...
            },
            "conditionAndLogicList": [
                {
                    "conditionColumnValue": [ { "<column name>": [value1] } ]
                    // OR for RangeBased: [ { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } } ],
                    "constraintColumnValue": [ { "<column name>": [value1, value2, ...] } ]
                    // OR for RangeBased: [ { "<column name>": { "start": number, "end": number, "startInclusive": boolean, "endInclusive": boolean } } ]
                }
            ]
        }
        // For any numeric range, set startInclusive=true and endInclusive=true unless NL explicitly says exclusive/strict/greater than/less than.
        // Parentheses like (a, b) are still inclusive unless the text explicitly says otherwise.
        '''

        class RangeValue(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class ConditionValuePair(BaseModel):
            conditionColumnValue: List[Dict[str, Union[List[str], RangeValue]]]
            constraintColumnValue: List[Dict[str, Union[List[str], RangeValue]]]

        class ConditionLogicColumn(BaseModel):
            conditionColumns: List[str]
            constraintColumns: List[str]
            columnType: Dict[str, Literal["EqualityBased", "RangeBased"]]
            conditionAndLogicList: List[ConditionValuePair]

        class RefineResult(BaseModel):
            refineResult: ConditionLogicColumn

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "MultiDifference":
        ruleDescription = "Checks distances between data points across multiple columns"

        ruleFormat = '''
        refineResult: {
            "differenceDict": {
                "start": number,           // Minimum valid difference, must be > 0
                "end": number,             // Maximum valid difference
                "startInclusive": boolean, // Include start value
                "endInclusive": boolean    // Include end value
            }
        }
        '''

        class DifferenceBoundary(BaseModel):
            start: float
            end: float
            startInclusive: bool
            endInclusive: bool

        class DifferenceDict(BaseModel):
            differenceDict: DifferenceBoundary
        
        class RefineResult(BaseModel):
            refineResult: DifferenceDict

        schema = RefineResult.model_json_schema()

    elif originalValidationRule["ruleType"] == "MultiDuplicate":
        ruleDescription = "Checks for duplicate values across multiple columns"

        ruleFormat = '''
        {
            refineResult: {
                "duplicateList": [
                    ["<column name>", "<column name>"],
                    ...
                ]
            }
        }
        '''

        class DuplicateList(BaseModel):
            duplicateList: List[List[str]]

        class RefineResult(BaseModel):
            refineResult: DuplicateList

        schema = RefineResult.model_json_schema()

    systemPrompt = '''
You are an expert in modifying data validation rules. Your task is to analyze a provided natural language description and an existing validation rule, then update the validation rule accordingly.
    '''

    userPrompt = '''
Based on the provided natural language description, modify the existing data validation rules as necessary. Perform the following steps:

1. Rule Type (ruleType): Describe the type of validation rule that is being modified.
2. Rule Description (ruleDescription): Describe the purpose and logic of the validation rule.
3. Columns List (columnsList): Indicate the columns that this rule applies to.
4. Original Validation Rule (OriginalValidationRule): Reference the original validation rule provided as input.
5. Rule Return Format (ruleReturnFormat): Specify the format in which the validation rule returns its result.
6. Natural Language (naturalLanguage): Use the provided natural language description as the driving blueprint for these modifications.


    '''
    returnJsonFormt = '''
    The updated validation rule should be returned in the following JSON format:
    '''
    userPrompt += "Rule Type: " + originalValidationRule["ruleType"] + "\n"
    userPrompt += "Rule Description: " + ruleDescription + "\n"
    userPrompt += "Columns List: " + str(originalValidationRule["columnsList"]) + "\n"
    userPrompt += "Original Validation Rule: " + str(originalValidationRule["validationRule"]) + "\n"
    userPrompt += "Rule Return Format: " + ruleFormat + "\n"
    userPrompt += "Natural Language: " + naturalLanguage + "\n"
    systemPrompt += "The updated validation rule should be returned in the following JSON format: \n```json\n" + ruleFormat + "\n```\n"
    userPrompt += "The updated validation rule should be returned in the following JSON format: \n```json\n" + ruleFormat + "\n```\n"

    # refinedValidationRule = ollama_api(user_prompt=userPrompt, system_prompt=systemPrompt, format=schema, temperature=0.1, model="qwen2.5:14b-instruct-q4_K_M")

    if model != "api":
        refinedValidationRule = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        refinedValidationRule = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    # Defensive extraction to avoid KeyError when model omits expected keys.
    refine_payload = refinedValidationRule.get("refineResult") if isinstance(refinedValidationRule, dict) else None
    if not isinstance(refine_payload, dict):
        return {"refineStatus": False, "refineResult": None}

    if originalValidationRule["ruleType"] == "Logical and condition":
        # Accept either a direct conditionAndLogicList or a wrapped conditionLogicColumnDict
        if "conditionLogicColumnDict" in refine_payload and isinstance(refine_payload["conditionLogicColumnDict"], dict):
            refineResult = refine_payload["conditionLogicColumnDict"].get("conditionAndLogicList") or refine_payload["conditionLogicColumnDict"]
        elif "conditionAndLogicList" in refine_payload:
            refineResult = refine_payload["conditionAndLogicList"]
        else:
            return {"refineStatus": False, "refineResult": None}
    elif originalValidationRule["ruleType"] == "Lookup":
        # Normalize lookup payload to expected shape and flatten child values
        vr = originalValidationRule.get("validationRule", {}) or {}
        parent_col = refine_payload.get("parentColumnName") or vr.get("parentColumnName") or ""
        child_col = refine_payload.get("childColumnName") or vr.get("childColumnName") or ""
        lookup_list = refine_payload.get("lookupList") or []

        normalized_lookup = []
        for entry in lookup_list if isinstance(lookup_list, list) else []:
            if not isinstance(entry, dict):
                continue
            parent_val = entry.get("parentValue")
            raw_children = entry.get("childValueList") or []
            child_values: list[str] = []
            for cv in raw_children if isinstance(raw_children, list) else []:
                if isinstance(cv, dict) and "value" in cv:
                    val = cv.get("value")
                else:
                    val = cv
                if val is None:
                    continue
                sval = str(val)
                if sval not in child_values:
                    child_values.append(sval)
            if parent_val is not None:
                normalized_lookup.append({
                    "parentValue": str(parent_val),
                    "childValueList": child_values,
                })

        refineResult = {
            "parentColumnName": parent_col,
            "childColumnName": child_col,
            "lookupList": normalized_lookup,
        }
    else:
        refineResult = refine_payload

    return {"refineStatus": True,
            "refineDict": {
                "updateRules": [{
                    "column": originalValidationRule["columnsList"],
                    "type": originalValidationRule["ruleType"],
                    "originalRule": originalValidationRule["validationRule"],
                    "refineRule": refineResult
                }]
            }
    }
