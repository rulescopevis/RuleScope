import os
import sys

from pydantic import BaseModel
from typing import List, Union, Literal

# Ensure the project root is on the import path
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def character_sequence(sequenceList, columnName, domainDescription, model):
    if model is None:
        model = "qwen2.5:72b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert business process analyst with deep domain knowledge across multiple industries.
You excel at evaluating event sequences, logical process flows, and ensuring business rule compliance by integrating semantic analysis with statistical evidence.
    '''

    class StateTransition(BaseModel):
        value: str
        allowed_next: List[str]

    class ProcessSequence(BaseModel):
        sequence: Union[List[StateTransition], Literal["None"]]

    schema = ProcessSequence.model_json_schema()

    userPrompt = '''
Task Description:
Your task is to detect, validate, and output the natural flow (sequence) of events in a dataset column that is expected to represent process states or action transitions. Use semantic analysis to determine whether sequence analysis is necessary. For example, if the events (such as status or action changes) are expected to follow a natural order, then any deviation may indicate an anomaly. However, if the column’s data does not exhibit an inherent sequential order, you must return "None". Use the overall dataset's domain and description to enhance your semantic understanding.

**Strict Applicability Check:**
- Column Name: Analyze whether the column name implies sequential, temporal, or process-driven data (e.g., "status", "stage", "event"). If it’s generic (e.g., "ID", "code"), combine this with the actual data values.
- Data Semantics: Using the overall dataset’s domain and description, assess the natural meaning of each event value. If the values clearly represent process states or action transitions that follow a logical progression, then sequence analysis is warranted. If not, return "None".
- Necessity: Based solely on semantic evaluation, only perform sequence analysis if the events inherently indicate a natural order. Do not force a sequence rule just because a list of values is provided.

Analysis Process:
Step 1: Determine Applicability and Context
- Evaluate the column name and incorporate the overall dataset's domain and description.
- Decide if the column’s events have clear semantics that imply a natural sequence (e.g., state or action transitions). If the events are ambiguous or do not follow inherent order, return "None".

Step 2: Joint Semantic and Statistical Analysis
- Use deep domain knowledge to define the natural, business-valid progression between events, and evaluate each candidate next event by jointly considering its semantic meaning and its statistical occurrence.
- For each current event state, determine the valid "allowed_next" transitions as follows:
  - Analyze the inherent semantic order to decide which transitions are expected given the context. For example, if the column represents server statuses recorded every second, it may be semantically valid for the state "starting" to transition to "starting" (self‑transition).
  - Evaluate statistical evidence (frequency counts, transition counts) for each candidate next event. If a candidate (including a self‑transition) appears with a high proportion relative to other transitions, then it is likely a valid next value. Conversely, if a candidate's occurrence count is significantly lower (e.g., most transitions occur 10 times while this candidate appears only 1–3 times), then it should be considered invalid—unless strong semantic evidence specifically supports its inclusion.
- Thus, allowed_next does not automatically exclude the current state's own value; the decision is based on whether the self‑transition is supported both semantically and statistically.
- Internally validate the rationale for each allowed transition by merging these analyses, but do not include any of this internal reasoning in the final output.

Step 3: Final Decision and Output
- Synthesize semantic evaluation and statistical evidence to finalize the sequence rule.
- For each current event state, compile an "allowed_next" list containing only the candidate events validated by both semantic and statistical analysis.
- IMPORTANT: If the semantics clearly indicate process states or action changes, you must output a sequence rule—even if some transitions have low counts. Return "None" only if the semantic analysis unequivocally shows that sequence analysis is not applicable.
- Do not include any internal analysis or validation details in the final output.

Return Value Rules:
If a valid sequence rule is derived, produce your result in the following JSON format:

{
    "sequence": [
        {
            "value": "<current_state>",
            "allowed_next": ["valid_next_state1", "valid_next_state2", ...]
        }
        // Additional state objects for multiple current states
    ]
}

If no clear, meaningful sequence rule is established (i.e., the column’s events do not indicate a natural order), return:

{
    "sequence": "None"
}

Remember:
- Base your analysis on semantic evaluation: only derive a sequence rule if the column’s events clearly represent process states or action changes.
- Do not force a sequence result if the data does not exhibit an inherent sequential order.
- Do not include any internal reasoning or validation steps in the final output.
- Adhere strictly to the specified JSON output format.

Input Format:
1. The overall dataset’s domain and description for contextual analysis.
2. The column name.
3. The list of event state values.


    '''
    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'column name: ' + columnName
    for valueDict in sequenceList:
        llmFlag = False
        if isinstance(valueDict["value"], str):
            nextValueFlag = False
            temp = ''
            for nextValueDict in valueDict["nextValueList"]:
                if isinstance(nextValueDict["value"], str):
                    nextValueFlag = True
                    temp += " " + nextValueDict["value"] + '(' + str(nextValueDict["sequenceRate"]) + '),'
            if nextValueFlag:
                llmFlag = True
                userPrompt += '\n' + valueDict["value"] + "'s next value:" + temp
                userPrompt = userPrompt.rstrip(',')
    try:
        if llmFlag:
            if model != "api":
                llmResult = chat_api(system_prompt=systemPrompt, provider="ollama", user_prompt=userPrompt, format=schema, temperature=0.3, model=model)
            else:
                llmResult = chat_api(system_prompt=systemPrompt, provider="api", user_prompt=userPrompt, format="json", temperature=0.3, model=None)

            characterSequence = llmResult['sequence']
            if characterSequence == "None":
                return {"status": False, "characterSequence": None}
            else:
                return {"status": True, "characterSequence": characterSequence}
        else:
            return {"status": False, "characterSequence": None}
    except Exception as e:
        return {"status": False, "characterSequence": None}