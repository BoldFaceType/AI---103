targetScope = 'subscription'

@description('Resource group location. Must be validated by scripts/azure/preflight.ps1 before live deployment.')
param location string = 'eastus'

@description('Manifest-owned resource group name.')
param resourceGroupName string = 'rg-ai103-free-lab'

@description('Short lowercase suffix used for globally unique resource names.')
@minLength(3)
@maxLength(12)
param nameSuffix string

@description('Learner or operator owner tag.')
param owner string

@description('Expiration date tag in YYYY-MM-DD format.')
param expiresAt string

@description('Optional budget amount for tagged lab resources.')
@minValue(1)
param budgetAmount int = 10

@description('Budget notification email. Leave empty to skip budget creation.')
param budgetContactEmail string = ''

@description('Deploy Azure AI Foundry account and project. Default false: no service resource is created.')
param deployFoundry bool = false

@description('Deploy Azure AI Search. Default false: no service resource is created.')
param deploySearch bool = false

@description('Deploy Storage. Default false: no service resource is created.')
param deployStorage bool = false

@description('Deploy Content Understanding-capable AI Services account. Default false: no service resource is created.')
param deployContentUnderstanding bool = false

var tags = {
  project: 'AI-103'
  owner: owner
  purpose: 'study-lab'
  expiresAt: expiresAt
  createdBy: 'AI---103'
}

resource labRg 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module foundry 'modules/foundry.bicep' = if (deployFoundry) {
  name: 'ai103-foundry'
  scope: labRg
  params: {
    location: location
    name: 'ai103foundry${nameSuffix}'
    projectName: 'ai103project${nameSuffix}'
    tags: tags
  }
}

module search 'modules/search.bicep' = if (deploySearch) {
  name: 'ai103-search'
  scope: labRg
  params: {
    location: location
    name: 'ai103-search-${nameSuffix}'
    tags: tags
  }
}

module storage 'modules/storage.bicep' = if (deployStorage) {
  name: 'ai103-storage'
  scope: labRg
  params: {
    location: location
    name: 'ai103st${nameSuffix}'
    tags: tags
  }
}

module contentUnderstanding 'modules/content-understanding.bicep' = if (deployContentUnderstanding) {
  name: 'ai103-content-understanding'
  scope: labRg
  params: {
    location: location
    name: 'ai103cu${nameSuffix}'
    tags: tags
  }
}

module budget 'modules/budget.bicep' = if (!empty(budgetContactEmail)) {
  name: 'ai103-budget'
  params: {
    budgetName: 'ai103-free-lab-budget'
    amount: budgetAmount
    contactEmail: budgetContactEmail
    projectTag: 'AI-103'
  }
}

output resourceGroupId string = labRg.id
output foundryAccountId string = deployFoundry ? resourceId(resourceGroupName, 'Microsoft.CognitiveServices/accounts', 'ai103foundry${nameSuffix}') : ''
output foundryProjectId string = deployFoundry ? resourceId(resourceGroupName, 'Microsoft.CognitiveServices/accounts/projects', 'ai103foundry${nameSuffix}', 'ai103project${nameSuffix}') : ''
output searchServiceId string = deploySearch ? resourceId(resourceGroupName, 'Microsoft.Search/searchServices', 'ai103-search-${nameSuffix}') : ''
output storageAccountId string = deployStorage ? resourceId(resourceGroupName, 'Microsoft.Storage/storageAccounts', 'ai103st${nameSuffix}') : ''
output contentUnderstandingAccountId string = deployContentUnderstanding ? resourceId(resourceGroupName, 'Microsoft.CognitiveServices/accounts', 'ai103cu${nameSuffix}') : ''
