from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AZURE_FREE = ROOT / "docs" / "setup" / "AZURE_FREE_ACCOUNT.md"
COSTS = ROOT / "docs" / "operations" / "COST_AND_TEARDOWN.md"


def test_azure_free_account_doc_records_current_sandbox_and_account_boundaries():
    text = AZURE_FREE.read_text(encoding="utf-8").casefold()

    assert "last verified: 2026-07-27" in text
    assert "sandboxes" in text and ("retired" in text or "unavailable" in text)
    assert "$200 credit" in text
    assert "within 30 days" in text
    assert "new azure customers" in text
    assert "azure for students" in text
    assert "$100 azure credit" in text
    assert "no credit card required" in text
    assert "must not" in text and "create the azure account for the learner" in text
    assert "do not promise that every azure ai or foundry service is free" in text
    assert "exam-interface sandbox" in text


def test_cost_and_teardown_doc_requires_budgets_tags_and_live_opt_in():
    text = COSTS.read_text(encoding="utf-8").casefold()

    assert "last verified: 2026-07-27" in text
    assert "budgets do not automatically stop consumption" in text
    assert "project=ai-103" in text
    assert "deleteafter=<yyyy-mm-dd>" in text
    assert "no explicit live-lab opt-in" in text
    assert "no budget or cost gate" in text
    assert "teardown plan is missing" in text
    assert "provisioned throughput" in text
    assert "delete lab resource groups" in text


def test_azure_setup_docs_include_official_microsoft_sources():
    combined = "\n".join(
        [
            AZURE_FREE.read_text(encoding="utf-8"),
            COSTS.read_text(encoding="utf-8"),
        ]
    )

    assert "https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account" in combined
    assert "https://azure.microsoft.com/en-us/free/students" in combined
    assert "https://learn.microsoft.com/en-us/answers/questions/5902797/sandbox-available" in combined
    assert "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets" in combined
    assert "https://learn.microsoft.com/en-us/azure/foundry/concepts/manage-costs" in combined
