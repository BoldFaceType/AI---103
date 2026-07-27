[CmdletBinding()]
param(
    [switch]$Live,
    [string]$Confirmation = "",
    [string]$ResourceGroupName = "rg-ai103-free-lab"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$statePath = Join-Path $repoRoot "state/azure-live/last-deployment.json"

Write-Host "AI-103 destroy guard"
Write-Host "Resource group: $ResourceGroupName"
Write-Host "Mode: $(if ($Live) { 'live' } else { 'offline' })"

if (-not $env:AZURE_CONFIG_DIR) {
    $env:AZURE_CONFIG_DIR = Join-Path $repoRoot ".azure-local"
}

if (-not $Live) {
    Write-Host "Offline mode: no Azure resources will be deleted."
    Write-Host "Live destroy requires -Live -Confirmation 'destroy AI-103 live lab'."
    exit 0
}

if ($Confirmation -ne "destroy AI-103 live lab") {
    throw "Live destroy requires -Confirmation 'destroy AI-103 live lab'."
}

$exists = az group exists --name $ResourceGroupName --only-show-errors
if ($exists -eq "false") {
    Write-Host "Resource group does not exist. Destroy is already complete."
    exit 0
}

Write-Host "Deleting manifest-owned resource group..."
az group delete --name $ResourceGroupName --yes --only-show-errors

$existsAfter = az group exists --name $ResourceGroupName --only-show-errors
if ($existsAfter -ne "false") {
    throw "Resource group still exists after delete attempt: $ResourceGroupName"
}

if (Test-Path -LiteralPath $statePath) {
    Write-Host "State file retained for audit. It is gitignored and contains non-secret identifiers only: $statePath"
}
Write-Host "Destroy verified."
