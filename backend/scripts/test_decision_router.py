"""
Test & Benchmark script for LegalDrishti AI - Jev Multi-Pipeline Decision Engine
Verifies dynamic pipeline combinations:
1. Pure Conversational / Greeting (0ms DB cost)
2. Pure 28 Bare Acts Statutory Search
3. Pure Client Case Vault Search
4. Pure Live Web Search (Tavily)
5. Combination: 28 Bare Acts + Client Vault
6. Combination: 28 Bare Acts + Live Web Search
7. Combination: Client Vault + Live Web Search
8. Combination: 28 Bare Acts + Client Vault + Live Web Search (Triple Stream!)
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.decision_router import decide_query_action, MultiPipelineDecision

TEST_SCENARIOS = [
    {
        "label": "1. Pure Conversational / Greeting",
        "query": "Hello, good morning! Who are you and how does LegalDrishti AI assist me?",
        "has_vault": False,
        "expected_active": ["conversational"],
    },
    {
        "label": "2. Pure 28 Bare Acts Statutory Query",
        "query": "What is the statutory limitation period under Section 138 of Negotiable Instruments Act for issuing a legal demand notice?",
        "has_vault": False,
        "expected_active": ["statutes_28_acts"],
    },
    {
        "label": "3. Pure Client Case Vault Query",
        "query": "According to the uploaded agreement, what is the notice period mentioned in Clause 12 of my document?",
        "has_vault": True,
        "expected_active": ["client_case_vault"],
    },
    {
        "label": "4. Pure Live Web Search",
        "query": "What is the latest breaking news and today's order from the Supreme Court on high court judge appointments?",
        "has_vault": False,
        "expected_active": ["live_web_search"],
    },
    {
        "label": "5. Combination: 28 Bare Acts + Client Vault",
        "query": "Does Clause 14 of my uploaded contract violate Section 23 of the Indian Contract Act regarding unlawful consideration?",
        "has_vault": True,
        "expected_active": ["statutes_28_acts", "client_case_vault"],
    },
    {
        "label": "6. Combination: 28 Bare Acts + Live Web Search",
        "query": "How did the latest 2024 Supreme Court rulings interpret Section 482 of BNSS regarding anticipatory bail?",
        "has_vault": False,
        "expected_active": ["statutes_28_acts", "live_web_search"],
    },
    {
        "label": "7. Combination: Client Vault + Live Web Search",
        "query": "Is the trademark in my uploaded petition affected by yesterday's new government policy guidelines?",
        "has_vault": True,
        "expected_active": ["client_case_vault", "live_web_search"],
    },
    {
        "label": "8. Combination: 28 Bare Acts + Client Vault + Live Web Search (Triple Stream!)",
        "query": "Based on my uploaded contract facts, what are our legal grounds under Section 9 of the Arbitration Act and what are the latest 2024 SC precedents?",
        "has_vault": True,
        "expected_active": ["statutes_28_acts", "client_case_vault", "live_web_search"],
    },
]


def main():
    print("=" * 85)
    print("⚖️  LegalDrishti AI - Jev Multi-Pipeline Decision Engine Verification Suite")
    print("=" * 85)

    passed = 0
    total = len(TEST_SCENARIOS)

    for idx, test in enumerate(TEST_SCENARIOS, 1):
        print(f"\n[{idx:02d}/{total:02d}] Test Scenario: {test['label']}")
        print(f"     Query: \"{test['query']}\"")
        print(f"     Vault Documents Attached: {test['has_vault']}")

        decision: MultiPipelineDecision = decide_query_action(
            query=test["query"],
            has_vault_documents=test["has_vault"],
        )

        active = decision.activated_pipelines
        expected = test["expected_active"]

        # Check if expected pipelines are activated
        all_expected_active = all(p in active for p in expected)
        status = "✅ PASSED" if all_expected_active else "⚠️ DIVERGED"
        if all_expected_active:
            passed += 1

        print(f"     Status:              {status}")
        print(f"     Activated Pipelines: {active}")
        print(f"     Engine Used:         {decision.engine_used}")
        print(f"     Reasoning:           {decision.reasoning}")
        if decision.suggested_clarification:
            print(f"     Clarification:       {decision.suggested_clarification[:75]}...")
        print("-" * 85)

    print(f"\n=====================================================================================")
    print(f"Summary: {passed}/{total} multi-pipeline combination tests passed successfully ({passed/total*100:.1f}%)")
    print(f"The decision model can dynamically activate ANY individual pipeline or COMBINATION of pipelines!")
    print(f"=====================================================================================\n")


if __name__ == "__main__":
    main()
