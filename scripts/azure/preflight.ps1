[CmdletBinding()]
param(
    [switch]$Live,
    [string]$Location = "eastus",
    [string]$ParameterFile = "infra/parameters/free-lab.bicepparam"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$parameterPath = Join-Path $repoRoot $ParameterFile

if (-not (Test-Path -LiteralPath $parameterPath)) {
    throw "Parameter file not found: $parameterPath"
}

Write-Host "AI-103 Azure preflight"
Write-Host "Mode: $(if ($Live) { 'live validation' } else { 'offline validation only' })"
Write-Host "Parameter file: $parameterPath"
Write-Host "Location: $Location"

$az = Get-Command az -ErrorAction SilentlyContinue
if (-not $az) {
    throw "Azure CLI is required for T17 preflight and deployment."
}

if (-not $env:AZURE_CONFIG_DIR) {
    $env:AZURE_CONFIG_DIR = Join-Path $repoRoot ".azure-local"
}
Write-Host "AZURE_CONFIG_DIR: $env:AZURE_CONFIG_DIR"

if (-not $Live) {
    Write-Host "Offline mode: no Azure account, quota, budget, or live SKU calls are required; no resources are created."
    Write-Host "Cost inputs to review before live use: resource group, selected optional modules, budget amount, budget email, region, quota."
    exit 0
}

$accountJson = az account show --only-show-errors 2>$null
if (-not $accountJson) {
    throw "No Azure account is selected. Run 'az login' and 'az account set --subscription <id>' before -Live."
}
$account = $accountJson | ConvertFrom-Json
if (-not $account.id) {
    throw "Azure subscription id was not returned by az account show."
}
Write-Host "Subscription: $($account.name) [$($account.id)]"
Write-Host "Tenant: $($account.tenantId)"

Write-Host "Checking provider registration state..."
$providers = @(
    "Microsoft.Resources",
    "Microsoft.CognitiveServices",
    "Microsoft.Search",
    "Microsoft.Storage",
    "Microsoft.Consumption"
)
foreach ($provider in $providers) {
    $state = az provider show --namespace $provider --query "registrationState" -o tsv --only-show-errors
    Write-Host "${provider}: $state"
}

Write-Host "Checking location metadata..."
az account list-locations --query "[?name=='$Location'].{name:name,displayName:displayName}" -o table --only-show-errors

Write-Host "Quota and SKU checks must be reviewed in Azure for selected optional services before deployment."
Write-Host "For Foundry/OpenAI quota, use the Foundry quota page or the documented Cognitive Services usage reader role."
