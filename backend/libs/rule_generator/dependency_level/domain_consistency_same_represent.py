import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal

# Add the project parent directory to the import search path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def character_same_represent(valueList, columnName, domainDescription, model):
    if model == None:
        model = "qwen2.5:32b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert entity resolution specialist with deep knowledge in entity matching and canonical form selection. You excel at identifying different representations of the same entity by leveraging semantic understanding, statistical patterns, and domain expertise.
    '''

    class EntityMapping(BaseModel):
        mainEntity: str
        sameEntityList: List[str]

    class SameEneityList(BaseModel):
        sameEntityList: Union[List[EntityMapping], Literal["None"]]
    

    schema = SameEneityList.model_json_schema()

    userPrompt = '''
Task Description:
You are provided with a single data column, including its name, corresponding data values with counts, and the overall dataset’s domain and description. Your goal is to analyze the column and identify different representations of the same entity. Determine the canonical (primary) form strictly based on statistical frequency and official standards. Only include entities that have multiple variations. If no entity variations are confidently identified, return "None".

Step 1: Data Analysis Requirements
- Examine the column name for semantic cues.
- Review the provided dataset's domain and description to accurately determine the semantic context of the current column.
- Analyze the data values and their occurrence counts to spot potential entity variants.
- Apply contextual and domain-specific understanding to guide entity resolution.

Step 2: Entity Resolution Standards
A. Core Identity Principle:
   - Entities are considered the same only if they are officially designated as equivalent with authoritative support and standard recognition.
B. Strict Requirements (ALL Must Be Met):
   1. Official Designation: Variants must be officially recognized as equivalent.
   2. Authority Support: There should be credible evidence from official documentation or recognized governing bodies.
   3. Standard Recognition: The variants must adhere to the formal standards in the domain.
C. Validation Process:
   - Verify that the equivalence is supported by official documentation and recognized authority.
   - Exclude matches based solely on substring similarity, similar spelling, or informal usage.
D. Examples:
   - Valid: "IBM" and "International Business Machines" (if officially registered)
   - Valid: "USA" and "United States of America" (if officially recognized)
   - Invalid: Unofficial abbreviations, informal short forms, or common nicknames.
E. Main Entity Selection:
   - The variant with the highest occurrence count becomes the main entity.
   - Ties should be broken by alphabetical order.

Step 3: Primary Form Selection
- Choose the canonical representation based solely on frequency and adherence to official standards.
- Only include entities that have confirmed variants; if there is no variation, exclude the entity from the result.

Step 4: Return Value Rules
- Return entities only if multiple representations (variants) are identified.
- If no entity variations are found, return "None".

Return your result ONLY in the following JSON format (do not include any additional notes or explanations):

{
    "sameEntityList": [
        {
            "mainEntity": "primary form of entity",
            "sameEntityList": ["variant1", "variant2", ...]
        },
        ...
    ]
}

OR, if no entity variations are identified:

{
    "sameEntityList": "None"
}


    '''

    if len(valueList) > 2000:
        return {"status": False, "sameEntityList": None}
    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'column name:' + columnName + '\n\n column data: '
    for valueDict in valueList:
        userPrompt += str(valueDict['value']) + '(' + str(valueDict['count']) + '), '
    if model != "api":
        llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.1, model=None)

    # differentDomainList = llmResult['differentDomainList']
    if llmResult == "" or llmResult == {} or llmResult["sameEntityList"] == "None" :
        return {"status": False, "sameEntityList": None}
    else:
        return {"status": True, "sameEntityList": llmResult['sameEntityList']}