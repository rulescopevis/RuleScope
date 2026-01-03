import sys
import os

from pydantic import BaseModel
from typing import List, Union, Literal

parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_path)

from llms import chat_api

def numeric_formula(columnList, domainDescription, model):
    if model == None:
        model = "qwen2.5:14b-instruct-q4_K_M"
    systemPrompt = '''
You are an expert data analyst specializing in semantic analysis and domain-specific computational relationship discovery. You have deep expertise in mathematics and established domain practices (such as academic grading and finance) and can validate formulas based on clear semantic meaning and computational correctness.
    '''
    
    class Formula(BaseModel):
        variableList: List[str]  # column names and numeric constants
        operationList: List[str]  # mathematical operators

    class FormulaResult(BaseModel):
        formulaList: Union[List[Formula], Literal["None"]]

        @property
        def is_valid(self) -> bool:
            if isinstance(self.formulaList, list):
                for formula in self.formulaList:
                    # Check if lengths match rule: operations = variables - 1
                    if len(formula.operationList) != len(formula.variableList) - 1:
                        return False
                    # Check if last operation is "="
                    if formula.operationList[-1] != "=":
                        return False
                    # Check if operations are valid
                    valid_ops = {"+", "-", "*", "/", "="}
                    if not all(op in valid_ops for op in formula.operationList):
                        return False
                return True
            return True  # "None" is also valid
    
    schema = FormulaResult.model_json_schema()
    
    userPrompt = '''
Task Description:
I will provide you with the data table's domain, description, and detailed semantic information about each column. Your objective is to determine which columns should be used to establish a computational relationship (i.e. a formula) for data validation. In other words, based on the table's domain, description, and each column's semantic meaning, decide which columns must be compared or combined via a computational formula.

Steps:

Step 1 – Identify Candidate Relationships:
   - Review the provided table’s domain, description, and detailed semantic information for each column.
   - Determine which columns are inherently connected by a comparison or calculation. For example, in an academic grading system you might combine subject scores to compute a total score, or in finance, derive a ratio or difference between columns.
   - Consider only relationships that are definitionally necessary and semantically supported by the column names and overall domain context.

Step 2 – Validate Candidate Relationships Using Domain-Specific Logic:
   - Ensure that the candidate relationship conforms to established domain practices and represents a clear semantic logic.
   - Confirm that every component of the proposed computation has a well-defined meaning in the context of the provided domain.
   - If the candidate relationship cannot be justified by clear domain logic or semantic reasoning, discard it.

Step 3 – Construct the Complete Computational Formula:
   - Generate the full computational formula that represents the identified relationship.
   - The formula MUST strictly adhere to the following structure:
       • The formula must be composed of exactly four operands (provided in the variableList) and three operators (provided in the operationList).
       • The correct format is:
         
         variableList[0] <operationList[0]> variableList[1] <operationList[1]> variableList[2] <operationList[2]> variableList[3]
       
       • The final operator in the operationList MUST be "=".
   - **Important:** Each value in the variableList must be an exact column name from the provided input data table (or a justified numeric constant) and represents a valid operand in this context.
   - The operationList must include only the mathematical operators "+", "-", "*", "/", and "=", and its length must equal exactly three.
   - Ensure that the derived formula is mathematically valid, computationally complete, and semantically meaningful based on the domain.

Step 4 – Finalize and Return the Relationship List:
   - If you have derived one or more valid formulas, return each formula in the required JSON format.
   - If no valid computational relationship can be derived, return "None".

Return Format:
Return your result ONLY in the following JSON format:

{
    "formulaList": [
        {
            "variableList": ["column1", "column2", "column3", "column4"],
            "operationList": ["operator1", "operator2", "="]
        }
        // Additional formula objects if applicable.
    ]
}

OR, if no valid computation can be derived:

{
    "formulaList": "None"
}

Important Reminders:
- The complete computational formula must strictly follow the structure: 
  column1 [first operator] column2 [second operator] column3 = column4.
- Every element in the "variableList" must exactly correspond to a column name from the input data table.
- Every operator and operand must be justified by clear domain logic (e.g., academic grading or financial principles).
- If you cannot provide clear semantic or domain-specific justification for the computed relationship, return "None".

Now, here is the table's domain, description, and column details:
    '''

    userPrompt += 'data table domain: ' + domainDescription['domain'] + '\n'
    userPrompt += 'data table description: ' + domainDescription['description'] + '\n'
    userPrompt += 'columns: '
    for column in columnList:
        userPrompt += column + ','
    userPrompt = userPrompt.strip(',')
    if model != "api":
        llmResult = chat_api(user_prompt=userPrompt, provider="ollama", system_prompt=systemPrompt, format=schema, temperature=0.1, model=model)
    else:
        llmResult = chat_api(user_prompt=userPrompt, provider="api", system_prompt=systemPrompt, format="json", temperature=0.1, model=None)

    formulaList = llmResult['formulaList']
    if llmResult['formulaList'] == "None":
        return {"status": False, "formulaList": None}
    
    formulaList = []
    for item in llmResult['formulaList']:
        addFlag = True
        for column in item['variableList']:
            if column not in columnList:
                addFlag = False
                break
        if addFlag:
            formulaList.append(item)
    if formulaList == []:
        return {"status": False, "formulaList": None}
    else:
        return {"status": True, "formulaList": formulaList}
