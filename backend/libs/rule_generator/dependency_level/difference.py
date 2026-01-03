import numpy as np
import os
import sys

from pydantic import BaseModel
from typing import Union, Literal

# Ensure the project root is on the import search path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def manage_list(input_list):
    null_count = sum(1 for x in input_list if x is None)
    null_ratio = null_count / len(input_list)

    if null_ratio > 0.1:
        return {"status": False}

    return {"status": True, "list": [x for x in input_list if x is not None]}

def format_statistics(data, prefix):
    """Format statistical information output"""
    stats = {
        'min': np.min(data),
        'max': np.max(data),
        'median': np.median(data),
        'mean': np.mean(data),
        'std': np.std(data),
        'Q1': np.percentile(data, 25),
        'Q3': np.percentile(data, 75),
        'P1': np.percentile(data, 1),
        'P5': np.percentile(data, 5),
        'P10': np.percentile(data, 10),
        'P90': np.percentile(data, 90),
        'P95': np.percentile(data, 95),
        'P99': np.percentile(data, 99)
    }
    
    return f"""{prefix} static info:
    Min: {stats['min']:.4f}
    Max: {stats['max']:.4f}
    Median: {stats['median']:.4f}
    Mean: {stats['mean']:.4f}
    Std: {stats['std']:.4f}
    Q1 (25%): {stats['Q1']:.4f}
    Q3 (75%): {stats['Q3']:.4f}
    P1: {stats['P1']:.4f}
    P5: {stats['P5']:.4f}
    P10: {stats['P10']:.4f}
    P90: {stats['P90']:.4f}
    P95: {stats['P95']:.4f}
    P99: {stats['P99']:.4f}
    """

def numeric_difference(differenceList, relativeDifferenceList, columnName, model):
    if model == None:
        model = "qwen2.5:7b-instruct-q4_K_M"
    differenceListStatus = manage_list(differenceList)
    if not differenceListStatus["status"]:
        return {"status": False, "numericDifference": None}
    difference = differenceListStatus["list"]
    relativeDifferenceListStatus = manage_list(relativeDifferenceList)
    if not relativeDifferenceListStatus["status"]:
        return {"status": False, "numericDifference": None}
    relativeDifference = relativeDifferenceListStatus["list"]
    systemPrompt = '''
You are an expert data analyst specializing in time series monitoring and threshold optimization. Your core responsibilities include:
- Analyzing statistical patterns in time series data
- Determining optimal monitoring thresholds based on process stability
- Providing statistically justified constraint ranges that are operationally relevant

Your current objective is to identify the stable interval where most data changes (differences) occur. Your analysis should focus on generating a difference rule that captures the natural range of changes that appear reliably and consistently within a narrow interval.
    '''

    class RangeConstraint(BaseModel):
        start: float
        end: float
        startInclusive: bool
        endInclusive: bool

    class DifferenceDict(BaseModel):
        difference: RangeConstraint
        relativeDifference: RangeConstraint

    class OptimizationResult(BaseModel):
        differenceDict: Union[DifferenceDict, Literal["None"]]

    schema = OptimizationResult.model_json_schema()

    userPrompt = '''
Task Description:
Analyze the provided statistical data to determine the interval in which the majority of data differences are concentrated. In other words, if most values are stable and lie within a narrow range, you should generate a difference rule with boundaries that fall inside this interval.

Steps:

Step 1 – Evaluate Data Stability for Difference Analysis:
  - Assess the statistical distribution of the differences.
  - Identify whether most data changes are relatively stable and concentrated within a specific interval.
    * For example, if over 80% of the differences lie within one narrow range, this indicates a stable behavior.
  - If the data is too stable (e.g., high percentiles near zero) or is widely scattered, reconsider applying a strict threshold rule.

Step 2 – Determine the Difference Interval:
  - Based on the statistical data (percentiles, mean, median, standard deviation, min, and max), derive the narrow interval that encompasses the primary clustering of differences.
  - Ensure the generated difference rule falls exactly within this interval.
  - The rule should accurately represent the natural, stable variation range observed in your statistical analysis.

Return Format:
Return your result ONLY in the following JSON format:

{
    "differenceDict": {
        "difference": {
            "start": <number>,          // Lower bound of the concentrated difference interval
            "end": <number>,            // Upper bound of the concentrated difference interval
            "startInclusive": <boolean>,// Whether the lower bound is included
            "endInclusive": <boolean>   // Whether the upper bound is included
        },
        "relativeDifference": {
            "start": <number>,          // Lower bound for the relative difference (similar analysis applies)
            "end": <number>,            // Upper bound for the relative difference
            "startInclusive": <boolean>,
            "endInclusive": <boolean>
        }
    }
}

OR, if your analysis determines that generating a constraint is inappropriate (e.g., differences are too stable or too scattered):

{
    "differenceDict": "None"
}

Statistical Input Context:
- You are provided with statistical metrics such as min, max, mean, median, standard deviation, and various percentiles for the differences.
- Your focus is to locate the narrow interval where the majority of differences fall, and use this interval to generate the difference rule.

Now, here is the column name and the statistical data:
    '''
    userPrompt += 'column name: ' + columnName + '\n'
    userPrompt += format_statistics(difference, "difference") + '\n'
    userPrompt += format_statistics(relativeDifference, "relative difference")
    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    differenceDict = llmResult['differenceDict']
    if differenceDict == "None":
        return {"status": False, "numericDifference": None}
    else:
        return {"status": True, "numericDifference": differenceDict}