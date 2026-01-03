"""LLM-assisted rule localization from natural language.
Extracts ruleType and columnsList using known schema, then fetches rule payload from validation JSON.
"""

import json
from typing import Any, Dict, List, Optional

from llms import chat_api

RULE_TYPES = [
    "Missing",
    "Duplicate",
    "Format",
    "DifferentDomain",
    "SameEntity",
    "Sequence",
    "Range",
    "Difference",
    "RelativeDifference",
    "DateFormat",
    "Compare",
    "Substring",
    "Lookup",
    "Logical and condition",
    "MultiDifference",
    "MultiDuplicate",
]


def locate_rule_type_and_columns(
    nl_text: str,
    available_columns: List[str],
    model: Optional[str],
    workflow_mode: str = "ollama",
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """Use LLM to guess ruleType and involved columns."""
    system_prompt = (
        "You are a data-quality rule router. "
        "Given a natural language request, pick the most likely ruleType and the columns involved. "
        f"Allowed rule types: {', '.join(RULE_TYPES)}. "
        f"Available columns: {', '.join(available_columns)}. "
        "Return JSON with ruleType (one of the allowed), columnsList (1-3 column names from available list), and reason."
    )
    user_prompt = f"""
User request:
{nl_text}
Return JSON fields: ruleType, columnsList, reason.
"""
    provider = "api" if workflow_mode == "api" else "ollama"
    model = "qwen2.5:72b-instruct-q4_K_M" if provider == "ollama" else None

    payload = chat_api(
        system_prompt=system_prompt,
        provider=provider,
        user_prompt=user_prompt,
        format="json",
        temperature=temperature,
        model=model,
    )
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return payload


def extract_rule_from_validation(
    rule_type: str,
    columns: List[str],
    validation_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Pick the existing validationRule from validation_data based on type/columns."""
    if not columns:
        return None

    col = columns[0]
    # Single-column rules
    if rule_type in {"Missing", "Duplicate", "Format", "Range", "DateFormat", "DifferentDomain", "SameEntity", "Sequence", "Difference", "RelativeDifference"}:
        if col not in validation_data:
            return None
        col_entry = validation_data[col]
        if rule_type == "Missing":
            return {
                "missingDetectFlag": col_entry.get("missingDetectFlag"),
                "specialMissingValueList": col_entry.get("specialMissingValueList", []),
            }
        if rule_type == "Duplicate":
            return {"duplicateDetectFlag": col_entry.get("duplicateDetectFlag")}
        if rule_type == "Format":
            return col_entry.get("format")
        if rule_type == "Range":
            return col_entry.get("range")
        if rule_type == "DateFormat":
            return col_entry.get("format")
        if rule_type == "DifferentDomain":
            return col_entry.get("differentDomainList")
        if rule_type == "SameEntity":
            return col_entry.get("sameEntityList")
        if rule_type == "Sequence":
            return col_entry.get("sequenceRule")
        if rule_type == "Difference":
            return col_entry.get("difference", {}).get("difference")
        if rule_type == "RelativeDifference":
            return col_entry.get("difference", {}).get("relativeDifference")

    # Compare (two columns)
    if rule_type == "Compare" and len(columns) >= 2:
        c1, c2 = columns[:2]
        for item in validation_data.get("numericCompareList", []):
            if {item.get("column1"), item.get("column2")} == {c1, c2}:
                return item
        for item in validation_data.get("dateCompareList", []):
            if {item.get("column1"), item.get("column2")} == {c1, c2}:
                return item

    # Lookup (two columns)
    if rule_type == "Lookup" and len(columns) >= 2:
        c1, c2 = columns[:2]
        for item in validation_data.get("lookupList", []):
            if {item.get("parentColumnName"), item.get("childColumnName")} == {c1, c2}:
                return item

    # Logical and condition (two columns typical)
    if rule_type == "Logical and condition" and len(columns) >= 2:
        for item in validation_data.get("conditionLogicColumnList", []):
            conds = set(item.get("conditionColumns", []))
            cons = set(item.get("constraintColumns", []))
            if set(columns) == conds.union(cons):
                return item

    # MultiDifference across multiple columns
    if rule_type == "MultiDifference" and len(columns) >= 2:
        for item in validation_data.get("multiDifference", []):
            if set(item.get("columns", [])) == set(columns):
                return item.get("differenceDict")

    # MultiDuplicate across multiple columns
    if rule_type == "MultiDuplicate" and len(columns) >= 2:
        for item in validation_data.get("multipleDuplicateColumnsList", []):
            if set(item) == set(columns):
                return item

    return None
