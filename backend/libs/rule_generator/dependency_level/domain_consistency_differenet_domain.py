import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal

# Add upper-level directory to sys.path so shared modules resolve.
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def character_domain(dataList, columnName, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"

    systemPrompt = '''
You are a domain knowledge expert specializing in semantic data analysis. Your expertise includes:
- Interpreting contextual meanings across multiple domains.
- Identifying domain mismatches in datasets.
- Making accurate domain-specific judgments based on comprehensive knowledge.
    '''

    class DifferentDomainList(BaseModel):
        differentDomainList: Union[List[str], Literal["None"]]

    schema = DifferentDomainList.model_json_schema()

    userPrompt = '''
Task Description:
You are provided with a data column that includes a list of values, along with the overall dataset’s domain and description. Your objective is to analyze the column and identify values that semantically do not belong to the dominant domain—meaning they describe a different type of entity or affair from the majority. Do not flag differences merely based on alternative expressions. Also, if any value is null or empty, do not include it in your output.

Step 1: Column Name Analysis
- Interpret the semantic meaning of the column name.
- Determine the expected data domain based on the column name.
- Incorporate the overall dataset's domain and description to form a comprehensive understanding of the expected domain.
- Identify typical values associated with this domain.
- Consider standard naming conventions for the domain.

Step 2: Data Pattern Analysis
- Compare all values to identify common patterns and characteristics.
- Group similar items based on their intrinsic nature.
- Note any values that differ significantly in substance from the majority’s semantic meaning (not merely in expression).

Step 3: Domain Consistency Check
- Cross-reference the expectations from the column name with the observed data.
- Flag items that semantically do not match the expected domain—i.e., they describe a different category or type of activity.
- Do not flag values that are null or empty.

Step 4: Final Validation
- Internally verify your flagged items by clearly establishing the column’s dominant domain.
- For each flagged value, internally confirm and articulate why it does not belong to this domain.
- Exclude any value from the final output if your internal verification finds insufficient justification.
- Do not include any of this internal validation reasoning in your final returned result.

Return Value Rules:
- If clear domain mismatches are found (after internal validation), return a list of these values.
- If all values semantically belong to the dominant domain, or if potential mismatches are null/empty, return "None".

Return your result ONLY in the following JSON format (do not include any additional notes or explanations):

{
    "differentDomainList": [
        "value1",
        "value2",
        ...
    ]
}

OR

{
    "differentDomainList": "None"
}

Requirements:
1. Follow the step-by-step instructions exactly as outlined.
2. Return "None" if all values belong to the same semantic domain or if mismatches are solely null/empty.
3. Include only values that are clear, semantic domain mismatches and that have been validated internally.
4. Do not return any internal self-verification reasoning in the final output.
5. Use the exact JSON format specified.


    '''
    if len(dataList) > 2000:
        return {"status": False, "differentDomainList": None}
    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'column name:' + columnName + '\n\n column data: '
    userPrompt += str(list(dataList))
    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    if llmResult == "" or llmResult['differentDomainList'] == "None":
        return {"status": False, "differentDomainList": None}
    else:
        return {"status": True, "differentDomainList": llmResult['differentDomainList']}
