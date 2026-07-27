[CmdletBinding()]
param(
    [switch]$Live,
    [switch]$WhatIf,
    [string]$Confirmation = "",
    [string]$Location = "eastus",
    [string]$ParameterFile = "infra/parameters/free-lab.bicepparam",
    [string]$DeploymentName = "ai103-free-lab"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$templatePath = Join-Path $repoRoot "infra/main.bicep"
$parameterPath = Join-Path $repoRoot $ParameterFile
$stateDir = Join-Path $repoRoot "state/azure-live"
$statePath = Join-Path $stateDir "last-deployment.json"

if (-not (Test-Path -LiteralPath $templatePath)) {
    throw "Bicep template not found: $templatePath"
}
if (-not (Test-Path -LiteralPath $parameterPath)) {
    throw "Parameter file not found: $parameterPath"
}
if (-not $env:AZURE_CONFIG_DIR) {
    $env:AZURE_CONFIG_DIR = Join-Path $repoRoot ".azure-local"
}

Write-Host "AI-103 deployment guard"
Write-Host "Template: $templatePath"
Write-Host "Parameters: $parameterPath"
Write-Host "Mode: $(if ($Live) { 'live' } else { 'offline' })"

if (-not $Live) {
    Write-Host "Offline mode: no Azure resources will be created."
    if ($WhatIf) {
        Write-Host "Offline what-if: validate template locally with 'az bicep build --file infra/main.bicep'."
    } else {
        Write-Host "Use -WhatIf for a safe preview or -Live with typed confirmation for a live Azure what-if/deploy."
    }
    exit 0
}

if ($Confirmation -ne "deploy AI-103 live lab") {
    throw "Live deployment requires -Confirmation 'deploy AI-103 live lab'."
}

& (Join-Path $PSScriptRoot "preflight.ps1") -Live -Location $Location -ParameterFile $ParameterFile

Write-Host "Running Azure what-if before any deployment..."
az deployment sub what-if `
    --name $DeploymentName `
    --location $Location `
    --template-file $templatePath `
    --parameters $parameterPath `
    --only-show-errors

if ($WhatIf) {
    Write-Host "What-if completed. No resources were created."
    exit 0
}

Write-Host "Starting live deployment..."
$resultJson = az deployment sub create `
    --name $DeploymentName `
    --location $Location `
    --template-file $templatePath `
    --parameters $parameterPath `
    --only-show-errors `
    -o json

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$result = $resultJson | ConvertFrom-Json
$outputs = $result.properties.outputs
$state = [ordered]@{
    deploymentName = $DeploymentName
    subscriptionId = (az account show --query id -o tsv --only-show-errors)
    location = $Location
    resourceGroupId = $outputs.resourceGroupId.value
    foundryAccountId = $outputs.foundryAccountId.value
    foundryProjectId = $outputs.foundryProjectId.value
    searchServiceId = $outputs.searchServiceId.value
    storageAccountId = $outputs.storageAccountId.value
    contentUnderstandingAccountId = $outputs.contentUnderstandingAccountId.value
}
$state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding utf8
Write-Host "Wrote non-secret deployment state: $statePath"
