from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bicep_main_is_subscription_scoped_and_offline_by_default():
    text = read("infra/main.bicep")

    assert "targetScope = 'subscription'" in text
    assert "Microsoft.Resources/resourceGroups@2025-04-01" in text
    assert "param deployFoundry bool = false" in text
    assert "param deploySearch bool = false" in text
    assert "param deployStorage bool = false" in text
    assert "param deployContentUnderstanding bool = false" in text
    assert "project: 'AI-103'" in text
    assert "owner: owner" in text
    assert "purpose: 'study-lab'" in text
    assert "expiresAt: expiresAt" in text


def test_bicep_modules_cover_required_optional_resources_and_budget():
    assert "Microsoft.CognitiveServices/accounts@2026-03-01" in read("infra/modules/foundry.bicep")
    assert "Microsoft.CognitiveServices/accounts/projects@2026-03-01" in read("infra/modules/foundry.bicep")
    assert "Microsoft.Search/searchServices@2025-05-01" in read("infra/modules/search.bicep")
    assert "Microsoft.Storage/storageAccounts@2025-06-01" in read("infra/modules/storage.bicep")
    assert "Microsoft.CognitiveServices/accounts@2026-03-01" in read("infra/modules/content-understanding.bicep")
    budget = read("infra/modules/budget.bicep")
    assert "Microsoft.Consumption/budgets@2024-08-01" in budget
    assert "Actual_GreaterThan_50_Percent" in budget
    assert "Actual_GreaterThan_80_Percent" in budget
    assert "Actual_GreaterThan_100_Percent" in budget


def test_free_lab_parameters_do_not_select_live_resources():
    text = read("infra/parameters/free-lab.bicepparam")

    assert "param deployFoundry = false" in text
    assert "param deploySearch = false" in text
    assert "param deployStorage = false" in text
    assert "param deployContentUnderstanding = false" in text
    assert "param budgetContactEmail = ''" in text


def test_azure_scripts_require_live_and_typed_confirmation_for_mutations():
    deploy = read("scripts/azure/deploy.ps1")
    destroy = read("scripts/azure/destroy.ps1")

    assert "if (-not $Live)" in deploy
    assert "Offline mode: no Azure resources will be created." in deploy
    assert "-Confirmation 'deploy AI-103 live lab'" in deploy
    assert "az deployment sub what-if" in deploy
    assert deploy.index("az deployment sub what-if") < deploy.index("az deployment sub create")
    assert "state/azure-live" in deploy
    assert "last-deployment.json" in deploy

    assert "if (-not $Live)" in destroy
    assert "Offline mode: no Azure resources will be deleted." in destroy
    assert "-Confirmation 'destroy AI-103 live lab'" in destroy
    assert "az group exists" in destroy
    assert "Destroy is already complete." in destroy
    assert "az group delete" in destroy


def test_preflight_checks_region_provider_and_cost_inputs_before_live_use():
    text = read("scripts/azure/preflight.ps1")

    assert "Offline mode: no Azure account, quota, budget, or live SKU calls are required" in text
    assert "Cost inputs to review before live use" in text
    assert "az account show" in text
    assert "Microsoft.CognitiveServices" in text
    assert "Microsoft.Search" in text
    assert "Microsoft.Storage" in text
    assert "Microsoft.Consumption" in text
    assert "az account list-locations" in text
    assert "Quota and SKU checks" in text


def test_gitignore_excludes_local_azure_config_and_state():
    text = read(".gitignore")

    assert ".azure-local/" in text
    assert "state/azure-live/" in text
    assert "infra/main.json" in text
