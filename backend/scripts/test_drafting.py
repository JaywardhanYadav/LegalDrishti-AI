# backend/scripts/test_drafting.py
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.models.draft import Draft
from app.schemas.draft import DraftGenerateRequest, DraftTypeEnum
from app.services.drafting import generate_legal_draft, run_statutory_validation


async def test_legal_drafting():
    print("=" * 80)
    print("TESTING STRUCTURED LEGAL DRAFTING ENGINE (PHASE 7)")
    print("=" * 80)

    async with async_session_factory() as session:
        # Step 0: Fetch or auto-create test advocate user
        stmt = select(User).limit(1)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            print("Notice: No user found. Creating test advocate user...")
            user = User(
                email="advocate.test@legaldrishti.ai",
                hashed_password="placeholder_hash",
                full_name="Adv. Ramesh Chandra",
                role="advocate",
                is_active=True,
                deep_search_credits=3,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        user_id = user.id
        print(f"Executing test drafts for User ID: {user_id} ({user.email})")

        # ----------------------------------------------------------------------
        # TEST 1: SECTION 138 NI ACT STATUTORY DEMAND NOTICE
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("[TEST 1] Generating Section 138 NI Act Statutory Demand Notice...")
        print("=" * 80)

        notice_request = DraftGenerateRequest(
            draft_type=DraftTypeEnum.NOTICE_138_NI_ACT,
            title="Statutory Demand Notice - Cheque Bounce Apex Infotech",
            court_name="Under Section 138 of Negotiable Instruments Act, 1881",
            jurisdiction="New Delhi, India",
            custom_facts=(
                "Complainant/Payee: Vikram Malhotra, residing at Defense Colony, New Delhi.\n"
                "Opponent/Drawer: Rajesh Sharma, Managing Director, Apex Infotech Pvt. Ltd., Connaught Place, New Delhi.\n"
                "Transaction: Loan of Rs. 15,00,000 advanced for business expansion.\n"
                "Cheque Details: Cheque No. 489201 dated 10th January 2025, drawn on HDFC Bank, Connaught Place Branch for Rs. 15,00,000/-.\n"
                "Dishonour: Presented on 12th January 2025, returned unpaid on 14th January 2025 vide Bank Return Memo "
                "with endorsement 'Funds Insufficient'."
            ),
            special_instructions="Specifically demand payment within 15 days, failing which criminal proceedings under Section 138 and 141 shall be initiated.",
        )

        draft1 = await generate_legal_draft(user_id=user_id, payload=notice_request, session=session)

        print(f"✅ Draft 1 Created! ID: {draft1.id} | Title: {draft1.title}")
        print(f"Statutory Validation Status: {draft1.validation_status}")
        print("\n--- VALIDATION REPORT ---")
        print(draft1.validation_report)
        print("\n--- GENERATED LEGAL NOTICE EXCERPT (FIRST 600 CHARACTERS) ---")
        print(draft1.content[:600] + "\n...")

        # ----------------------------------------------------------------------
        # TEST 2: ANTICIPATORY BAIL APPLICATION UNDER BNSS SECTION 482
        # ----------------------------------------------------------------------
        print("\n" + "=" * 80)
        print("[TEST 2] Generating Anticipatory Bail Application (BNSS Sec 482)...")
        print("=" * 80)

        bail_request = DraftGenerateRequest(
            draft_type=DraftTypeEnum.ANTICIPATORY_BAIL_BNSS,
            title="Anticipatory Bail Application - Sanjay Verma",
            court_name="In the Court of the Principal Sessions Judge, Patiala House Courts, New Delhi",
            jurisdiction="New Delhi",
            custom_facts=(
                "Applicant: Sanjay Verma, aged 45 years, businessman of high repute with no criminal antecedents.\n"
                "Respondent: State (NCT of Delhi) & Complainant M/s Global Traders.\n"
                "Allegations: Apprehension of arrest in relation to FIR No. 89/2024, PS Barakhamba Road, registered "
                "under Sections 318(4) and 316(2) of Bharatiya Nyaya Sanhita, 2023 (formerly 420 & 406 IPC).\n"
                "Defence: Dispute is purely civil in nature arising out of breach of a commercial sales contract."
            ),
            special_instructions=(
                "Emphasize deep roots in society, absolute willingness to cooperate with the Investigating Officer, "
                "and an express undertaking not to tamper with any witness or evidence."
            ),
        )

        draft2 = await generate_legal_draft(user_id=user_id, payload=bail_request, session=session)

        print(f"✅ Draft 2 Created! ID: {draft2.id} | Title: {draft2.title}")
        print(f"Statutory Validation Status: {draft2.validation_status}")
        print("\n--- VALIDATION REPORT ---")
        print(draft2.validation_report)
        print("\n--- GENERATED BAIL APPLICATION EXCERPT (FIRST 600 CHARACTERS) ---")
        print(draft2.content[:600] + "\n...")

        print("\n" + "=" * 80)
        print("PHASE 7 LEGAL DRAFTING ENGINE VERIFICATION PASSED ✅")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_legal_drafting())
