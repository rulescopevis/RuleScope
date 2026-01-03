import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal

# Ensure project root is included in the import search path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def numeric_range(staticDict, columnName, domainDescription, model):
    if model == None:
        model = "qwen2.5:72b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert range analyzer with comprehensive domain knowledge in geographic coordinates, time values, percentages, and other numeric measurements. Your role is to determine valid numeric boundaries by leveraging domain-specific constraints and insights.
    '''

    class RangeBoundary(BaseModel):
        start: float
        end: float
        startInclusive: bool
        endInclusive: bool

    class RangeConstraints(BaseModel):
        rangeList: Union[List[RangeBoundary], Literal["None"]]

    schema = RangeConstraints.model_json_schema()

    userPrompt = '''
Task Description:
Analyze the provided column information to determine valid numeric range boundaries using domain-specific knowledge. Prioritize semantic analysis based on the column name, data meaning, and the dataset’s domain description. Use statistical analysis only when no explicit domain-range constraints exist.

Steps:

Step 1 – Domain Identification and Knowledge Retrieval:
- Identify the data domain using the provided table domain and description.
- Retrieve all relevant domain-specific knowledge, including any standard numeric ranges for this type of data.

Step 2 – Range Determination:
- Analyze the column name and data semantics to check for any standard numeric range defined by your domain knowledge.
- If a standard range exists, directly assign it as the valid numeric boundary.

Step 3 – Semantic and Statistical Evaluation:
- If no domain-specific range is defined, combine semantic analysis with statistical indicators (e.g., value distributions) to derive a reasonable numeric range.
- Do not use raw min-max values without thorough evaluation. Only include a candidate range if both semantic context and statistical evidence support it.

Step 4 – Range Validation Exemption:
- If you determine that the column’s data does not require range validation (i.e., any numeric value is acceptable), return an exemption.

Return Format:
Return your result ONLY in the following JSON format (DO NOT include any additional explanations):

{
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

Or, if no numeric range constraints apply, return:

{
    "rangeList": "None"
}

CRITICAL REQUIREMENTS:
1. PRIORITIZE domain-specific knowledge and semantic analysis.
2. Use statistical analysis ONLY when no explicit domain-range is available.
3. NEVER use raw min-max values without thorough analysis.

    '''
    userPrompt += "data table domain: " + domainDescription['domain'] + "\n"
    userPrompt += "data table description: " + domainDescription['description'] + "\n\n"
    userPrompt += "Here is the column name and static info:"
    userPrompt += 'column name: ' + columnName
    userPrompt += "\n static info:\n"
    userPrompt += f" median: {str(staticDict['median'])}\n"
    userPrompt += f" mean: {str(staticDict['mean'])}\n"
    userPrompt += f" std: {str(staticDict['std'])}\n"
    userPrompt += f" skewness: {str(staticDict['skewness'])}\n"
    userPrompt += f" kurtosis: {str(staticDict['kurtosis'])}\n"
    userPrompt += f" q1: {str(staticDict['q1'])}\n"
    userPrompt += f" q3: {str(staticDict['q3'])}\n"
    userPrompt += f" p1: {str(staticDict['p1'])}\n"
    userPrompt += f" p5: {str(staticDict['p5'])}\n"
    userPrompt += f" p10: {str(staticDict['p10'])}\n"
    userPrompt += f" p90: {str(staticDict['p90'])}\n"
    userPrompt += f" p95: {str(staticDict['p95'])}\n"
    userPrompt += f" p99: {str(staticDict['p99'])}\n"
    userPrompt += f" mad: {str(staticDict['mad'])}\n"
    userPrompt += f" iqr: {str(staticDict['iqr'])}\n"
    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)
    numericRange = llmResult['rangeList']
    if numericRange == "None":
        return {"status": False, "numericRange": None}
    else:
        return {"status": True, "numericRange": numericRange}