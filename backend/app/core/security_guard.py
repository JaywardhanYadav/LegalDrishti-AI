import re
from fastapi import HTTPException, status

MAX_QUERY_LENGTH = 1000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules|prompts)",
    r"disregard\s+(all\s+)?(previous|prior)?\s*rules",
    r"system\s+(override|bypass|prompt)",
    r"you\s+are\s+now\s+(in\s+developer\s+mode|dan|unrestricted)",
    r"forget\s+(everything|your\s+instructions)",
    r"print\s+(your\s+)?(system\s+prompt|initial\s+instructions)",
    r"act\s+as\s+(an\s+unrestricted|a\s+jailbroken)\s+ai",
]


def validate_and_sanitize_query(query: str) -> str:
    cleaned = query.strip()

 
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Legal query exceeds the maximum allowed limit of {MAX_QUERY_LENGTH} characters.",
        )

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Guardrail: Disallowed system override commands detected in query.",
            )

    return cleaned
