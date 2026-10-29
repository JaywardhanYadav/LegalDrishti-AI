"""
LegalDrishti AI - Jev Multi-Pipeline Decision Engine & Query Triage Service
Uses TypeSafe AI's System One model (Jev) to dynamically evaluate and activate
any combination of retrieval pipelines:
  1. Indian Bare Acts PDFs (26+ Acts in Weaviate)
  2. Client Case Vault (Uploaded user contracts, FIRs, evidence)
  3. Live Web Search (Tavily legal research across Indian Kanoon, LiveLaw, Bar & Bench)
  4. Direct Conversational / Clarification (Zero DB lookup)
"""

import json
import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger("legaldrishti.decision_router")


class MultiPipelineDecision(BaseModel):
    is_conversational: bool = Field(
        default=False,
        description="True if query is a greeting, conversational chat, or lacks legal substance.",
    )
    search_statutes: bool = Field(
        default=False,
        description="True if query asks about Indian statutory law, Bare Acts, sections, or penalties.",
    )
    search_vault: bool = Field(
        default=False,
        description="True if query inquires about client-uploaded documents, agreements, or case records.",
    )
    search_web: bool = Field(
        default=False,
        description="True if query asks for recent Supreme Court rulings, live legal news, or contemporary developments.",
    )

    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence / probability score for each individual pipeline switch.",
    )
    reasoning: str = Field(
        default="",
        description="Brief legal rationale for which pipelines were activated.",
    )
    engine_used: str = Field(
        default="Jev (TypeSafe AI)",
        description="The underlying engine that evaluated the query.",
    )
    suggested_clarification: Optional[str] = Field(
        default=None,
        description="Suggested prompt back to user if query is conversational or information is insufficient.",
    )

    @property
    def activated_pipelines(self) -> list[str]:
        active = []
        if self.is_conversational:
            active.append("conversational")
        if self.search_statutes:
            active.append("statutes_28_acts")
        if self.search_vault:
            active.append("client_case_vault")
        if self.search_web:
            active.append("live_web_search")
        return active


def _get_typesafe_key() -> str:
    settings = get_settings()
    return settings.typesafe_api_key or os.environ.get("TYPESAFE_API_KEY", "").strip()


def decide_with_jev(query: str, has_vault_documents: bool = False) -> MultiPipelineDecision:
    """
    Executes multi-pipeline decisioning via TypeSafe AI's Jev model using independent Noul questions.
    """
    try:
        from typesafe_sdk import Noul, TypeSafeClient  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "typesafe-sdk is not installed in the active environment. Please run `pip install typesafe-sdk`."
        ) from exc

    api_key = _get_typesafe_key()
    if not api_key:
        raise ValueError("TYPESAFE_API_KEY is not configured.")

    questions = {
        "is_conversational": Noul(
            instructions="Is this message a casual greeting, conversational chat, or vague query lacking legal facts?"
        ),
        "search_statutes": Noul(
            instructions="Does this query ask about Indian Bare Acts, statutory law, legal sections, definitions, or penalties?"
        ),
        "search_web": Noul(
            instructions="Does this query require recent Supreme Court / High Court orders, breaking legal news, or live updates?"
        ),
    }

    if has_vault_documents:
        questions["search_vault"] = Noul(
            instructions="Does this query reference or ask about client-uploaded documents, agreements, petitions, or case evidence?"
        )

    with TypeSafeClient(api_key=api_key) as client:
        response = client.system_one(state=query, questions=questions)

        scores = {}
        flags = {}

        for key in ["is_conversational", "search_statutes", "search_web", "search_vault"]:
            if key in response.answers:
                answer = response.answers[key]
                # NoulAnswer.noul is a probability float (0.0 to 1.0)
                prob = getattr(answer, "noul", 0.0)
                scores[key] = round(float(prob), 4)
                flags[key] = bool(prob >= 0.5)
            else:
                scores[key] = 0.0
                flags[key] = False

        # If conversational flag is true and no substantive sources were activated
        if flags.get("is_conversational") and not any([flags.get("search_statutes"), flags.get("search_vault"), flags.get("search_web")]):
            clarification = (
                "Greetings. I am LegalDrishti AI. Please provide the details of your legal issue, "
                "relevant facts, or specific statutory provisions you wish to analyze."
            )
        else:
            clarification = None

        active_list = [k for k, v in flags.items() if v]

        return MultiPipelineDecision(
            is_conversational=flags.get("is_conversational", False),
            search_statutes=flags.get("search_statutes", False),
            search_vault=flags.get("search_vault", False),
            search_web=flags.get("search_web", False),
            confidence_scores=scores,
            reasoning=f"Jev activated pipelines: {', '.join(active_list) if active_list else 'none'}",
            engine_used="Jev (TypeSafe AI)",
            suggested_clarification=clarification,
        )


def decide_with_fallback(query: str, has_vault_documents: bool = False) -> MultiPipelineDecision:
    """
    Intelligent fallback multi-pipeline decision model when Jev API key is not yet configured.
    Evaluates independent switches so any combination of pipelines can activate.
    """
    settings = get_settings()

    # Try fast OpenAI decision triage if openai_api_key is available
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            system_prompt = (
                "You are the Lead Legal Intake Router for LegalDrishti AI.\n"
                "Evaluate the user query and determine which data pipelines must be activated.\n"
                "You can activate MULTIPLE pipelines simultaneously if the query requires them.\n"
                "Return ONLY a JSON object matching this schema:\n"
                "{\n"
                '  "is_conversational": bool,\n'
                '  "search_statutes": bool,\n'
                '  "search_vault": bool,\n'
                '  "search_web": bool,\n'
                '  "reasoning": "brief explanation",\n'
                '  "suggested_clarification": "optional text if is_conversational"\n'
                "}\n\n"
                "RULES:\n"
                "- is_conversational: True if greetings ('hi', 'hello') or vague with insufficient details.\n"
                "- search_statutes: True if query mentions/needs Indian Bare Acts, Sections, BNS, BNSS, BSA, NI Act, etc.\n"
                f"- search_vault: True if query asks about user's uploaded case files/contracts (Vault active: {has_vault_documents}).\n"
                "- search_web: True if query asks for latest news, today's order, or recent Supreme Court rulings.\n"
                "- COMBINATIONS: If a query asks to check an uploaded contract against a statutory section and recent news, activate ALL of them!"
            )

            res = client.chat.completions.create(
                model=settings.openai_model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            data = json.loads(res.choices[0].message.content or "{}")
            search_v = bool(data.get("search_vault", False)) if has_vault_documents else False

            return MultiPipelineDecision(
                is_conversational=bool(data.get("is_conversational", False)),
                search_statutes=bool(data.get("search_statutes", False)),
                search_vault=search_v,
                search_web=bool(data.get("search_web", False)),
                confidence_scores={"llm_confidence": 0.95},
                reasoning=data.get("reasoning", "OpenAI Multi-Pipeline Triage"),
                engine_used="Decision Fallback (OpenAI Triage)",
                suggested_clarification=data.get("suggested_clarification"),
            )
        except Exception as e:
            logger.warning(f"OpenAI fallback decision error: {e}")

    # Pure heuristic multi-switch engine
    q_lower = query.strip().lower()

    # 1. Conversational check
    greeting_starters = ["hi", "hello", "hey", "good morning", "good evening", "who are you", "what can you do", "help me"]
    has_greeting = any(q_lower.startswith(g) or f" {g}" in q_lower for g in greeting_starters)

    statutory_indicators = [
        "section", "act", "offence", "offense", "ipc", "crpc", "bns", "bnss", "bsa",
        "bail", "cheque", "dishonour", "limitation", "court", "magistrate", "punishment",
        "jurisdiction", "cognizance", "arrest", "warrant", "fir", "advocate", "arbitration"
    ]
    vault_indicators = ["my document", "my contract", "uploaded", "exhibit", "the agreement", "the clause", "case file", "petition", "our lease"]
    web_indicators = ["latest news", "today", "yesterday", "recent amendment", "recent ruling", "recent supreme court", "breaking", "latest 2024", "latest order"]

    has_statutes = any(si in q_lower for si in statutory_indicators)
    has_vault = has_vault_documents and any(vi in q_lower for vi in vault_indicators)
    has_web = any(wi in q_lower for wi in web_indicators)

    # If greeting and no substantive searches
    if (has_greeting and not (has_statutes or has_vault or has_web)) or (not (has_statutes or has_vault or has_web) and len(q_lower.split()) < 10):
        return MultiPipelineDecision(
            is_conversational=True,
            search_statutes=False,
            search_vault=False,
            search_web=False,
            confidence_scores={"conversational": 0.98},
            reasoning="Casual greeting or insufficient legal facts provided.",
            engine_used="Decision Fallback (Rule Engine)",
            suggested_clarification=(
                "Greetings. I am LegalDrishti AI. Please provide the details of your legal issue, "
                "relevant facts, or specific statutory provisions you wish to analyze."
            ),
        )

    # Otherwise, independent switches are activated based on query triggers:
    # Default to statutory search if no other specific domain is triggered but query has legal terms
    search_statutes = has_statutes or (not has_vault and not has_web)

    active_names = []
    if search_statutes:
        active_names.append("28 Bare Acts")
    if has_vault:
        active_names.append("Client Case Vault")
    if has_web:
        active_names.append("Live Web Search")

    return MultiPipelineDecision(
        is_conversational=False,
        search_statutes=search_statutes,
        search_vault=has_vault,
        search_web=has_web,
        confidence_scores={
            "statutes": 0.94 if search_statutes else 0.1,
            "vault": 0.92 if has_vault else 0.05,
            "web": 0.89 if has_web else 0.08,
        },
        reasoning=f"Query dynamically activated {len(active_names)} pipeline(s): {', '.join(active_names)}",
        engine_used="Decision Fallback (Rule Engine)",
        suggested_clarification=None,
    )


def decide_query_action(query: str, has_vault_documents: bool = False) -> MultiPipelineDecision:
    """
    Main entry point for multi-pipeline decisioning.
    Attempts Jev (TypeSafe AI) first if TYPESAFE_API_KEY is configured;
    otherwise gracefully falls back to the internal Multi-Pipeline Decision Engine.
    """
    api_key = _get_typesafe_key()

    if api_key:
        try:
            return decide_with_jev(query=query, has_vault_documents=has_vault_documents)
        except Exception as e:
            logger.warning(f"Jev API call failed ({e}). Falling back to secondary decision engine.")

    return decide_with_fallback(query=query, has_vault_documents=has_vault_documents)
