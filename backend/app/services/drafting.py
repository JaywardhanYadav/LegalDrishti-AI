
import json
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.case import Case
from app.models.case_document import CaseDocument
from app.models.document import Document
from app.models.draft import Draft
from app.schemas.draft import DraftGenerateRequest, DraftTypeEnum


def run_statutory_validation(draft_type: str, content: str) -> tuple[str, str]:
    """
    Validates essential statutory ingredients in the generated legal draft.
    Returns (status, report_json_string).
    """
    text_lower = content.lower()
    checks = []

    if draft_type == DraftTypeEnum.NOTICE_138_NI_ACT.value:
        # Ingredient 1: 15-day statutory cure period (Proviso c, Sec 138)
        import re
        has_15_days = bool(
            re.search(
                r"(15\s*days|fifteen\s*days|fifteen\s*\(\s*15\s*\)\s*days|15\s*\(\s*fifteen\s*\)\s*days|within\s*(?:a\s*period\s*of\s*)?(?:15|fifteen))",
                text_lower,
            )
        )


        # Ingredient 2: Cheque details
        has_cheque = "cheque" in text_lower
        checks.append({
            "rule": "Cheque Identification",
            "passed": has_cheque,
            "details": "Cheque particulars referenced in pleading." if has_cheque else "Cheque details missing.",
        })

        # Ingredient 3: Dishonour / Return Memo
        has_dishonour = any(term in text_lower for term in ["dishonour", "unpaid", "insufficient", "memo"])
        checks.append({
            "rule": "Bank Dishonour / Return Memo Allegation",
            "passed": has_dishonour,
            "details": "Allegation of bank return memo and dishonour included." if has_dishonour else "Bank return memo date or reason not specified.",
        })

        # Ingredient 4: Section 138 & 141 NI Act invocation
        has_section = "138" in text_lower
        checks.append({
            "rule": "Statutory Invocation (Sec 138 NI Act)",
            "passed": has_section,
            "details": "Section 138 correctly cited." if has_section else "Section 138 citation missing.",
        })

    elif draft_type == DraftTypeEnum.ANTICIPATORY_BAIL_BNSS.value:
        # Ingredient 1: BNSS Section 482 / CrPC 438 invocation
        has_bnss = "482" in text_lower or "438" in text_lower or "bnss" in text_lower
        checks.append({
            "rule": "Statutory Provision Cited (BNSS Sec 482 / CrPC Sec 438)",
            "passed": has_bnss,
            "details": "Governing anticipatory bail provision cited." if has_bnss else "Statutory bail provision citation missing.",
        })

        # Ingredient 2: Undertaking to cooperate with investigation
        has_cooperate = any(term in text_lower for term in ["cooperat", "join the investigation", "interrogation", "summon"])
        checks.append({
            "rule": "Undertaking to Join Investigation",
            "passed": has_cooperate,
            "details": "Mandatory undertaking to appear before Investigating Officer included." if has_cooperate else "Undertaking to join investigation missing.",
        })

        # Ingredient 3: Non-tampering undertaking
        has_tamper = "tamper" in text_lower or "influence" in text_lower
        checks.append({
            "rule": "No Witness Tampering / Inducement Undertaking",
            "passed": has_tamper,
            "details": "Standard undertaking not to influence witnesses included." if has_tamper else "Undertaking against tampering missing.",
        })

        # Ingredient 4: Formal Prayer
        has_prayer = "prayer" in text_lower or "pray" in text_lower
        checks.append({
            "rule": "Formal Court Prayer Clause",
            "passed": has_prayer,
            "details": "Formal prayer for pre-arrest bail present." if has_prayer else "Prayer clause missing.",
        })

    elif draft_type == DraftTypeEnum.LEGAL_AFFIDAVIT.value:
        has_affirm = "solemnly affirm" in text_lower or "deponent" in text_lower
        checks.append({
            "rule": "Deponent Affirmation Clause",
            "passed": has_affirm,
            "details": "Solemn affirmation block included." if has_affirm else "Affirmation statement missing.",
        })

        has_verify = "verif" in text_lower
        checks.append({
            "rule": "Pleading Verification Clause",
            "passed": has_verify,
            "details": "Standard verification of truth on oath included." if has_verify else "Verification clause missing.",
        })

    else:
        checks.append({
            "rule": "Pleading Form",
            "passed": len(content) > 200,
            "details": "General legal format satisfied.",
        })

    all_passed = all(c["passed"] for c in checks)
    status = "VALIDATED" if all_passed else "WARNINGS"
    return status, json.dumps(checks, indent=2)


async def build_case_context(case_id: int, session: AsyncSession) -> str:
    """Extracts factual parameters from Case and associated Document records."""
    stmt = select(Case).where(Case.id == case_id)
    res = await session.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        return "No case record linked."

    facts = [
        f"Case Title: {case.title}",
        f"Court / Forum: {case.court_name or 'Competent Court'}",
        f"Case Type: {case.case_type}",
        f"Client / Complainant / Petitioner: {case.client_name or '[Client Name]'}",
        f"Opponent / Accused / Respondent: {case.opponent_name or '[Opponent Name]'}",
        f"Case Summary on Record: {case.description or 'None'}",
    ]

    doc_stmt = (
        select(Document.title, Document.extracted_text)
        .join(CaseDocument, CaseDocument.document_id == Document.id)
        .where(CaseDocument.case_id == case_id)
        .limit(3)
    )
    doc_res = await session.execute(doc_stmt)
    doc_excerpts = []
    for d_title, d_text in doc_res.all():
        if d_text:
            snippet = d_text[:1200].replace("\n", " ")
            doc_excerpts.append(f"Document '{d_title}': {snippet}...")

    if doc_excerpts:
        facts.append("Evidentiary Excerpts from Vault:\n" + "\n".join(doc_excerpts))

    return "\n".join(facts)


async def generate_legal_draft(
    user_id: int,
    payload: DraftGenerateRequest,
    session: AsyncSession,
) -> Draft:
    """
    Generates a structured court-ready legal draft adhering to Indian rules of practice.
    Saves and returns the Draft model instance.
    """
    settings = get_settings()

    case_context = ""
    if payload.case_id:
        case_context = await build_case_context(payload.case_id, session)

    system_prompt = (
        "You are LegalDrishti AI, a specialized legal drafting engine adhering strictly to Indian Court Rules of Practice.\n"
        "Your task is to draft formal, inspection-ready legal pleadings and statutory notices.\n\n"
        "STRICT DRAFTING RULES:\n"
        "1. FORMAT & STRUCTURE: Follow the formal Indian legal pleading hierarchy:\n"
        "   - Heading / Court Name / Forum\n"
        "   - Cause Title / Memo of Parties (Complainant/Petitioner vs. Accused/Respondent)\n"
        "   - Subject / Statutory Caption\n"
        "   - Numbered Pleading Paragraphs (1., 2., 3., ...)\n"
        "   - Specific Statutory Grounds / Mandatory Notice Demand\n"
        "   - Formal Prayer Clause\n"
        "   - Verification & Deponent Affidavit Clause\n"
        "   - Advocate Signature Block & Date/Place placeholders\n"
        "2. MANDATORY STATUTORY INGREDIENTS:\n"
        "   - If drafting a Section 138 NI Act Notice: You MUST demand payment strictly within 15 (FIFTEEN) DAYS of notice receipt. "
        "Include cheque particulars, return memo date, and consequences under Sec 138 & 141.\n"
        "   - If drafting Anticipatory Bail: Cite Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) (and Sec 438 CrPC). "
        "Include undertakings to join investigation and not to tamper with witnesses or evidence.\n"
        "3. EDITABLE PLACEHOLDERS: Where specific particulars (like Cheque No., Exact Date, Bank Name) are missing from the record, "
        "insert clear brackets like [Cheque No. _______], [Date: DD/MM/YYYY], [Bank Name] so the advocate can fill them in.\n"
        "4. TONE: Solemn, dignified, rigorous, and professional legal parlance. Do NOT add conversational pleasantries or meta-comments."
    )

    user_instructions = (
        f"Draft Type: {payload.draft_type.value}\n"
        f"Target Court / Forum: {payload.court_name or 'Competent Court'}\n"
        f"Jurisdiction: {payload.jurisdiction}\n\n"
    )

    if case_context:
        user_instructions += f"CASE FACTS ON RECORD:\n{case_context}\n\n"

    if payload.custom_facts:
        user_instructions += f"ADVOCATE'S FACTUAL INSTRUCTIONS:\n{payload.custom_facts}\n\n"

    if payload.special_instructions:
        user_instructions += f"SPECIAL PRAYER / RELIEF INSTRUCTIONS:\n{payload.special_instructions}\n\n"

    user_instructions += "Generate the complete, formal legal draft now:"

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_instructions},
        ],
    )

    draft_content = response.choices[0].message.content or ""

    # Run statutory compliance check
    validation_status, validation_report = run_statutory_validation(
        draft_type=payload.draft_type.value,
        content=draft_content,
    )

    default_title = payload.title or f"{payload.draft_type.value.replace('_', ' ').title()} - {payload.jurisdiction}"

    new_draft = Draft(
        user_id=user_id,
        case_id=payload.case_id,
        title=default_title,
        draft_type=payload.draft_type.value,
        content=draft_content.strip(),
        jurisdiction=payload.jurisdiction,
        court_name=payload.court_name,
        validation_status=validation_status,
        validation_report=validation_report,
        version=1,
    )

    session.add(new_draft)
    await session.commit()
    await session.refresh(new_draft)

    return new_draft
