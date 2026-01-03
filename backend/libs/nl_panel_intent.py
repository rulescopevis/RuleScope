import json
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from llms import chat_api

DEFAULT_OLLAMA_MODEL = "qwen2.5:72b-instruct-q4_K_M"


class NLPanelIntentResult(BaseModel):
    intent: Literal["create_new_rule", "modify_existing_rule", "clarify"]
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    reason: str


def _build_prompts(natural_language: str) -> tuple[str, str]:
    system_prompt = (
        "You are a data-quality copilot for validation rules. "
        "Classify the user's natural-language input as either creating a new validation rule, "
        "modifying an existing validation rule, or requesting clarification. "
        "Known rule categories include: Missing, Duplicate, Format, DifferentDomain, SameEntity, "
        "Sequence, Range, Difference, RelativeDifference, DateFormat, Compare, Substring, Lookup, "
        "Logical and condition, MultiDifference, MultiDuplicate. "
        "Be strict about JSON validity and only return the fields specified."
    )

    user_prompt = f"""
Analyze the intent of the user's request for the validation-rule panel.
Return a JSON object with fields: intent (create_new_rule | modify_existing_rule | clarify), confidence (0-1), and reason (short rationale).

Guidance:
- create_new_rule: user wants to add a brand new validation rule or describes a rule without referencing an existing one.
- modify_existing_rule: user wants to change, refine, or adjust a rule that already exists (mentions update/fix/tune/relax/tighten a rule, or references a prior rule or a rule type from the known categories).
- clarify: the request is too vague to decide.

User request:
{natural_language}
"""
    return system_prompt, user_prompt


def _normalize_response(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def detect_nl_intent(
    natural_language: str,
    workflow_mode: str = "ollama",
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """Route NLPanel input to create vs modify flow using the configured LLM."""
    if not natural_language or not natural_language.strip():
        return {"status": False, "error": "natural language is empty"}

    provider = "api" if workflow_mode == "api" else "ollama"
    system_prompt, user_prompt = _build_prompts(natural_language.strip())

    try:
        if provider == "ollama":
            schema = NLPanelIntentResult.model_json_schema()
            llm_resp = chat_api(
                system_prompt=system_prompt,
                provider=provider,
                user_prompt=user_prompt,
                format=schema,
                temperature=temperature,
                model=model or DEFAULT_OLLAMA_MODEL,
            )
        else:
            llm_resp = chat_api(
                system_prompt=system_prompt,
                provider=provider,
                user_prompt=user_prompt,
                format="json",
                temperature=temperature,
                model=None,
            )
    except Exception as exc:  # noqa: BLE001
        return {"status": False, "error": str(exc)}

    normalized = _normalize_response(llm_resp)

    try:
        parsed = NLPanelIntentResult.model_validate(normalized)
        return {
            "status": True,
            "intent": parsed.intent,
            "confidence": parsed.confidence,
            "reason": parsed.reason,
            "raw": normalized,
        }
    except ValidationError as exc:
        return {"status": False, "error": f"intent parsing failed: {exc}"}
