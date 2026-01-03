import os
import sys

from pydantic import BaseModel, Field
from typing import List, Union, Literal

# Add the project root directory to the import search path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api
from rule_generator.dependency_level.calculate_multi_difference import calculate_multi_difference

def numeric_difference_multi(dataframe, domainDescription, model):
    if model == None:
        model1 = "qwen2.5:14b-instruct-q4_K_M"
        model2 = "qwen2.5:72b-instruct-q4_K_M"
    else:
        model1 = model
        model2 = model
    systemFindColumnPrompt = '''
You are an expert data analyst specializing in identifying multi-dimensional state relationships in data. Your core responsibility is to analyze the table's domain, its difference, and the semantic meaning of each column. Based on this information, determine which columns are so interdependent that difference validation must be performed on them together.

Key Expertise Areas:
1. Multi-dimensional coordinate systems (e.g., spatial, motion, color spaces)
2. Composite state transitions
3. Inseparable component relationships
4. State change analysis

Your goal is to identify only truly inseparable column groups for difference verification. If a column group must be validated as a unit because its individual components lose meaning when separated, include that group. Otherwise, return "None".
    '''

    class MultiDifferenceColumns(BaseModel):
        multiDifferenceList: Union[List[List[str]], Literal["None"]]

    schemaColumn = MultiDifferenceColumns.model_json_schema()

    userFindColumnPrompt = '''
Task Description:
You will be provided with the data table's domain and description along with the semantic information for each column. Your task is to identify groups of columns where difference validation must be performed together—for these groups, validating columns individually does not make sense.

Step 1 – Context and Semantic Evaluation:
   - Review the provided data table's domain and description.
   - Analyze the semantic meaning of each column to assess their interdependencies.
   - Determine which columns should be combined for difference verification based on their domain and semantic relationship.

Step 2 – Identification of Valid Component Groups:
   - Look for groups of columns that form inseparable, composite components.
   - Valid examples include:
       • Spatial coordinates (e.g., x, y, z)
       • Geolocation pairs (e.g., Latitude and Longitude)
       • Color space components (e.g., R, G, B or H, S, V)
       • Motion tracking points
       • Market state metrics
   - Validate that the complete component set is required and that difference checking is meaningless when columns are treated independently.

Step 3 – Answer Construction:
   - If valid column groups are identified, list them as arrays of column names.
   - If no inseparable groups exist, simply return "None".

Return your results ONLY in the following JSON format:

{
    "multiDifferenceList": [
        ["column1", "column2"],
        ["column3", "column4", "column5"]
    ]
}
OR
{
    "multiDifferenceList": "None"
}



    '''
    userFindColumnPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userFindColumnPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userFindColumnPrompt += 'columns: '
    for column in dataframe.columns:
        userFindColumnPrompt += column + ','
    userFindColumnPrompt = userFindColumnPrompt.strip(',')
    if model != "api":
        findColumnResult = chat_api(user_prompt=userFindColumnPrompt, provider="ollama", system_prompt=systemFindColumnPrompt, format=schemaColumn, temperature=0.1, model=model1)
    else:
        findColumnResult = chat_api(user_prompt=userFindColumnPrompt, provider="api", system_prompt=systemFindColumnPrompt, format="json", temperature=0.1, model=None)
    multiDifferenceList = findColumnResult['multiDifferenceList']
    systemCalculateDiffPrompt = '''
You are an expert data analyst specializing in time series monitoring and threshold optimization. Your core responsibilities include:
- Analyzing statistical patterns in time series data
- Determining optimal monitoring thresholds based on process stability
- Providing statistically justified constraint ranges that are operationally relevant

Your goal is to balance statistical evidence with domain expertise to define ranges that capture normal variations while excluding outliers. All differences must be treated as absolute values, and the range values must start above 0.
    '''

    class DifferenceRange(BaseModel):
        start: float = Field(gt=0)  # Must be greater than 0
        end: float = Field(gt=0)    # Must be greater than 0
        startInclusive: bool
        endInclusive: bool

    class DifferenceResult(BaseModel):
        differenceDict: DifferenceRange

    schemaDiff = DifferenceResult.model_json_schema()

    userDiffPrompt = '''
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
    if multiDifferenceList == "None":
        return {"status": False, "multiDifferenceList": None}
    else:
        initialMultiDifferenceList = []
        for item in multiDifferenceList:
            addFlag = True
            for column in item:
                if column not in list(dataframe.columns):
                    addFlag = False
                    break
            if addFlag:
                initialMultiDifferenceList.append(item)
        multiDifference = []
        for item in initialMultiDifferenceList:
            columnList = []
            for column in item:
                columnList.append(dataframe[column])
            calculateDict = calculate_multi_difference(columnList)
            userCalculateDiffPrompt = userDiffPrompt + 'columns: ' + str(item) + '\ndata static info dict: ' + str(calculateDict)
            if model != "api":
                calculateDiffResult = chat_api(user_prompt=userCalculateDiffPrompt, provider="ollama", system_prompt=systemCalculateDiffPrompt, format=schemaDiff, temperature=0.1, model=model2)
            else:
                calculateDiffResult = chat_api(user_prompt=userCalculateDiffPrompt, provider="api", system_prompt=systemCalculateDiffPrompt, format="json", temperature=0.1, model=None)
            multiDifference.append({"columns": item, "differenceDict": calculateDiffResult["differenceDict"]})
    
    finalMultiDifference = []
    for item in multiDifference:
        addFlag = True
        for column in item["columns"]:
            if column not in list(dataframe.columns):
                addFlag = False
                break
        if addFlag:
            finalMultiDifference.append(item)
    if finalMultiDifference == []:
        return {"status": False, "multiDifference": None}
    else:
        return {"status": True, "multiDifference": multiDifference}