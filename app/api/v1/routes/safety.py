"""
Safety Routes — Tests the real GuardrailsService without calling the LLM.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.guardrails_service import GuardrailsService


router = APIRouter(prefix="/safety", tags=["Safety"])

guardrails = GuardrailsService()


class SafetyCheckRequest(BaseModel):
    text: str


@router.post("/check")
async def check_safety(request: SafetyCheckRequest):
    """
    Run the submitted text through the same guardrails
    used by the chat pipeline.
    """

    result = guardrails.check_query(request.text)

    return {
        "is_safe": result.is_safe,
        "sanitized_text": result.sanitized_query,
        "pii_detected": result.pii_detected,
        "is_emergency": result.is_emergency,
        "refusal_message": result.refusal_message,
    }